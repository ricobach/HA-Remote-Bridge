"""Per-Web virtual Host/SNI support for HA Remote Bridge.

A Web resource may connect to an IP/port while presenting a different virtual
hostname to the upstream application. The configured resource URL remains the
transport destination; ``virtual_host`` controls the HTTP Host header and,
for TLS connections, the SNI/server hostname.
"""

from __future__ import annotations

import json
import re
from urllib.parse import urlparse, urlunparse

from aiohttp import ClientSession, web
from multidict import CIMultiDict

import launcher
import main

_INSTALLED = False
_SNI_SENTINEL = "X-HA-Remote-Bridge-Upstream-SNI"
_HOST_RE = re.compile(r"^(?=.{1,253}$)(?:[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?\.)*[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?$", re.ASCII)


def _clean_virtual_host(value: object) -> str | None:
    value = str(value or "").strip().rstrip(".")
    if not value:
        return None
    if "://" in value or any(ch in value for ch in "/\\@?#: \t\r\n"):
        raise web.HTTPBadRequest(text="Virtual host / SNI must be a hostname only, for example www.example.com")
    try:
        ascii_name = value.encode("idna").decode("ascii")
    except UnicodeError as err:
        raise web.HTTPBadRequest(text="Invalid virtual host / SNI hostname") from err
    if not _HOST_RE.fullmatch(ascii_name):
        raise web.HTTPBadRequest(text="Invalid virtual host / SNI hostname")
    return ascii_name.lower()


def _is_web_resource(resource: dict | None, payload: dict | None = None) -> bool:
    resource_type = str((payload or {}).get("resource_type", "") or (resource or {}).get("resource_type", "")).strip().lower()
    return resource_type not in {"ssh", "smb", "vnc"}


def _logical_netloc(target: str, virtual_host: str) -> str:
    parsed = urlparse(target)
    port = parsed.port
    default = 443 if parsed.scheme in {"https", "wss"} else 80
    return virtual_host if not port or port == default else f"{virtual_host}:{port}"


def _apply_resource_setting(resource: dict, virtual_host: str | None) -> None:
    if virtual_host:
        resource["virtual_host"] = virtual_host
    else:
        resource.pop("virtual_host", None)


def _response_resource(response: web.StreamResponse) -> dict | None:
    if not isinstance(response, web.Response) or not response.body:
        return None
    try:
        data = json.loads(response.body.decode(response.charset or "utf-8"))
    except Exception:
        return None
    if not isinstance(data, dict) or not data.get("id"):
        return None
    return main.STORE.get(str(data["id"]))


def install() -> None:
    """Install virtual-host storage, headers, SNI and browser compatibility."""
    global _INSTALLED
    if _INSTALLED:
        return
    _INSTALLED = True

    previous_add_resource = main.add_resource
    previous_update_resource = launcher.update_resource
    previous_headers = main.filtered_request_headers
    previous_location = main.rewrite_location
    previous_bridge_script = main.bridge_runtime_script
    previous_rewrite_text = main.rewrite_text_body
    previous_client_request = ClientSession._request

    async def add_resource(request: web.Request) -> web.StreamResponse:
        try:
            payload = await request.json()
        except Exception:
            return await previous_add_resource(request)
        virtual_host = _clean_virtual_host(payload.get("virtual_host")) if _is_web_resource(None, payload) else None
        response = await previous_add_resource(request)
        resource = _response_resource(response)
        if resource is not None and _is_web_resource(resource):
            _apply_resource_setting(resource, virtual_host)
            await main.STORE.save()
            return web.json_response(resource, status=getattr(response, "status", 201))
        return response

    async def update_resource(request: web.Request) -> web.StreamResponse:
        resource_id = request.match_info.get("resource_id", "")
        existing = main.STORE.get(resource_id)
        try:
            payload = await request.json()
        except Exception:
            return await previous_update_resource(request)
        is_web = _is_web_resource(existing, payload)
        virtual_host = _clean_virtual_host(payload.get("virtual_host")) if is_web else None
        response = await previous_update_resource(request)
        resource = main.STORE.get(resource_id)
        if resource is not None and is_web:
            _apply_resource_setting(resource, virtual_host)
            await main.STORE.save()
            return web.json_response(resource, status=getattr(response, "status", 200))
        return response

    def filtered_request_headers(request: web.Request, target: str, resource_id: str) -> dict[str, str]:
        headers = previous_headers(request, target, resource_id)
        resource = main.STORE.get(resource_id)
        virtual_host = str((resource or {}).get("virtual_host", "")).strip().lower()
        if not virtual_host:
            return headers

        parsed = urlparse(target)
        logical_netloc = _logical_netloc(target, virtual_host)
        logical_origin = f"{parsed.scheme}://{logical_netloc}"
        logical_target = urlunparse((parsed.scheme, logical_netloc, parsed.path, parsed.params, parsed.query, parsed.fragment))

        # Host is deliberately the configured virtual hostname without a port;
        # this gives reverse proxies an exact server-name value even when the
        # transport endpoint uses a non-standard port.
        headers["Host"] = virtual_host
        headers["Origin"] = logical_origin
        headers["Referer"] = logical_target
        # Private in-process marker. ClientSession._request removes this before
        # transmission and turns it into TLS server_hostname/SNI.
        headers[_SNI_SENTINEL] = virtual_host
        return headers

    async def client_request(self, method, str_or_url, **kwargs):
        headers = kwargs.get("headers")
        virtual_host = None
        if headers:
            copied = CIMultiDict(headers)
            virtual_host = copied.pop(_SNI_SENTINEL, None)
            kwargs["headers"] = copied
        if virtual_host:
            scheme = urlparse(str(str_or_url)).scheme.lower()
            if scheme in {"https", "wss"}:
                kwargs["server_hostname"] = str(virtual_host)
        return await previous_client_request(self, method, str_or_url, **kwargs)

    def rewrite_location(location: str, target: str, resource: dict, resource_id: str, prefix: str) -> str:
        virtual_host = str(resource.get("virtual_host", "")).strip().lower()
        if virtual_host:
            resolved = urlparse(location)
            if resolved.hostname and resolved.hostname.lower() == virtual_host:
                path = resolved.path.lstrip("/")
                query = f"?{resolved.query}" if resolved.query else ""
                fragment = f"#{resolved.fragment}" if resolved.fragment else ""
                return f"{prefix}proxy/{resource_id}/{path}{query}{fragment}"
        return previous_location(location, target, resource, resource_id, prefix)

    def rewrite_text_body(body: bytes, content_type: str, resource: dict, resource_id: str, prefix: str, **kwargs) -> bytes:
        virtual_host = str(resource.get("virtual_host", "")).strip().lower()
        if virtual_host and body and any(token in content_type.lower() for token in ("text/html", "text/css", "javascript", "ecmascript")):
            text = body.decode("utf-8", errors="replace")
            target = urlparse(str(resource.get("url", "")))
            target_origin = f"{target.scheme}://{target.netloc}"
            # Normalize absolute virtual-host references to the configured
            # transport target first; the mature bridge rewriter then turns
            # those target URLs into Ingress proxy URLs.
            text = re.sub(
                rf"https?://{re.escape(virtual_host)}(?=[:/\"'\\s]|$)",
                target_origin,
                text,
                flags=re.IGNORECASE,
            )
            body = text.encode("utf-8")
        return previous_rewrite_text(body, content_type, resource, resource_id, prefix, **kwargs)

    def bridge_runtime_script(prefix: str, resource_id: str, target_url: str) -> str:
        original = previous_bridge_script(prefix, resource_id, target_url)
        resource = main.STORE.get(resource_id)
        virtual_host = str((resource or {}).get("virtual_host", "")).strip().lower()
        if not virtual_host:
            return original

        target = urlparse(target_url)
        target_origin = f"{target.scheme}://{target.netloc}"
        extension = f'''<script data-ha-remote-bridge-virtual-host>
(() => {{
  const virtualHost = {json.dumps(virtual_host)};
  const targetOrigin = {json.dumps(target_origin)};
  const normalizeVirtual = (value, websocket=false) => {{
    if (value instanceof URL) value=value.href;
    if (typeof value !== 'string') return value;
    try {{
      const u=new URL(value,window.location.href);
      if (u.hostname.toLowerCase() !== virtualHost) return value;
      const target=new URL(targetOrigin);
      u.protocol=websocket ? (target.protocol==='https:'?'wss:':'ws:') : target.protocol;
      u.host=target.host;
      return u.href;
    }} catch (_) {{ return value; }}
  }};

  const previousFetch=window.fetch;
  window.fetch=function(input,init) {{
    if(input instanceof Request) {{
      const normalized=normalizeVirtual(input.url);
      if(normalized!==input.url) input=new Request(normalized,input);
    }} else if(input instanceof URL || typeof input==='string') {{
      input=normalizeVirtual(input);
    }}
    return previousFetch.call(this,input,init);
  }};

  const previousOpen=XMLHttpRequest.prototype.open;
  XMLHttpRequest.prototype.open=function(method,url,...rest) {{
    return previousOpen.call(this,method,normalizeVirtual(url),...rest);
  }};

  if(window.EventSource) {{
    const PreviousEventSource=window.EventSource;
    class VirtualHostEventSource extends PreviousEventSource {{
      constructor(url,options) {{ super(normalizeVirtual(url),options); }}
    }}
    window.EventSource=VirtualHostEventSource;
  }}

  if(window.WebSocket) {{
    const PreviousWebSocket=window.WebSocket;
    const WrappedWebSocket=function(url,protocols) {{
      const normalized=normalizeVirtual(url,true);
      return protocols===undefined ? new PreviousWebSocket(normalized) : new PreviousWebSocket(normalized,protocols);
    }};
    WrappedWebSocket.prototype=PreviousWebSocket.prototype;
    try {{ Object.assign(WrappedWebSocket,PreviousWebSocket); }} catch (_) {{}}
    window.WebSocket=WrappedWebSocket;
  }}
}})();
</script>'''
        return original + extension

    main.add_resource = add_resource
    launcher.update_resource = update_resource
    main.filtered_request_headers = filtered_request_headers
    main.rewrite_location = rewrite_location
    main.rewrite_text_body = rewrite_text_body
    main.bridge_runtime_script = bridge_runtime_script
    ClientSession._request = client_request
