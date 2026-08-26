"""Browser-based VNC support for HA Remote Bridge using noVNC assets."""

from __future__ import annotations

import asyncio
import base64
import html
import mimetypes
import os
import socket
from pathlib import Path

from aiohttp import WSMsgType, web

import main

NOVNC_ROOT_CANDIDATES = (
    Path("/usr/share/novnc"),
    Path("/usr/share/webapps/novnc"),
)


def _novnc_root() -> Path:
    for candidate in NOVNC_ROOT_CANDIDATES:
        if (candidate / "core" / "rfb.js").is_file():
            return candidate
    raise web.HTTPServiceUnavailable(text="noVNC assets are not installed")


def validate_vnc_payload(payload: dict) -> tuple[str, str, int, bool]:
    name = str(payload.get("name", "")).strip()
    host = str(payload.get("vnc_host", "")).strip()
    view_only = bool(payload.get("vnc_view_only", False))
    try:
        port = int(payload.get("vnc_port", 5900))
    except (TypeError, ValueError):
        raise web.HTTPBadRequest(text="VNC port must be a number")

    if not name:
        raise web.HTTPBadRequest(text="Session Name is required")
    if len(name) > 100:
        raise web.HTTPBadRequest(text="Session Name is too long")
    if not host or any(ch in host for ch in "/\\\r\n\t "):
        raise web.HTTPBadRequest(text="A valid VNC hostname or IP address is required")
    if len(host) > 255:
        raise web.HTTPBadRequest(text="VNC host is too long")
    if not 1 <= port <= 65535:
        raise web.HTTPBadRequest(text="VNC port must be between 1 and 65535")
    return name, host, port, view_only


def vnc_resource_url(host: str, port: int) -> str:
    display_host = f"[{host}]" if ":" in host and not host.startswith("[") else host
    return f"vnc://{display_host}:{port}"


async def probe_vnc_resource(resource: dict) -> dict:
    started = asyncio.get_running_loop().time()
    try:
        reader, writer = await asyncio.wait_for(
            asyncio.open_connection(resource["vnc_host"], int(resource.get("vnc_port", 5900))),
            timeout=3,
        )
        del reader
        writer.close()
        await writer.wait_closed()
        return {
            "online": True,
            "status": None,
            "latency_ms": round((asyncio.get_running_loop().time() - started) * 1000),
        }
    except (asyncio.TimeoutError, OSError):
        return {
            "online": False,
            "status": None,
            "latency_ms": round((asyncio.get_running_loop().time() - started) * 1000),
        }


def _get_vnc_resource(resource_id: str) -> dict:
    resource = main.STORE.get(resource_id)
    if resource is None or resource.get("resource_type") != "vnc":
        raise web.HTTPNotFound(text="Unknown VNC resource")
    return resource


async def novnc_asset(request: web.Request) -> web.StreamResponse:
    """Serve packaged noVNC ES modules/assets under the current Ingress prefix."""
    root = _novnc_root().resolve()
    tail = request.match_info.get("tail", "").lstrip("/")
    candidate = (root / tail).resolve()
    root_prefix = str(root) + os.sep
    if not str(candidate).startswith(root_prefix) or not candidate.is_file():
        raise web.HTTPNotFound(text="Unknown noVNC asset")

    content_type, _ = mimetypes.guess_type(str(candidate))
    response = web.FileResponse(candidate)
    if content_type:
        response.content_type = content_type
    # noVNC recommends revalidation so updated HTML and ES modules cannot get out of sync.
    response.headers["Cache-Control"] = "no-cache"
    return response


async def vnc_page(request: web.Request) -> web.Response:
    resource = _get_vnc_resource(request.match_info["resource_id"])
    session_name = html.escape(str(resource.get("name", "VNC")))
    target_host = html.escape(str(resource["vnc_host"]))
    target_port = int(resource.get("vnc_port", 5900))
    view_only = "true" if resource.get("vnc_view_only", False) else "false"

    page = f'''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=1,user-scalable=no">
<title>{session_name}</title>
<style>
html,body{{width:100%;height:100%;margin:0;background:#111;overflow:hidden;font-family:Roboto,system-ui,sans-serif}}
body{{display:flex;flex-direction:column}}
#toolbar{{height:38px;flex:0 0 38px;display:flex;align-items:center;gap:7px;padding:0 9px;background:#20272d;color:#fff;border-bottom:1px solid #39434b;box-sizing:border-box}}
#toolbar button{{height:27px;border:1px solid #59646d;border-radius:5px;padding:0 9px;background:#303a42;color:#fff;cursor:pointer;font:inherit;font-size:11px}}
#toolbar button:hover{{background:#3c4851}}
#toolbar .spacer{{flex:1}}
#focus-state{{font-size:10px;color:#aeb8bf;white-space:nowrap}}
#screen{{min-width:0;min-height:0;flex:1;display:flex;align-items:center;justify-content:center;outline:none;position:relative}}
#screen:focus-within{{box-shadow:inset 0 0 0 2px #03a9f4}}
#status{{position:fixed;left:12px;top:50px;z-index:20;background:#172027dd;color:#fff;padding:7px 10px;border-radius:6px;font-size:12px;box-shadow:0 2px 8px #0005}}
#credentials{{display:none;position:fixed;inset:0;z-index:30;background:#0008;align-items:center;justify-content:center}}
#credentials.open{{display:flex}}
.card{{width:min(360px,calc(100vw - 30px));background:#fff;color:#222;border-radius:10px;padding:18px;box-shadow:0 18px 60px #0008}}
.card h2{{margin:0 0 4px;font-size:18px}} .card p{{margin:0 0 14px;color:#666;font-size:12px}}
.card input{{width:100%;box-sizing:border-box;padding:9px 10px;border:1px solid #ccc;border-radius:5px;font:inherit}}
.actions{{display:flex;justify-content:flex-end;gap:8px;margin-top:12px}}
.card button{{border:1px solid #ccc;border-radius:5px;padding:8px 12px;background:#fff;cursor:pointer}} .card button.primary{{background:#03a9f4;border-color:#03a9f4;color:#fff}}
</style>
</head>
<body>
<div id="toolbar">
  <button id="focus-keyboard" type="button" title="Send keyboard input to the remote desktop">⌨ Keyboard</button>
  <button id="ctrl-alt-del" type="button" title="Send Ctrl-Alt-Delete">Ctrl-Alt-Del</button>
  <div class="spacer"></div>
  <span id="focus-state">Click the desktop to capture keyboard</span>
</div>
<div id="screen" tabindex="0"></div>
<div id="status">Connecting to {target_host}:{target_port}…</div>
<div id="credentials"><form id="credentials-form" class="card"><h2>VNC password</h2><p>This password is sent only to the active VNC server and is not stored by HA Remote Bridge.</p><input id="password" type="password" autocomplete="current-password" autofocus><div class="actions"><button class="primary" type="submit">Connect</button></div></form></div>
<script type="module">
const assetBase = new URL('../../novnc-assets/', window.location.href);
const {{default:RFB}} = await import(new URL('core/rfb.js', assetBase));
const screen = document.getElementById('screen');
const status = document.getElementById('status');
const credentials = document.getElementById('credentials');
const password = document.getElementById('password');
const focusState = document.getElementById('focus-state');
const ws = new URL('websockify', window.location.href);
ws.protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
let rfb = new RFB(screen, ws.href, {{shared:true}});

// Prefer responsiveness over maximum image quality. Keep the remote framebuffer size
// stable and scale it locally; remote resize requests can be expensive on many servers.
rfb.scaleViewport = true;
rfb.resizeSession = false;
rfb.clipViewport = false;
rfb.qualityLevel = 5;
rfb.compressionLevel = 1;
rfb.focusOnClick = true;
rfb.viewOnly = {view_only};

function focusRemote() {{
  try {{ screen.focus({{preventScroll:true}}); }} catch (_) {{ screen.focus(); }}
  try {{ rfb.focus({{preventScroll:true}}); }} catch (_) {{ rfb.focus(); }}
  focusState.textContent = rfb.viewOnly ? 'View only' : 'Keyboard active';
}}

screen.addEventListener('pointerdown', focusRemote, {{passive:true}});
screen.addEventListener('touchstart', focusRemote, {{passive:true}});
document.getElementById('focus-keyboard').addEventListener('click', focusRemote);
document.getElementById('ctrl-alt-del').addEventListener('click', () => {{ focusRemote(); rfb.sendCtrlAltDel(); }});
window.addEventListener('focus', () => {{ if (!rfb.viewOnly) focusRemote(); }});
document.addEventListener('visibilitychange', () => {{ if (!document.hidden && !rfb.viewOnly) setTimeout(focusRemote, 0); }});

rfb.addEventListener('connect', () => {{
  status.textContent = 'Connected';
  setTimeout(() => status.style.display='none', 900);
  if (!rfb.viewOnly) setTimeout(focusRemote, 0);
}});
rfb.addEventListener('disconnect', e => {{ status.style.display='block'; status.textContent = e.detail.clean ? 'Disconnected' : 'Connection lost'; focusState.textContent='Disconnected'; }});
rfb.addEventListener('credentialsrequired', () => {{ credentials.classList.add('open'); password.focus(); }});
rfb.addEventListener('securityfailure', e => {{ status.style.display='block'; status.textContent = e.detail.reason || 'VNC authentication failed'; }});
document.getElementById('credentials-form').addEventListener('submit', e => {{ e.preventDefault(); rfb.sendCredentials({{password:password.value}}); password.value=''; credentials.classList.remove('open'); setTimeout(focusRemote, 0); }});
</script>
</body>
</html>'''
    return web.Response(text=page, content_type="text/html", headers={"Cache-Control": "no-store"})


async def vnc_websocket(request: web.Request) -> web.WebSocketResponse:
    """Bridge one configured noVNC WebSocket to its VNC TCP endpoint."""
    resource = _get_vnc_resource(request.match_info["resource_id"])
    try:
        reader, writer = await asyncio.wait_for(
            asyncio.open_connection(resource["vnc_host"], int(resource.get("vnc_port", 5900))),
            timeout=5,
        )
    except (asyncio.TimeoutError, OSError) as err:
        raise web.HTTPBadGateway(text=f"Unable to connect to VNC server: {err}") from err

    # Avoid Nagle delays for small keyboard/mouse RFB messages.
    raw_socket = writer.get_extra_info("socket")
    if raw_socket is not None:
        try:
            raw_socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        except OSError:
            pass

    browser_ws = web.WebSocketResponse(protocols=("binary", "base64"), max_msg_size=0, heartbeat=30)
    await browser_ws.prepare(request)
    use_base64 = browser_ws.ws_protocol == "base64"
    main.LOGGER.info(
        "VNC session opened for %s -> %s:%s (protocol=%s)",
        resource.get("name", resource["id"]),
        resource["vnc_host"],
        resource.get("vnc_port", 5900),
        browser_ws.ws_protocol or "binary",
    )

    async def browser_to_vnc() -> None:
        async for message in browser_ws:
            if message.type == WSMsgType.BINARY:
                writer.write(message.data)
                await writer.drain()
            elif message.type == WSMsgType.TEXT:
                data = base64.b64decode(message.data) if use_base64 else message.data.encode("latin1")
                writer.write(data)
                await writer.drain()
            elif message.type in {WSMsgType.CLOSE, WSMsgType.CLOSED, WSMsgType.ERROR}:
                break

    async def vnc_to_browser() -> None:
        while not browser_ws.closed:
            data = await reader.read(256 * 1024)
            if not data:
                break
            if use_base64:
                await browser_ws.send_str(base64.b64encode(data).decode("ascii"))
            else:
                await browser_ws.send_bytes(data)

    try:
        tasks = [asyncio.create_task(browser_to_vnc()), asyncio.create_task(vnc_to_browser())]
        done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
        for task in pending:
            task.cancel()
        await asyncio.gather(*pending, return_exceptions=True)
        for task in done:
            if not task.cancelled():
                task.exception()
    finally:
        writer.close()
        try:
            await writer.wait_closed()
        except OSError:
            pass
        if not browser_ws.closed:
            await browser_ws.close()
        main.LOGGER.info("VNC session closed for %s", resource.get("name", resource["id"]))
    return browser_ws
