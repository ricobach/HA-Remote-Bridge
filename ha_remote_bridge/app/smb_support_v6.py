"""Inline ZIP browsing for SMB files in HA Remote Bridge 0.3.2."""

from __future__ import annotations

import asyncio
import html
import io
import mimetypes
import zipfile
from pathlib import PurePosixPath
from urllib.parse import quote

from aiohttp import web

import smb_support_v5 as previous

base = previous.base
MAX_ZIP_ENTRIES = 10_000
MAX_ZIP_TOTAL_UNCOMPRESSED = 2 * 1024 * 1024 * 1024
MAX_ZIP_ENTRY_PREVIEW = 64 * 1024 * 1024
MAX_ZIP_TEXT_PREVIEW = previous.TEXT_PREVIEW_LIMIT


def _safe_entry_name(value: str) -> str:
    value = str(value or "").replace("\\", "/").lstrip("/")
    parts = []
    for part in PurePosixPath("/" + value).parts:
        if part in {"/", "", "."}:
            continue
        if part == "..":
            raise web.HTTPBadRequest(text="Unsafe ZIP entry path")
        parts.append(part)
    cleaned = "/".join(parts)
    if not cleaned or len(cleaned) > 4096 or "\x00" in cleaned:
        raise web.HTTPBadRequest(text="Invalid ZIP entry path")
    return cleaned


def _validate_archive(zf: zipfile.ZipFile) -> list[zipfile.ZipInfo]:
    infos = zf.infolist()
    if len(infos) > MAX_ZIP_ENTRIES:
        raise web.HTTPRequestEntityTooLarge(
            max_size=MAX_ZIP_ENTRIES,
            actual_size=len(infos),
            text=f"ZIP archive contains too many entries (maximum {MAX_ZIP_ENTRIES})",
        )
    total = 0
    for info in infos:
        _safe_entry_name(info.filename.rstrip("/")) if info.filename.rstrip("/") else None
        total += max(0, int(info.file_size))
        if total > MAX_ZIP_TOTAL_UNCOMPRESSED:
            raise web.HTTPRequestEntityTooLarge(
                max_size=MAX_ZIP_TOTAL_UNCOMPRESSED,
                actual_size=total,
                text="ZIP archive expands beyond the preview safety limit",
            )
    return infos


async def _open_zip_from_smb(request: web.Request) -> tuple[dict, str, str, object, zipfile.ZipFile]:
    resource = base._resource(request)
    share = base._safe_share(request.query.get("share", ""))
    full_path = base._safe_path(request.query.get("path", ""))
    if not full_path:
        raise web.HTTPBadRequest(text="A ZIP file path is required")
    local_path, filename = await previous._fetch_to_temp(resource, share, full_path, timeout=180)
    try:
        zf = zipfile.ZipFile(local_path, "r")
        _validate_archive(zf)
    except (zipfile.BadZipFile, zipfile.LargeZipFile) as err:
        local_path.unlink(missing_ok=True)
        raise web.HTTPBadRequest(text=f"Unable to read ZIP archive: {err}") from err
    except Exception:
        local_path.unlink(missing_ok=True)
        raise
    return resource, share, full_path, local_path, zf


def _zip_children(infos: list[zipfile.ZipInfo], folder: str) -> list[dict]:
    folder = folder.strip("/")
    prefix = folder + "/" if folder else ""
    children: dict[str, dict] = {}
    for info in infos:
        raw = info.filename.replace("\\", "/").lstrip("/")
        clean = raw.rstrip("/")
        if not clean:
            continue
        safe = _safe_entry_name(clean)
        if not safe.startswith(prefix):
            continue
        remainder = safe[len(prefix):]
        if not remainder:
            continue
        first, sep, _rest = remainder.partition("/")
        key = prefix + first
        if sep or info.is_dir():
            children[key] = {"name": first, "entry": key, "directory": True, "size": None}
        elif key not in children:
            children[key] = {"name": first, "entry": safe, "directory": False, "size": int(info.file_size)}
    return sorted(children.values(), key=lambda item: (not item["directory"], item["name"].lower()))


async def zip_list(request: web.Request) -> web.Response:
    folder = request.query.get("folder", "").replace("\\", "/").strip("/")
    if folder:
        folder = _safe_entry_name(folder)
    _resource, _share, _path, local_path, zf = await _open_zip_from_smb(request)
    try:
        infos = zf.infolist()
        return web.json_response({
            "folder": folder,
            "items": _zip_children(infos, folder),
            "entries": len(infos),
        }, headers={"Cache-Control": "no-store"})
    finally:
        zf.close()
        local_path.unlink(missing_ok=True)


def _find_zip_info(zf: zipfile.ZipFile, entry: str) -> zipfile.ZipInfo:
    entry = _safe_entry_name(entry)
    for info in zf.infolist():
        if info.filename.replace("\\", "/").lstrip("/").rstrip("/") == entry:
            if info.is_dir():
                raise web.HTTPBadRequest(text="ZIP entry is a directory")
            if info.flag_bits & 0x1:
                raise web.HTTPBadRequest(text="Encrypted ZIP entries are not supported for inline preview")
            if info.file_size > MAX_ZIP_ENTRY_PREVIEW:
                raise web.HTTPRequestEntityTooLarge(
                    max_size=MAX_ZIP_ENTRY_PREVIEW,
                    actual_size=info.file_size,
                    text="ZIP entry is too large for inline preview",
                )
            return info
    raise web.HTTPNotFound(text="ZIP entry not found")


async def _read_zip_entry(request: web.Request, limit: int | None = None) -> tuple[str, bytes, bool]:
    entry = _safe_entry_name(request.query.get("entry", ""))
    _resource, _share, _path, local_path, zf = await _open_zip_from_smb(request)
    try:
        info = _find_zip_info(zf, entry)
        read_limit = (limit + 1) if limit is not None else (MAX_ZIP_ENTRY_PREVIEW + 1)
        with zf.open(info, "r") as handle:
            data = await asyncio.to_thread(handle.read, read_limit)
        if limit is None and len(data) > MAX_ZIP_ENTRY_PREVIEW:
            raise web.HTTPRequestEntityTooLarge(
                max_size=MAX_ZIP_ENTRY_PREVIEW,
                actual_size=len(data),
                text="ZIP entry is too large for inline preview",
            )
        truncated = limit is not None and len(data) > limit
        return entry, data[:limit] if limit is not None else data, truncated
    finally:
        zf.close()
        local_path.unlink(missing_ok=True)


async def zip_raw(request: web.Request) -> web.Response:
    entry, data, _truncated = await _read_zip_entry(request)
    mime = mimetypes.guess_type(entry)[0] or "application/octet-stream"
    filename = entry.rpartition("/")[2]
    return web.Response(
        body=data,
        headers={
            "Content-Type": mime,
            "Content-Disposition": f"inline; filename*=UTF-8''{quote(filename, safe='')}",
            "Cache-Control": "no-store",
            "X-Content-Type-Options": "nosniff",
        },
    )


async def zip_text(request: web.Request) -> web.Response:
    entry, data, truncated = await _read_zip_entry(request, MAX_ZIP_TEXT_PREVIEW)
    return web.json_response({
        "name": entry.rpartition("/")[2],
        "text": data.decode("utf-8", errors="replace"),
        "truncated": truncated,
        "limit": MAX_ZIP_TEXT_PREVIEW,
    }, headers={"Cache-Control": "no-store"})


ZIP_PAGE = r'''<!doctype html>
<html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<title>ZIP Browser</title><style>
:root{color-scheme:light dark;--bg:#f5f5f5;--surface:#fff;--text:#212121;--muted:#727272;--border:#ddd;--accent:#03a9f4}@media(prefers-color-scheme:dark){:root{--bg:#111;--surface:#1c1c1c;--text:#eee;--muted:#aaa;--border:#383838}}*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--text);font:14px system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}.bar{height:52px;display:flex;align-items:center;gap:8px;padding:0 12px;background:var(--surface);border-bottom:1px solid var(--border);position:sticky;top:0}.title{font-weight:600}.crumbs{flex:1;min-width:0;color:var(--muted);overflow:hidden;text-overflow:ellipsis;white-space:nowrap}button,a{border:1px solid var(--border);background:var(--surface);color:var(--text);border-radius:6px;padding:7px 10px;text-decoration:none;font:inherit}.wrap{padding:12px;max-width:1100px;margin:auto}.list{background:var(--surface);border:1px solid var(--border);border-radius:8px;overflow:hidden}.row{display:grid;grid-template-columns:minmax(0,1fr) 90px;gap:10px;align-items:center;padding:10px 12px;border-bottom:1px solid var(--border)}.row:last-child{border-bottom:0}.name{min-width:0}.name button{border:0;padding:0;background:transparent;text-align:left;max-width:100%;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.meta{text-align:right;color:var(--muted);font-size:12px}.empty,.error{padding:24px;text-align:center;color:var(--muted)}.error{color:#d32f2f}
</style></head><body><div class="bar"><button id="back">← File</button><button id="up">↑ Up</button><div class="title">ZIP</div><div id="crumbs" class="crumbs">__ZIP_NAME__</div><a href="__DOWNLOAD__">Download ZIP</a></div><div class="wrap"><div id="list" class="list"><div class="empty">Loading…</div></div></div><script>
const baseQuery='share=__Q_SHARE__&path=__Q_PATH__';let folder=new URLSearchParams(location.search).get('folder')||'';const list=document.getElementById('list'),crumbs=document.getElementById('crumbs');const enc=encodeURIComponent;
function human(n){if(n==null)return'';const u=['B','KB','MB','GB'];let i=0,v=Number(n);while(v>=1024&&i<u.length-1){v/=1024;i++;}return(i?v.toFixed(v<10?1:0):v)+' '+u[i];}
async function load(){crumbs.textContent='__ZIP_NAME__'+(folder?' / '+folder:'');list.innerHTML='<div class="empty">Loading…</div>';try{const r=await fetch('__LIST_API__&folder='+enc(folder),{cache:'no-store'});const d=await r.json();if(!r.ok)throw new Error(d.error||'Unable to read ZIP');list.innerHTML='';if(!d.items.length){list.innerHTML='<div class="empty">This ZIP folder is empty.</div>';return;}for(const item of d.items){const row=document.createElement('div');row.className='row';const n=document.createElement('div');n.className='name';const b=document.createElement('button');b.textContent=(item.directory?'📁 ':'📄 ')+item.name;b.onclick=()=>{if(item.directory){folder=item.entry;history.replaceState(null,'',location.pathname+'?'+baseQuery+'&folder='+enc(folder));load();}else location.href='zip-entry?'+baseQuery+'&entry='+enc(item.entry)+'&folder='+enc(folder);};n.append(b);const m=document.createElement('div');m.className='meta';m.textContent=item.directory?'Folder':human(item.size);row.append(n,m);list.append(row);}}catch(e){list.innerHTML='<div class="error"></div>';list.firstChild.textContent=e.message||String(e);}}
document.getElementById('up').onclick=()=>{if(!folder)return;const p=folder.split('/');p.pop();folder=p.join('/');history.replaceState(null,'',location.pathname+'?'+baseQuery+(folder?'&folder='+enc(folder):''));load();};document.getElementById('back').onclick=()=>location.replace('__FILE_VIEW__');load();
</script></body></html>'''


ZIP_ENTRY_PAGE = previous.VIEW_PAGE


def _entry_kind(entry: str) -> tuple[str, str]:
    return previous._preview_kind(entry.rpartition("/")[2])


async def viewer_page(request: web.Request) -> web.Response:
    full_path = base._safe_path(request.query.get("path", ""))
    if full_path.lower().endswith(".zip"):
        resource = base._resource(request)
        share = base._safe_share(request.query.get("share", ""))
        q_share = quote(share, safe="")
        q_path = quote(full_path, safe="")
        parent = full_path.rpartition("/")[0]
        rid = resource["id"]
        page = ZIP_PAGE
        replacements = {
            "__ZIP_NAME__": html.escape(full_path.rpartition("/")[2]),
            "__Q_SHARE__": q_share,
            "__Q_PATH__": q_path,
            "__LIST_API__": f"../../api/smb/{rid}/zip/list?share={q_share}&path={q_path}",
            "__DOWNLOAD__": f"../../api/smb/{rid}/download?share={q_share}&path={q_path}",
            "__FILE_VIEW__": f"./?share={q_share}&path={quote(parent, safe='')}",
        }
        for key, value in replacements.items():
            page = page.replace(key, value)
        return web.Response(text=page, content_type="text/html", headers={"Cache-Control": "no-store"})
    return await previous.viewer_page(request)


async def zip_entry_page(request: web.Request) -> web.Response:
    resource = base._resource(request)
    share = base._safe_share(request.query.get("share", ""))
    full_path = base._safe_path(request.query.get("path", ""))
    entry = _safe_entry_name(request.query.get("entry", ""))
    folder = request.query.get("folder", "").replace("\\", "/").strip("/")
    if folder:
        folder = _safe_entry_name(folder)
    kind, mime = _entry_kind(entry)
    q_share, q_path, q_entry = quote(share, safe=""), quote(full_path, safe=""), quote(entry, safe="")
    rid = resource["id"]
    raw_url = f"../../api/smb/{rid}/zip/raw?share={q_share}&path={q_path}&entry={q_entry}"
    text_url = f"../../api/smb/{rid}/zip/text?share={q_share}&path={q_path}&entry={q_entry}"
    back_url = f"view?share={q_share}&path={q_path}" + (f"&folder={quote(folder, safe='')}" if folder else "")
    filename = entry.rpartition("/")[2]
    if kind == "image": viewer = f'<img src="{html.escape(raw_url, quote=True)}" alt="">'
    elif kind == "pdf": viewer = f'<iframe src="{html.escape(raw_url, quote=True)}" title="PDF preview"></iframe>'
    elif kind == "audio": viewer = f'<audio controls autoplay src="{html.escape(raw_url, quote=True)}"></audio>'
    elif kind == "video": viewer = f'<video controls playsinline src="{html.escape(raw_url, quote=True)}"></video>'
    elif kind == "text": viewer = ""
    else: viewer = '<div class="unknown"><h2>No inline preview</h2><p>This ZIP entry type is not supported by the built-in viewer.</p></div>'
    page = ZIP_ENTRY_PAGE.replace("const back=document.getElementById('back');back.onclick=()=>history.length>1?history.back():location.replace('__BROWSER__');", "const back=document.getElementById('back');back.onclick=()=>location.replace('__BROWSER__');", 1)
    for key, value in {
        "__NAME__": html.escape(filename), "__MIME__": html.escape(mime), "__VIEWER__": viewer,
        "__KIND__": kind, "__TEXT_API__": text_url, "__DOWNLOAD__": raw_url, "__BROWSER__": back_url,
    }.items(): page = page.replace(key, value)
    return web.Response(text=page, content_type="text/html", headers={"Cache-Control": "no-store"})


# Public interface expected by the runtime.
VAULT = previous.VAULT
validate_smb_payload = previous.validate_smb_payload
smb_resource_url = previous.smb_resource_url
list_credentials = previous.list_credentials
add_credential = previous.add_credential
delete_credential = previous.delete_credential
list_shares = previous.list_shares
list_directory = previous.list_directory
download_file = previous.download_file
probe_smb_resource = previous.probe_smb_resource
test_connection = previous.test_connection
raw_file = previous.raw_file
text_preview = previous.text_preview
smb_page = previous.smb_page
