"""SMB browser and reusable credential support for HA Remote Bridge."""

from __future__ import annotations

import asyncio
import json
import os
import secrets
import tempfile
import time
from pathlib import Path, PurePosixPath
from urllib.parse import quote

from aiohttp import web

import main

DATA_DIR = Path("/data")
SMB_DIR = DATA_DIR / "smb"
CREDENTIALS_FILE = SMB_DIR / "credentials.json"
DOWNLOAD_DIR = SMB_DIR / "downloads"


def _ensure_storage() -> None:
    SMB_DIR.mkdir(parents=True, exist_ok=True)
    DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)
    os.chmod(SMB_DIR, 0o700)
    os.chmod(DOWNLOAD_DIR, 0o700)


def _atomic_json_write(path: Path, value: object) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.chmod(tmp, 0o600)
    os.replace(tmp, path)
    os.chmod(path, 0o600)


class SMBCredentialVault:
    """Persist reusable SMB username/password credentials."""

    def __init__(self) -> None:
        self._lock = asyncio.Lock()
        self._loaded = False
        self._items: list[dict] = []

    async def load(self) -> None:
        async with self._lock:
            if self._loaded:
                return
            _ensure_storage()
            if CREDENTIALS_FILE.exists():
                try:
                    data = json.loads(CREDENTIALS_FILE.read_text(encoding="utf-8"))
                    if isinstance(data, list):
                        self._items = [item for item in data if isinstance(item, dict)]
                except (OSError, json.JSONDecodeError):
                    main.LOGGER.exception("Unable to load SMB credential vault")
                    self._items = []
            self._loaded = True

    def get(self, credential_id: str | None) -> dict | None:
        if not credential_id:
            return None
        return next((item for item in self._items if item.get("id") == credential_id), None)

    @staticmethod
    def _public(item: dict) -> dict:
        return {
            "id": item.get("id"),
            "name": item.get("name"),
            "username": item.get("username"),
            "domain": item.get("domain", ""),
            "created_at": item.get("created_at"),
        }

    async def list_public(self) -> list[dict]:
        await self.load()
        return [self._public(item) for item in self._items]

    async def add(self, name: str, username: str, password: str, domain: str = "") -> dict:
        await self.load()
        name = name.strip()
        username = username.strip()
        domain = domain.strip()
        if not name:
            raise web.HTTPBadRequest(text="Credential name is required")
        if len(name) > 80:
            raise web.HTTPBadRequest(text="Credential name is too long")
        if not username:
            raise web.HTTPBadRequest(text="SMB username is required")
        if len(username) > 128 or any(ch in username for ch in "\r\n"):
            raise web.HTTPBadRequest(text="Invalid SMB username")
        if len(password) > 1024 or any(ch in password for ch in "\r\n"):
            raise web.HTTPBadRequest(text="Invalid SMB password")
        if len(domain) > 128 or any(ch in domain for ch in "\r\n"):
            raise web.HTTPBadRequest(text="Invalid SMB domain")

        item = {
            "id": secrets.token_hex(8),
            "name": name,
            "username": username,
            "password": password,
            "domain": domain,
            "created_at": int(time.time()),
        }
        self._items.append(item)
        _atomic_json_write(CREDENTIALS_FILE, self._items)
        main.LOGGER.info("Added reusable SMB credential %s", name)
        return self._public(item)

    async def delete(self, credential_id: str) -> None:
        await self.load()
        item = self.get(credential_id)
        if item is None:
            raise web.HTTPNotFound(text="Unknown SMB credential")
        if any(resource.get("smb_credential_id") == credential_id for resource in main.STORE.resources):
            raise web.HTTPConflict(text="This SMB credential is still used by one or more resources")
        self._items.remove(item)
        _atomic_json_write(CREDENTIALS_FILE, self._items)


VAULT = SMBCredentialVault()


def validate_smb_payload(payload: dict) -> tuple[str, str, int, str | None]:
    name = str(payload.get("name", "")).strip()
    host = str(payload.get("smb_host", "")).strip()
    credential_id = str(payload.get("smb_credential_id", "")).strip() or None
    try:
        port = int(payload.get("smb_port", 445))
    except (TypeError, ValueError):
        raise web.HTTPBadRequest(text="SMB port must be a number")

    if not name:
        raise web.HTTPBadRequest(text="Session Name is required")
    if len(name) > 100:
        raise web.HTTPBadRequest(text="Session Name is too long")
    if not host or any(ch in host for ch in "/\\\r\n\t "):
        raise web.HTTPBadRequest(text="A valid SMB hostname or IP address is required")
    if len(host) > 255:
        raise web.HTTPBadRequest(text="SMB host is too long")
    if not 1 <= port <= 65535:
        raise web.HTTPBadRequest(text="SMB port must be between 1 and 65535")
    if credential_id and VAULT.get(credential_id) is None:
        raise web.HTTPBadRequest(text="Unknown SMB credential")
    return name, host, port, credential_id


def smb_resource_url(host: str, port: int) -> str:
    display_host = f"[{host}]" if ":" in host and not host.startswith("[") else host
    return f"smb://{display_host}:{port}"


def _safe_share(value: str) -> str:
    value = value.strip()
    forbidden = {'/', '\\', ';', '\r', '\n', '\t', '"', "'"}
    if not value or len(value) > 255 or any(ch in forbidden for ch in value):
        raise web.HTTPBadRequest(text="Invalid SMB share name")
    return value


def _safe_path(value: str) -> str:
    value = value.replace("\\", "/").strip("/")
    forbidden = {';', '\r', '\n', '\t', '"'}
    if len(value) > 4096 or any(ch in forbidden for ch in value):
        raise web.HTTPBadRequest(text="Invalid SMB path")
    parts = []
    for part in PurePosixPath("/" + value).parts:
        if part in {"/", "", "."}:
            continue
        if part == "..":
            raise web.HTTPBadRequest(text="Parent path traversal is not allowed")
        parts.append(part)
    return "/".join(parts)


def _auth_file(credential: dict | None) -> str | None:
    if credential is None:
        return None
    _ensure_storage()
    fd, path = tempfile.mkstemp(prefix="ha-rb-smb-auth-", dir="/tmp", text=True)
    try:
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(f"username = {credential['username']}\n")
            handle.write(f"password = {credential['password']}\n")
            if credential.get("domain"):
                handle.write(f"domain = {credential['domain']}\n")
        return path
    except Exception:
        try:
            os.close(fd)
        except OSError:
            pass
        Path(path).unlink(missing_ok=True)
        raise


async def _run_smbclient(resource: dict, extra: list[str], timeout: float = 20) -> str:
    credential = VAULT.get(resource.get("smb_credential_id"))
    auth_path = _auth_file(credential)
    command = [
        "smbclient",
        "-g",
        "-m", "SMB3",
        "-p", str(resource.get("smb_port", 445)),
        "-t", "12",
    ]
    if auth_path:
        command += ["-A", auth_path]
    else:
        command += ["-N"]
    command += extra
    try:
        process = await asyncio.create_subprocess_exec(
            *command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        try:
            stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=timeout)
        except asyncio.TimeoutError:
            process.kill()
            await process.wait()
            raise web.HTTPGatewayTimeout(text="SMB request timed out")
        if process.returncode != 0:
            message = stderr.decode(errors="replace").strip() or stdout.decode(errors="replace").strip()
            raise web.HTTPBadGateway(text=(message or "SMB request failed")[:1000])
        return stdout.decode(errors="replace")
    finally:
        if auth_path:
            Path(auth_path).unlink(missing_ok=True)


def _resource(request: web.Request) -> dict:
    resource = main.STORE.get(request.match_info["resource_id"])
    if resource is None or resource.get("resource_type") != "smb":
        raise web.HTTPNotFound(text="Unknown SMB resource")
    return resource


async def list_credentials(request: web.Request) -> web.Response:
    return web.json_response(await VAULT.list_public())


async def add_credential(request: web.Request) -> web.Response:
    try:
        payload = await request.json()
    except (json.JSONDecodeError, ValueError):
        raise web.HTTPBadRequest(text="Invalid JSON")
    item = await VAULT.add(
        str(payload.get("name", "")),
        str(payload.get("username", "")),
        str(payload.get("password", "")),
        str(payload.get("domain", "")),
    )
    return web.json_response(item, status=201)


async def delete_credential(request: web.Request) -> web.Response:
    await VAULT.delete(request.match_info["credential_id"])
    return web.Response(status=204)


async def list_shares(request: web.Request) -> web.Response:
    resource = _resource(request)
    raw = await _run_smbclient(resource, ["-L", resource["smb_host"]])
    shares = []
    for line in raw.splitlines():
        fields = line.split("|")
        if len(fields) < 2:
            continue
        kind = fields[0].strip().lower()
        name = fields[1].strip()
        comment = fields[2].strip() if len(fields) > 2 else ""
        if kind in {"disk", "disk share"} and name and not name.endswith("$"):
            shares.append({"name": name, "comment": comment})
    return web.json_response(shares)


def _parse_directory(raw: str) -> list[dict]:
    items = []
    for line in raw.splitlines():
        fields = line.split("|")
        if len(fields) < 3:
            continue
        attrs = fields[0].strip()
        size_text = fields[1].strip()
        name = fields[2].strip()
        if not name or name in {".", ".."}:
            continue
        is_dir = "D" in attrs.upper()
        try:
            size = int(size_text)
        except ValueError:
            size = None
        items.append({"name": name, "directory": is_dir, "size": None if is_dir else size})
    items.sort(key=lambda item: (not item["directory"], item["name"].lower()))
    return items


async def list_directory(request: web.Request) -> web.Response:
    resource = _resource(request)
    share = _safe_share(request.query.get("share", ""))
    path = _safe_path(request.query.get("path", ""))
    service = f"//{resource['smb_host']}/{share}"
    extra = [service]
    if path:
        extra += ["-D", path]
    extra += ["-c", "ls"]
    raw = await _run_smbclient(resource, extra)
    return web.json_response({"share": share, "path": path, "items": _parse_directory(raw)})


def _quoted_smb_name(value: str) -> str:
    if not value or any(ch in value for ch in '";\r\n'):
        raise web.HTTPBadRequest(text="This SMB filename cannot be downloaded safely")
    return f'"{value}"'


async def download_file(request: web.Request) -> web.StreamResponse:
    resource = _resource(request)
    share = _safe_share(request.query.get("share", ""))
    full_path = _safe_path(request.query.get("path", ""))
    if not full_path:
        raise web.HTTPBadRequest(text="A file path is required")
    parent, _, filename = full_path.rpartition("/")
    local_path = DOWNLOAD_DIR / f"{secrets.token_hex(12)}.bin"
    service = f"//{resource['smb_host']}/{share}"
    command = f"get {_quoted_smb_name(filename)} {_quoted_smb_name(str(local_path))}"
    extra = [service]
    if parent:
        extra += ["-D", parent]
    extra += ["-c", command]
    await _run_smbclient(resource, extra, timeout=120)
    if not local_path.exists():
        raise web.HTTPBadGateway(text="SMB download did not produce a local file")

    response = web.StreamResponse(
        status=200,
        headers={
            "Content-Type": "application/octet-stream",
            "Content-Disposition": f"attachment; filename*=UTF-8''{quote(filename, safe='')}",
            "Content-Length": str(local_path.stat().st_size),
            "Cache-Control": "no-store",
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


async def probe_smb_resource(resource: dict) -> dict:
    started = time.monotonic()
    try:
        _reader, writer = await asyncio.wait_for(
            asyncio.open_connection(resource["smb_host"], int(resource.get("smb_port", 445))),
            timeout=2,
        )
        writer.close()
        await writer.wait_closed()
        return {"online": True, "status": None, "latency_ms": round((time.monotonic() - started) * 1000)}
    except (OSError, asyncio.TimeoutError):
        return {"online": False, "status": None, "latency_ms": round((time.monotonic() - started) * 1000)}


SMB_PAGE = r'''<!doctype html>
<html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>SMB Browser</title>
<style>
:root{color-scheme:light dark;--bg:#f5f5f5;--surface:#fff;--text:#212121;--muted:#727272;--border:#ddd;--accent:#03a9f4}
@media(prefers-color-scheme:dark){:root{--bg:#111;--surface:#1c1c1c;--text:#eee;--muted:#aaa;--border:#383838}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--text);font:14px system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}.bar{height:52px;display:flex;align-items:center;gap:8px;padding:0 14px;background:var(--surface);border-bottom:1px solid var(--border);position:sticky;top:0}.title{font-weight:600}.crumbs{flex:1;white-space:nowrap;overflow:auto;color:var(--muted)}button{border:1px solid var(--border);background:var(--surface);color:var(--text);border-radius:6px;padding:7px 10px;cursor:pointer}.wrap{padding:14px;max-width:1100px;margin:auto}.list{background:var(--surface);border:1px solid var(--border);border-radius:8px;overflow:hidden}.row{display:grid;grid-template-columns:minmax(0,1fr) 110px 90px;gap:12px;align-items:center;padding:10px 12px;border-bottom:1px solid var(--border)}.row:last-child{border-bottom:0}.name{min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.name button{border:0;padding:0;background:transparent;color:var(--text);font:inherit;text-align:left}.meta{color:var(--muted);font-size:12px;text-align:right}.empty,.error{padding:24px;text-align:center;color:var(--muted)}.error{color:#d32f2f}.share{cursor:pointer}.icon{display:inline-block;width:24px} @media(max-width:600px){.row{grid-template-columns:minmax(0,1fr) 72px}.row .kind{display:none}}
</style></head>
<body><div class="bar"><button id="up" type="button">← Up</button><div class="title">SMB Browser</div><div id="crumbs" class="crumbs"></div><button id="refresh" type="button">↻</button></div><div class="wrap"><div id="content" class="list"><div class="empty">Loading…</div></div></div>
<script>
const resourceId='__RESOURCE_ID__';let share='';let path='';const $=id=>document.getElementById(id);const enc=v=>encodeURIComponent(v);
function api(rel){return '../../api/smb/'+resourceId+'/'+rel;}
function human(n){if(n==null)return'';const u=['B','KB','MB','GB','TB'];let i=0,v=Number(n);while(v>=1024&&i<u.length-1){v/=1024;i++;}return (i?v.toFixed(v<10?1:0):v)+' '+u[i];}
function setError(t){$('content').innerHTML='<div class="error"></div>';$('content').firstChild.textContent=t;}
function crumbs(){const bits=[];if(share)bits.push(share);if(path)bits.push(...path.split('/'));$('crumbs').textContent=bits.length?bits.join(' / '):'Shares';$('up').disabled=!share;}
async function load(){crumbs();$('content').innerHTML='<div class="empty">Loading…</div>';try{if(!share){const r=await fetch(api('shares'));if(!r.ok)throw new Error(await r.text());const data=await r.json();renderShares(data);}else{const r=await fetch(api('list?share='+enc(share)+'&path='+enc(path)));if(!r.ok)throw new Error(await r.text());const data=await r.json();renderItems(data.items||[]);}}catch(e){setError(e.message||String(e));}}
function renderShares(items){$('content').innerHTML='';if(!items.length){$('content').innerHTML='<div class="empty">No disk shares found.</div>';return;}for(const s of items){const row=document.createElement('div');row.className='row share';const name=document.createElement('div');name.className='name';name.innerHTML='<span class="icon">🗄️</span>';const b=document.createElement('button');b.textContent=s.name;b.onclick=()=>{share=s.name;path='';load();};name.append(b);const comment=document.createElement('div');comment.className='meta kind';comment.textContent=s.comment||'';const action=document.createElement('div');action.className='meta';action.textContent='Open';row.append(name,comment,action);$('content').append(row);}}
function renderItems(items){$('content').innerHTML='';if(!items.length){$('content').innerHTML='<div class="empty">This folder is empty.</div>';return;}for(const item of items){const row=document.createElement('div');row.className='row';const name=document.createElement('div');name.className='name';name.innerHTML='<span class="icon">'+(item.directory?'📁':'📄')+'</span>';const b=document.createElement('button');b.textContent=item.name;if(item.directory)b.onclick=()=>{path=[path,item.name].filter(Boolean).join('/');load();};else b.onclick=()=>{location.href=api('download?share='+enc(share)+'&path='+enc([path,item.name].filter(Boolean).join('/')));};name.append(b);const kind=document.createElement('div');kind.className='meta kind';kind.textContent=item.directory?'Folder':'File';const size=document.createElement('div');size.className='meta';size.textContent=item.directory?'':human(item.size);row.append(name,kind,size);$('content').append(row);}}
$('up').onclick=()=>{if(path){const p=path.split('/');p.pop();path=p.join('/');}else share='';load();};$('refresh').onclick=load;load();
</script></body></html>'''


async def smb_page(request: web.Request) -> web.Response:
    resource = _resource(request)
    page = SMB_PAGE.replace("__RESOURCE_ID__", resource["id"])
    return web.Response(text=page, content_type="text/html", headers={"Cache-Control": "no-store"})
