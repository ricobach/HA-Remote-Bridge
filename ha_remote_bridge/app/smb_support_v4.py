"""SMB file preview support for HA Remote Bridge 0.3.0."""

from __future__ import annotations

import asyncio
import html
import mimetypes
import secrets
from pathlib import Path
from urllib.parse import quote

from aiohttp import web

import smb_support_v3 as previous

base = previous.base
PREVIEW_DIR = Path("/tmp/ha-remote-bridge-smb-preview")
TEXT_PREVIEW_LIMIT = 2 * 1024 * 1024


def _ensure_preview_dir() -> None:
    PREVIEW_DIR.mkdir(parents=True, exist_ok=True)
    PREVIEW_DIR.chmod(0o700)


def _resource(request: web.Request) -> dict:
    return base._resource(request)


def _preview_kind(filename: str) -> tuple[str, str]:
    mime, _encoding = mimetypes.guess_type(filename)
    mime = mime or "application/octet-stream"
    lower = filename.lower()
    if mime.startswith("image/"):
        return "image", mime
    if mime == "application/pdf" or lower.endswith(".pdf"):
        return "pdf", "application/pdf"
    if mime.startswith("audio/"):
        return "audio", mime
    if mime.startswith("video/"):
        return "video", mime
    if mime.startswith("text/") or lower.endswith((
        ".txt", ".log", ".md", ".markdown", ".json", ".yaml", ".yml", ".xml", ".csv",
        ".ini", ".cfg", ".conf", ".py", ".js", ".ts", ".css", ".html", ".htm", ".sh",
        ".bash", ".zsh", ".sql", ".toml", ".properties", ".env",
    )):
        return "text", mime if mime != "application/octet-stream" else "text/plain"
    return "download", mime


async def _fetch_to_temp(resource: dict, share: str, full_path: str, *, timeout: float = 120) -> tuple[Path, str]:
    share = base._safe_share(share)
    full_path = base._safe_path(full_path)
    if not full_path:
        raise web.HTTPBadRequest(text="A file path is required")
    parent, _, filename = full_path.rpartition("/")
    if not filename:
        raise web.HTTPBadRequest(text="A file name is required")

    _ensure_preview_dir()
    local_path = PREVIEW_DIR / secrets.token_hex(16)
    service = f"//{resource['smb_host']}/{share}"
    command = f"get {base._quoted_smb_name(filename)} {base._quoted_smb_name(str(local_path))}"
    extra = [service]
    if parent:
        extra += ["-D", parent]
    extra += ["-c", command]
    try:
        await base._run_smbclient(resource, extra, timeout=timeout)
    except Exception:
        local_path.unlink(missing_ok=True)
        raise
    if not local_path.exists():
        raise web.HTTPBadGateway(text="SMB preview did not produce a local file")
    return local_path, filename


async def raw_file(request: web.Request) -> web.StreamResponse:
    """Stream a configured SMB file inline through Ingress, then delete the temp copy."""
    resource = _resource(request)
    share = request.query.get("share", "")
    full_path = request.query.get("path", "")
    local_path, filename = await _fetch_to_temp(resource, share, full_path)
    _kind, mime = _preview_kind(filename)
    response = web.StreamResponse(
        status=200,
        headers={
            "Content-Type": mime,
            "Content-Disposition": f"inline; filename*=UTF-8''{quote(filename, safe='')}",
            "Content-Length": str(local_path.stat().st_size),
            "Cache-Control": "no-store",
            "X-Content-Type-Options": "nosniff",
        },
    )
    await response.prepare(request)
    try:
        with local_path.open("rb") as handle:
            while True:
                chunk = await asyncio.to_thread(handle.read, 256 * 1024)
                if not chunk:
                    break
                await response.write(chunk)
        await response.write_eof()
        return response
    finally:
        local_path.unlink(missing_ok=True)


async def text_preview(request: web.Request) -> web.Response:
    """Return a bounded UTF-8 text preview so huge logs cannot exhaust the browser."""
    resource = _resource(request)
    share = request.query.get("share", "")
    full_path = request.query.get("path", "")
    local_path, filename = await _fetch_to_temp(resource, share, full_path)
    try:
        size = local_path.stat().st_size
        with local_path.open("rb") as handle:
            raw = await asyncio.to_thread(handle.read, TEXT_PREVIEW_LIMIT + 1)
        truncated = len(raw) > TEXT_PREVIEW_LIMIT
        raw = raw[:TEXT_PREVIEW_LIMIT]
        text = raw.decode("utf-8", errors="replace")
        return web.json_response({
            "name": filename,
            "text": text,
            "size": size,
            "truncated": truncated,
            "limit": TEXT_PREVIEW_LIMIT,
        }, headers={"Cache-Control": "no-store"})
    finally:
        local_path.unlink(missing_ok=True)


VIEW_PAGE = r'''<!doctype html>
<html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<title>SMB File Viewer</title>
<style>
:root{color-scheme:light dark;--bg:#f5f5f5;--surface:#fff;--text:#212121;--muted:#727272;--border:#ddd;--accent:#03a9f4}
@media(prefers-color-scheme:dark){:root{--bg:#111;--surface:#1c1c1c;--text:#eee;--muted:#aaa;--border:#383838}}
*{box-sizing:border-box}html,body{height:100%}body{margin:0;background:var(--bg);color:var(--text);font:14px system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;display:flex;flex-direction:column}.bar{min-height:52px;display:flex;align-items:center;gap:8px;padding:8px 12px;background:var(--surface);border-bottom:1px solid var(--border)}.name{font-weight:600;min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;flex:1}.meta{font-size:11px;color:var(--muted);white-space:nowrap}button,a.btn{border:1px solid var(--border);background:var(--surface);color:var(--text);border-radius:6px;padding:7px 10px;text-decoration:none;font:inherit}.viewer{flex:1;min-height:0;display:flex;align-items:center;justify-content:center;padding:10px;overflow:auto}.viewer img{max-width:100%;max-height:100%;object-fit:contain}.viewer iframe{width:100%;height:100%;border:0;background:white}.viewer video{max-width:100%;max-height:100%}.viewer audio{width:min(720px,100%)}.text-wrap{width:100%;height:100%;display:flex;flex-direction:column;gap:8px}.notice{display:none;padding:8px 10px;border:1px solid var(--border);border-radius:6px;color:var(--muted);background:var(--surface)}pre{margin:0;flex:1;overflow:auto;padding:14px;background:var(--surface);border:1px solid var(--border);border-radius:8px;font:12px/1.5 ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;white-space:pre;tab-size:4}.wrap pre{white-space:pre-wrap;overflow-wrap:anywhere}.unknown{max-width:560px;text-align:center;background:var(--surface);border:1px solid var(--border);border-radius:10px;padding:28px}.unknown h2{margin-top:0}@media(max-width:600px){.meta{display:none}.viewer{padding:6px}.bar{flex-wrap:wrap}}
</style></head><body>
<div class="bar"><button id="back" type="button">← Back</button><div class="name" id="name">__NAME__</div><div class="meta">__MIME__</div><button id="wrap" type="button" style="display:none">Wrap</button><button id="copy" type="button" style="display:none">Copy</button><a class="btn" href="__DOWNLOAD__">Download</a></div>
<div class="viewer" id="viewer">__VIEWER__</div>
<script>
const back=document.getElementById('back');back.onclick=()=>history.length>1?history.back():location.replace('__BROWSER__');
const kind='__KIND__';
if(kind==='text'){
 const viewer=document.getElementById('viewer');viewer.innerHTML='<div class="text-wrap"><div id="notice" class="notice"></div><pre id="text">Loading…</pre></div>';
 const wrap=document.getElementById('wrap'),copy=document.getElementById('copy');wrap.style.display='';copy.style.display='';
 wrap.onclick=()=>{viewer.classList.toggle('wrap');wrap.textContent=viewer.classList.contains('wrap')?'No wrap':'Wrap';};
 copy.onclick=async()=>{try{await navigator.clipboard.writeText(document.getElementById('text').textContent);copy.textContent='Copied';setTimeout(()=>copy.textContent='Copy',1200);}catch(_){copy.textContent='Copy failed';}};
 fetch('__TEXT_API__',{cache:'no-store'}).then(async r=>{const d=await r.json();if(!r.ok)throw new Error(d.error||'Unable to load text preview');document.getElementById('text').textContent=d.text;document.getElementById('name').textContent=d.name;const n=document.getElementById('notice');if(d.truncated){n.style.display='block';n.textContent='Preview limited to the first '+Math.round(d.limit/1024/1024)+' MB of this file.';}}).catch(e=>{document.getElementById('text').textContent=e.message||String(e);});
}
</script></body></html>'''


async def viewer_page(request: web.Request) -> web.Response:
    resource = _resource(request)
    share = base._safe_share(request.query.get("share", ""))
    full_path = base._safe_path(request.query.get("path", ""))
    if not full_path:
        raise web.HTTPBadRequest(text="A file path is required")
    filename = full_path.rpartition("/")[2]
    kind, mime = _preview_kind(filename)
    q_share = quote(share, safe="")
    q_path = quote(full_path, safe="")
    rid = resource["id"]
    raw_url = f"../../api/smb/{rid}/raw?share={q_share}&path={q_path}"
    text_url = f"../../api/smb/{rid}/text?share={q_share}&path={q_path}"
    download_url = f"../../api/smb/{rid}/download?share={q_share}&path={q_path}"
    browser_url = f"./"

    if kind == "image":
        viewer = f'<img src="{html.escape(raw_url, quote=True)}" alt="">'
    elif kind == "pdf":
        viewer = f'<iframe src="{html.escape(raw_url, quote=True)}" title="PDF preview"></iframe>'
    elif kind == "audio":
        viewer = f'<audio controls autoplay src="{html.escape(raw_url, quote=True)}"></audio>'
    elif kind == "video":
        viewer = f'<video controls playsinline src="{html.escape(raw_url, quote=True)}"></video>'
    elif kind == "text":
        viewer = ""
    else:
        viewer = '<div class="unknown"><h2>No inline preview</h2><p>This file type is not supported by the built-in viewer.</p><p>Use Download to open it with another app.</p></div>'

    page = VIEW_PAGE
    replacements = {
        "__NAME__": html.escape(filename),
        "__MIME__": html.escape(mime),
        "__VIEWER__": viewer,
        "__KIND__": kind,
        "__TEXT_API__": text_url,
        "__DOWNLOAD__": download_url,
        "__BROWSER__": browser_url,
    }
    for key, value in replacements.items():
        page = page.replace(key, value)
    return web.Response(text=page, content_type="text/html", headers={"Cache-Control": "no-store"})


# Enhance the existing SMB browser so tapping a file opens the viewer, while a
# separate Download action remains available.
SMB_PAGE = base.SMB_PAGE
old = "const size=document.createElement('div');size.className='meta';size.textContent=item.directory?'':human(item.size);row.append(name,kind,size);$('content').append(row);"
new = "const size=document.createElement('div');size.className='meta';if(item.directory){size.textContent='';}else{const dl=document.createElement('a');dl.href=api('download?share='+enc(share)+'&path='+enc([path,item.name].filter(Boolean).join('/')));dl.textContent='Download';dl.style.color='var(--accent)';dl.style.textDecoration='none';size.append(dl);}row.append(name,kind,size);$('content').append(row);"
SMB_PAGE = SMB_PAGE.replace(old, new)
SMB_PAGE = SMB_PAGE.replace(
    "else b.onclick=()=>{location.href=api('download?share='+enc(share)+'&path='+enc([path,item.name].filter(Boolean).join('/')));};",
    "else b.onclick=()=>{location.href='view?share='+enc(share)+'&path='+enc([path,item.name].filter(Boolean).join('/'));};",
)


async def smb_page(request: web.Request) -> web.Response:
    resource = _resource(request)
    page = SMB_PAGE.replace("__RESOURCE_ID__", resource["id"])
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
