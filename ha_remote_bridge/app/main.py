"""HA Remote Bridge Home Assistant App.

Provides an Ingress-only UI and reverse proxy for selected local HTTP/HTTPS
resources. Resource configuration is persisted in /data/resources.json.
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
import secrets
from http.cookies import SimpleCookie
from pathlib import Path
from urllib.parse import urljoin, urlparse

from aiohttp import ClientError, ClientSession, ClientTimeout, WSMsgType, web
from multidict import CIMultiDict

LOGGER = logging.getLogger("ha_remote_bridge")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

PORT = 8099
DATA_FILE = Path("/data/resources.json")
INGRESS_REMOTE = "172.30.32.2"
COOKIE_PREFIX = "hrb_"

HOP_BY_HOP = {
    "connection",
    "keep-alive",
    "proxy-authenticate",
    "proxy-authorization",
    "te",
    "trailer",
    "transfer-encoding",
    "upgrade",
    "host",
    "content-length",
}

REQUEST_HEADERS_TO_DROP = HOP_BY_HOP | {
    "authorization",
    "cookie",
    "origin",
    "referer",
}

RESPONSE_HEADERS_TO_DROP = HOP_BY_HOP | {
    "content-length",
    "content-encoding",
    "set-cookie",
    "content-security-policy",
    "content-security-policy-report-only",
    "x-frame-options",
}


class ResourceStore:
    """Persistent resource configuration."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self._lock = asyncio.Lock()
        self.resources: list[dict] = []

    async def load(self) -> None:
        """Load resources from persistent storage."""
        if not self.path.exists():
            self.resources = []
            return

        try:
            self.resources = json.loads(self.path.read_text(encoding="utf-8"))
            if not isinstance(self.resources, list):
                raise ValueError("resource store must contain a list")
        except (OSError, ValueError, json.JSONDecodeError) as err:
            LOGGER.error("Unable to read %s: %s", self.path, err)
            self.resources = []

    async def save(self) -> None:
        """Persist resources atomically."""
        async with self._lock:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            temp = self.path.with_suffix(".tmp")
            temp.write_text(
                json.dumps(self.resources, indent=2, sort_keys=True),
                encoding="utf-8",
            )
            temp.replace(self.path)

    def get(self, resource_id: str) -> dict | None:
        """Return a resource by id."""
        return next((item for item in self.resources if item["id"] == resource_id), None)


STORE = ResourceStore(DATA_FILE)
CLIENT: ClientSession | None = None


def ingress_prefix(request: web.Request) -> str:
    """Return the external Home Assistant Ingress prefix."""
    value = request.headers.get("X-Ingress-Path", "")
    if not value:
        return "/"
    return value.rstrip("/") + "/"


def validate_resource_payload(payload: dict) -> tuple[str, str, bool]:
    """Validate and normalize a resource payload."""
    name = str(payload.get("name", "")).strip()
    url = str(payload.get("url", "")).strip().rstrip("/")
    verify_ssl = bool(payload.get("verify_ssl", True))

    parsed = urlparse(url)
    if not name:
        raise web.HTTPBadRequest(text="Resource name is required")
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise web.HTTPBadRequest(text="A valid HTTP or HTTPS URL is required")
    if parsed.username or parsed.password:
        raise web.HTTPBadRequest(text="Credentials in target URLs are not supported")

    return name, url, verify_ssl


@web.middleware
async def ingress_only(request: web.Request, handler):
    """Only accept requests delivered through Home Assistant Ingress."""
    if request.remote not in {INGRESS_REMOTE, "127.0.0.1", "::1"}:
        LOGGER.warning("Rejected non-Ingress request from %s", request.remote)
        raise web.HTTPForbidden(text="HA Remote Bridge is available through Home Assistant Ingress only")
    return await handler(request)


async def index(request: web.Request) -> web.Response:
    """Serve the resource manager UI."""
    return web.Response(text=INDEX_HTML, content_type="text/html")


async def list_resources(request: web.Request) -> web.Response:
    """Return configured resources."""
    return web.json_response(STORE.resources)


async def add_resource(request: web.Request) -> web.Response:
    """Create a resource."""
    try:
        payload = await request.json()
    except (json.JSONDecodeError, ValueError):
        raise web.HTTPBadRequest(text="Invalid JSON")

    name, url, verify_ssl = validate_resource_payload(payload)
    resource = {
        "id": secrets.token_hex(8),
        "name": name,
        "url": url,
        "verify_ssl": verify_ssl,
    }
    STORE.resources.append(resource)
    await STORE.save()
    LOGGER.info("Added resource %s -> %s", name, url)
    return web.json_response(resource, status=201)


async def delete_resource(request: web.Request) -> web.Response:
    """Delete a resource."""
    resource_id = request.match_info["resource_id"]
    before = len(STORE.resources)
    STORE.resources = [item for item in STORE.resources if item["id"] != resource_id]
    if len(STORE.resources) == before:
        raise web.HTTPNotFound(text="Unknown resource")
    await STORE.save()
    return web.Response(status=204)


def upstream_url(resource: dict, tail: str, query: str) -> str:
    """Build an upstream URL from a proxy request."""
    base = resource["url"].rstrip("/") + "/"
    target = urljoin(base, tail)
    if query:
        target += "?" + query
    return target


def resource_cookie_prefix(resource_id: str) -> str:
    """Return the browser-side prefix used to isolate a target's cookies."""
    return f"{COOKIE_PREFIX}{resource_id}_"


def upstream_cookie_header(request: web.Request, resource_id: str) -> str | None:
    """Extract only this resource's cookies and restore original cookie names."""
    raw = request.headers.get("Cookie", "")
    if not raw:
        return None

    parsed = SimpleCookie()
    try:
        parsed.load(raw)
    except Exception:  # malformed browser cookies should not break the proxy
        return None

    prefix = resource_cookie_prefix(resource_id)
    values = []
    for name, morsel in parsed.items():
        if name.startswith(prefix):
            original = name[len(prefix):]
            if original:
                values.append(f"{original}={morsel.value}")
    return "; ".join(values) or None


def filtered_request_headers(
    request: web.Request,
    target: str,
    resource_id: str,
) -> dict[str, str]:
    """Prepare safe request headers for the upstream resource."""
    headers = {
        key: value
        for key, value in request.headers.items()
        if key.lower() not in REQUEST_HEADERS_TO_DROP
        and not key.lower().startswith("sec-fetch-")
    }
    parsed = urlparse(target)
    origin = f"{parsed.scheme}://{parsed.netloc}"
    headers["Origin"] = origin
    headers["Referer"] = target
    headers["X-Forwarded-Host"] = request.host
    headers["X-Forwarded-Proto"] = request.scheme

    cookie = upstream_cookie_header(request, resource_id)
    if cookie:
        headers["Cookie"] = cookie

    return headers


def add_rewritten_cookies(
    headers: CIMultiDict,
    upstream,
    request: web.Request,
    resource_id: str,
) -> None:
    """Rewrite upstream cookies so they are isolated to one bridged resource."""
    bridge_path = f"{ingress_prefix(request)}proxy/{resource_id}/"
    prefix = resource_cookie_prefix(resource_id)

    for raw_cookie in upstream.headers.getall("Set-Cookie", []):
        parsed = SimpleCookie()
        try:
            parsed.load(raw_cookie)
        except Exception:
            LOGGER.debug("Unable to parse upstream Set-Cookie: %s", raw_cookie)
            continue

        for original_name, morsel in parsed.items():
            rewritten = SimpleCookie()
            browser_name = prefix + original_name
            rewritten[browser_name] = morsel.value
            output = rewritten[browser_name]
            output["path"] = bridge_path
            output["httponly"] = bool(morsel["httponly"])
            output["secure"] = bool(morsel["secure"])
            if morsel["samesite"]:
                output["samesite"] = morsel["samesite"]
            if morsel["expires"]:
                output["expires"] = morsel["expires"]
            if morsel["max-age"]:
                output["max-age"] = morsel["max-age"]
            headers.add("Set-Cookie", output.OutputString())


def copy_response_headers(upstream) -> CIMultiDict:
    """Copy safe upstream headers while preserving duplicates."""
    headers = CIMultiDict()
    for key, value in upstream.headers.items():
        if key.lower() not in RESPONSE_HEADERS_TO_DROP:
            headers.add(key, value)
    return headers


def rewrite_location(
    location: str,
    target: str,
    resource: dict,
    resource_id: str,
    prefix: str,
) -> str:
    """Rewrite upstream redirects back through Ingress."""
    resolved = urljoin(target, location)
    resolved_parts = urlparse(resolved)
    base_parts = urlparse(resource["url"])
    if resolved_parts.netloc != base_parts.netloc:
        return location

    path = resolved_parts.path.lstrip("/")
    query = f"?{resolved_parts.query}" if resolved_parts.query else ""
    return f"{prefix}proxy/{resource_id}/{path}{query}"


def bridge_runtime_script(prefix: str, resource_id: str, target_url: str) -> str:
    """Return a small browser shim for root-relative fetch/XHR/WebSocket URLs."""
    bridge = f"{prefix}proxy/{resource_id}"
    target = urlparse(target_url)
    target_origin = f"{target.scheme}://{target.netloc}"

    return f"""<script data-ha-remote-bridge>
(() => {{
  const bridge = {json.dumps(bridge)};
  const targetOrigin = {json.dumps(target_origin)};
  const rewrite = (value, websocket = false) => {{
    if (typeof value !== 'string') return value;
    try {{
      const u = new URL(value, window.location.href);
      const target = new URL(targetOrigin);
      const sameTarget = u.host === target.host;
      const rootRelative = value.startsWith('/');
      if (sameTarget || rootRelative) {{
        const scheme = websocket ? (window.location.protocol === 'https:' ? 'wss:' : 'ws:') : window.location.protocol;
        return scheme + '//' + window.location.host + bridge + u.pathname + u.search + u.hash;
      }}
    }} catch (_) {{}}
    return value;
  }};

  const nativeFetch = window.fetch;
  window.fetch = function(input, init) {{
    if (typeof input === 'string') input = rewrite(input);
    return nativeFetch.call(this, input, init);
  }};

  const nativeOpen = XMLHttpRequest.prototype.open;
  XMLHttpRequest.prototype.open = function(method, url, ...rest) {{
    return nativeOpen.call(this, method, rewrite(url), ...rest);
  }};

  const NativeWebSocket = window.WebSocket;
  window.WebSocket = function(url, protocols) {{
    const rewritten = rewrite(url, true);
    return protocols === undefined ? new NativeWebSocket(rewritten) : new NativeWebSocket(rewritten, protocols);
  }};
  window.WebSocket.prototype = NativeWebSocket.prototype;
}})();
</script>"""


def rewrite_text_body(
    body: bytes,
    content_type: str,
    resource: dict,
    resource_id: str,
    prefix: str,
) -> bytes:
    """Best-effort rewrite of HTML/CSS root-relative URLs."""
    charset = "utf-8"
    match = re.search(r"charset=([^;\s]+)", content_type, flags=re.IGNORECASE)
    if match:
        charset = match.group(1).strip("\"'")

    try:
        text = body.decode(charset, errors="replace")
    except LookupError:
        charset = "utf-8"
        text = body.decode(charset, errors="replace")

    bridge = f"{prefix}proxy/{resource_id}"
    lowered = content_type.lower()

    if "text/html" in lowered:
        text = re.sub(
            r"(?i)(href|src|action|poster)=(\"|')/(?!/)",
            lambda m: f"{m.group(1)}={m.group(2)}{bridge}/",
            text,
        )
        shim = bridge_runtime_script(prefix, resource_id, resource["url"])
        if re.search(r"(?i)<head[^>]*>", text):
            text = re.sub(r"(?i)(<head[^>]*>)", r"\1" + shim, text, count=1)
        else:
            text = shim + text

    if "text/css" in lowered or "text/html" in lowered:
        text = re.sub(
            r"(?i)url\((['\"]?)/(?!/)",
            lambda m: f"url({m.group(1)}{bridge}/",
            text,
        )

    return text.encode(charset, errors="replace")


async def proxy_websocket(
    request: web.Request,
    resource: dict,
    resource_id: str,
    tail: str,
) -> web.WebSocketResponse:
    """Bridge a browser WebSocket to the selected local resource."""
    assert CLIENT is not None
    target = upstream_url(resource, tail, request.query_string)
    parsed = urlparse(target)
    ws_scheme = "wss" if parsed.scheme == "https" else "ws"
    ws_target = parsed._replace(scheme=ws_scheme).geturl()
    protocols = [
        item.strip()
        for item in request.headers.get("Sec-WebSocket-Protocol", "").split(",")
        if item.strip()
    ]

    browser_ws = web.WebSocketResponse(protocols=protocols)
    await browser_ws.prepare(request)

    try:
        async with CLIENT.ws_connect(
            ws_target,
            headers=filtered_request_headers(request, target, resource_id),
            protocols=protocols,
            ssl=None if resource.get("verify_ssl", True) else False,
            timeout=20,
        ) as upstream_ws:

            async def browser_to_upstream() -> None:
                async for message in browser_ws:
                    if message.type == WSMsgType.TEXT:
                        await upstream_ws.send_str(message.data)
                    elif message.type == WSMsgType.BINARY:
                        await upstream_ws.send_bytes(message.data)
                    elif message.type in {WSMsgType.CLOSE, WSMsgType.CLOSED, WSMsgType.ERROR}:
                        break

            async def upstream_to_browser() -> None:
                async for message in upstream_ws:
                    if message.type == WSMsgType.TEXT:
                        await browser_ws.send_str(message.data)
                    elif message.type == WSMsgType.BINARY:
                        await browser_ws.send_bytes(message.data)
                    elif message.type in {WSMsgType.CLOSE, WSMsgType.CLOSED, WSMsgType.ERROR}:
                        break

            tasks = [
                asyncio.create_task(browser_to_upstream()),
                asyncio.create_task(upstream_to_browser()),
            ]
            done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
            for task in pending:
                task.cancel()
            await asyncio.gather(*pending, return_exceptions=True)
            for task in done:
                if task.exception():
                    raise task.exception()
    except (ClientError, asyncio.TimeoutError) as err:
        LOGGER.warning("WebSocket bridge failed for %s: %r", resource["name"], err)
    finally:
        if not browser_ws.closed:
            await browser_ws.close()

    return browser_ws


async def stream_upstream_response(
    request: web.Request,
    upstream,
    resource_id: str,
) -> web.StreamResponse:
    """Stream long-lived responses such as Server-Sent Events."""
    headers = copy_response_headers(upstream)
    add_rewritten_cookies(headers, upstream, request, resource_id)
    response = web.StreamResponse(
        status=upstream.status,
        reason=upstream.reason,
        headers=headers,
    )
    await response.prepare(request)

    try:
        async for chunk in upstream.content.iter_any():
            if chunk:
                await response.write(chunk)
    except (ConnectionResetError, asyncio.CancelledError):
        pass
    finally:
        try:
            await response.write_eof()
        except (ConnectionResetError, RuntimeError):
            pass

    return response


async def proxy(request: web.Request) -> web.StreamResponse:
    """Reverse proxy a request to a configured local resource."""
    assert CLIENT is not None
    resource_id = request.match_info["resource_id"]
    tail = request.match_info.get("tail", "")
    resource = STORE.get(resource_id)
    if resource is None:
        raise web.HTTPNotFound(text="Unknown resource")

    if request.headers.get("Upgrade", "").lower() == "websocket":
        return await proxy_websocket(request, resource, resource_id, tail)

    target = upstream_url(resource, tail, request.query_string)
    body = await request.read() if request.can_read_body else None

    try:
        upstream = await CLIENT.request(
            request.method,
            target,
            headers=filtered_request_headers(request, target, resource_id),
            data=body,
            allow_redirects=False,
            ssl=None if resource.get("verify_ssl", True) else False,
            timeout=ClientTimeout(total=None, connect=15, sock_connect=15, sock_read=None),
        )

        try:
            content_type = upstream.headers.get("Content-Type", "")
            if "text/event-stream" in content_type.lower():
                return await stream_upstream_response(request, upstream, resource_id)

            raw_body = await upstream.read()
            headers = copy_response_headers(upstream)
            add_rewritten_cookies(headers, upstream, request, resource_id)

            prefix = ingress_prefix(request)
            if upstream.headers.get("Location"):
                headers["Location"] = rewrite_location(
                    upstream.headers["Location"],
                    target,
                    resource,
                    resource_id,
                    prefix,
                )

            if raw_body and (
                "text/html" in content_type.lower()
                or "text/css" in content_type.lower()
            ):
                raw_body = rewrite_text_body(
                    raw_body,
                    content_type,
                    resource,
                    resource_id,
                    prefix,
                )

            return web.Response(
                status=upstream.status,
                reason=upstream.reason,
                headers=headers,
                body=b"" if request.method == "HEAD" else raw_body,
            )
        finally:
            upstream.release()
    except (ClientError, asyncio.TimeoutError) as err:
        LOGGER.warning("Proxy request failed for %s: %r", resource["name"], err)
        raise web.HTTPBadGateway(text=f"Unable to reach {resource['name']}: {err}") from err


async def health(request: web.Request) -> web.Response:
    """Health endpoint for local diagnostics."""
    return web.json_response({"status": "ok", "resources": len(STORE.resources)})


async def on_startup(app: web.Application) -> None:
    """Initialize persistent state and HTTP client."""
    global CLIENT
    await STORE.load()
    CLIENT = ClientSession(timeout=ClientTimeout(total=None, connect=15, sock_read=None))
    LOGGER.info("Loaded %d configured resource(s)", len(STORE.resources))


async def on_cleanup(app: web.Application) -> None:
    """Close HTTP resources."""
    global CLIENT
    if CLIENT is not None:
        await CLIENT.close()
        CLIENT = None


INDEX_HTML = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>HA Remote Bridge</title>
  <style>
    :root { color-scheme: light dark; font-family: system-ui, sans-serif; }
    body { margin: 0; background: var(--primary-background-color, #fafafa); color: var(--primary-text-color, #222); }
    main { max-width: 900px; margin: 0 auto; padding: 24px; }
    h1 { margin: 0 0 4px; font-size: 28px; }
    .subtitle { opacity: .7; margin: 0 0 24px; }
    .card { background: var(--card-background-color, #fff); border-radius: 12px; padding: 18px; margin-bottom: 16px; box-shadow: 0 2px 8px #0002; }
    .row { display: flex; gap: 12px; align-items: center; justify-content: space-between; }
    .resource-name { font-weight: 650; font-size: 17px; }
    .resource-url { opacity: .7; font-size: 13px; overflow-wrap: anywhere; margin-top: 3px; }
    .actions { display: flex; gap: 8px; flex-wrap: wrap; }
    button, .button { border: 0; border-radius: 8px; padding: 10px 14px; cursor: pointer; text-decoration: none; font: inherit; background: var(--primary-color, #03a9f4); color: white; }
    button.danger { background: #c62828; }
    form { display: grid; grid-template-columns: 1fr 2fr auto auto; gap: 10px; align-items: end; }
    label { font-size: 12px; opacity: .8; display: grid; gap: 5px; }
    input[type=text], input[type=url] { padding: 10px; border: 1px solid #8887; border-radius: 8px; background: transparent; color: inherit; font: inherit; }
    .empty { opacity: .65; text-align: center; padding: 28px 4px; }
    .note { font-size: 13px; opacity: .7; }
    @media (max-width: 700px) {
      main { padding: 14px; }
      form { grid-template-columns: 1fr; }
      .row { align-items: flex-start; flex-direction: column; }
    }
  </style>
</head>
<body>
<main>
  <h1>HA Remote Bridge</h1>
  <p class="subtitle">Secure access to local resources through Home Assistant Ingress.</p>

  <section class="card">
    <form id="add-form">
      <label>Name<input id="name" type="text" required placeholder="Kitchen ESPHome"></label>
      <label>Local URL<input id="url" type="url" required placeholder="http://192.168.1.50"></label>
      <label><span>Verify SSL</span><input id="verify" type="checkbox" checked></label>
      <button type="submit">Add resource</button>
    </form>
    <p class="note">HTTP/HTTPS, target login cookies, WebSockets and Server-Sent Events are supported. Credentials embedded in URLs are rejected.</p>
  </section>

  <section id="resources"></section>
</main>
<script>
  const base = window.location.pathname.endsWith('/') ? window.location.pathname : window.location.pathname + '/';
  const api = (path) => base + path;

  async function load() {
    const response = await fetch(api('api/resources'));
    const resources = await response.json();
    const host = document.getElementById('resources');
    host.innerHTML = '';
    if (!resources.length) {
      host.innerHTML = '<div class="card empty">No resources configured yet.</div>';
      return;
    }
    for (const resource of resources) {
      const card = document.createElement('div');
      card.className = 'card row';
      const info = document.createElement('div');
      const name = document.createElement('div');
      name.className = 'resource-name';
      name.textContent = resource.name;
      const url = document.createElement('div');
      url.className = 'resource-url';
      url.textContent = resource.url;
      info.append(name, url);

      const actions = document.createElement('div');
      actions.className = 'actions';
      const open = document.createElement('a');
      open.className = 'button';
      open.textContent = 'Open';
      open.href = api('proxy/' + resource.id + '/');
      const remove = document.createElement('button');
      remove.className = 'danger';
      remove.textContent = 'Delete';
      remove.onclick = async () => {
        if (!confirm('Delete ' + resource.name + '?')) return;
        await fetch(api('api/resources/' + resource.id), {method: 'DELETE'});
        load();
      };
      actions.append(open, remove);
      card.append(info, actions);
      host.append(card);
    }
  }

  document.getElementById('add-form').addEventListener('submit', async (event) => {
    event.preventDefault();
    const response = await fetch(api('api/resources'), {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({
        name: document.getElementById('name').value,
        url: document.getElementById('url').value,
        verify_ssl: document.getElementById('verify').checked,
      }),
    });
    if (!response.ok) {
      alert(await response.text());
      return;
    }
    event.target.reset();
    document.getElementById('verify').checked = true;
    load();
  });

  load();
</script>
</body>
</html>
"""


def create_app() -> web.Application:
    """Create the aiohttp application."""
    app = web.Application(middlewares=[ingress_only], client_max_size=32 * 1024 * 1024)
    app.router.add_get("/", index)
    app.router.add_get("/health", health)
    app.router.add_get("/api/resources", list_resources)
    app.router.add_post("/api/resources", add_resource)
    app.router.add_delete("/api/resources/{resource_id}", delete_resource)
    app.router.add_route("*", "/proxy/{resource_id}/{tail:.*}", proxy)
    app.on_startup.append(on_startup)
    app.on_cleanup.append(on_cleanup)
    return app


if __name__ == "__main__":
    web.run_app(create_app(), host="0.0.0.0", port=PORT, access_log=LOGGER)
