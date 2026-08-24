"""Runtime launcher for HA Remote Bridge.

Keeps Home Assistant Ingress header handling separate from the deliberately
small set of headers forwarded to LAN resources, while applying compatibility
rules for browser APIs such as EventSource and approved companion API origins.
"""

from __future__ import annotations

import asyncio
import json
from urllib.parse import urlparse

from aiohttp import ClientError, ClientTimeout, web

import main
from ui_shell import INDEX_HTML as TABBED_INDEX_HTML

_UPSTREAM_HEADER_ALLOWLIST = {
    "accept",
    "accept-encoding",
    "accept-language",
    "cache-control",
    "content-type",
    "if-modified-since",
    "if-none-match",
    "last-event-id",
    "pragma",
    "range",
    "user-agent",
    "x-csrftoken",
    "x-requested-with",
}

# Companion origins are deliberately server-defined. Browser code can only
# select one of these named endpoints; it cannot provide an arbitrary URL.
_COMPANION_ORIGINS = {
    "myip.dk": {
        "ipv4": "https://ipv4.myip.dk",
        "ipv6": "https://ipv6.myip.dk",
    },
}


def _is_event_stream_target(target: str) -> bool:
    """Return True for the conventional SSE events endpoint used by ESPHome."""
    return urlparse(target).path.rstrip("/").endswith("/events")


def _companion_policy(target_url: str) -> dict[str, str]:
    """Return approved companion endpoints for one configured resource."""
    hostname = (urlparse(target_url).hostname or "").lower()
    return _COMPANION_ORIGINS.get(hostname, {})


def filtered_request_headers(
    request: web.Request,
    target: str,
    resource_id: str,
) -> dict[str, str]:
    """Build a minimal, target-safe upstream header set."""
    headers = {
        key: value
        for key, value in request.headers.items()
        if key.lower() in _UPSTREAM_HEADER_ALLOWLIST
    }

    parsed = urlparse(target)
    origin = f"{parsed.scheme}://{parsed.netloc}"

    if _is_event_stream_target(target):
        # ESPHome uses /events as a long-lived Server-Sent Events connection.
        # Keep this request tiny and deterministic for constrained embedded
        # web servers, and preserve Last-Event-ID for native EventSource
        # reconnect semantics.
        headers["Accept"] = "text/event-stream"
        headers["Cache-Control"] = "no-cache"
        headers["Accept-Encoding"] = "identity"
    else:
        # Login/CSRF flows such as OPNsense can validate Origin/Referer.
        headers["Origin"] = origin
        headers["Referer"] = target

    cookie = main.upstream_cookie_header(request, resource_id)
    if cookie:
        headers["Cookie"] = cookie

    return headers


def companion_request_headers(request: web.Request, resource: dict) -> dict[str, str]:
    """Build browser-like headers for an approved companion API request."""
    headers = {
        key: value
        for key, value in request.headers.items()
        if key.lower() in _UPSTREAM_HEADER_ALLOWLIST
    }
    resource_url = urlparse(resource["url"])
    resource_origin = f"{resource_url.scheme}://{resource_url.netloc}"
    headers["Origin"] = resource_origin
    headers["Referer"] = resource["url"].rstrip("/") + "/"
    return headers


_original_bridge_runtime_script = main.bridge_runtime_script


def enhanced_bridge_runtime_script(prefix: str, resource_id: str, target_url: str) -> str:
    """Extend the browser shim for Request/URL objects, EventSource and companion APIs."""
    original = _original_bridge_runtime_script(prefix, resource_id, target_url)
    bridge = f"{prefix}proxy/{resource_id}"
    companion_bridge = f"{prefix}companion/{resource_id}"
    target = urlparse(target_url)
    target_origin = f"{target.scheme}://{target.netloc}"
    companion_by_origin = {
        origin: key
        for key, origin in _companion_policy(target_url).items()
    }

    extension = f"""<script data-ha-remote-bridge-extended>
(() => {{
  const bridge = {json.dumps(bridge)};
  const companionBridge = {json.dumps(companion_bridge)};
  const targetOrigin = {json.dumps(target_origin)};
  const companionOrigins = {json.dumps(companion_by_origin)};

  const rewrite = (value) => {{
    if (value instanceof URL) value = value.href;
    if (typeof value !== 'string') return value;
    try {{
      const u = new URL(value, window.location.href);
      const target = new URL(targetOrigin);
      const alreadyBridged = u.origin === window.location.origin && (
        u.pathname === bridge || u.pathname.startsWith(bridge + '/') ||
        u.pathname === companionBridge || u.pathname.startsWith(companionBridge + '/')
      );
      if (alreadyBridged) return u.href;

      const companionKey = companionOrigins[u.origin];
      if (companionKey) {{
        return window.location.protocol + '//' + window.location.host +
          companionBridge + '/' + encodeURIComponent(companionKey) +
          u.pathname + u.search + u.hash;
      }}

      const sameTarget = u.host === target.host;
      const rootRelative = value.startsWith('/');
      if (sameTarget || rootRelative) {{
        return window.location.protocol + '//' + window.location.host + bridge + u.pathname + u.search + u.hash;
      }}
    }} catch (_) {{}}
    return value;
  }};

  const isBridgeUrl = (value) => {{
    try {{
      const raw = value instanceof Request ? value.url : (value instanceof URL ? value.href : value);
      if (typeof raw !== 'string') return false;
      const u = new URL(raw, window.location.href);
      return u.origin === window.location.origin && (
        u.pathname === bridge || u.pathname.startsWith(bridge + '/') ||
        u.pathname === companionBridge || u.pathname.startsWith(companionBridge + '/')
      );
    }} catch (_) {{
      return false;
    }}
  }};

  // The base shim handles plain string fetch URLs. Extend it for modern
  // frameworks that pass Request or URL objects, and avoid sending an
  // already-bridged string through the base shim a second time.
  const previousFetch = window.fetch;
  window.fetch = function(input, init) {{
    if (input instanceof Request) {{
      const rewritten = rewrite(input.url);
      if (rewritten !== input.url) {{
        input = new Request(rewritten, input);
      }}
    }} else if (input instanceof URL) {{
      const rewritten = rewrite(input);
      input = new Request(rewritten, init);
      init = undefined;
    }} else if (typeof input === 'string') {{
      const rewritten = rewrite(input);
      if (rewritten !== input || isBridgeUrl(input)) {{
        input = new Request(rewritten, init);
        init = undefined;
      }}
    }}
    return previousFetch.call(this, input, init);
  }};

  // ESPHome Web Server uses EventSource('/events') for initial entity state,
  // live state updates, logs and heartbeat pings. Subclassing preserves the
  // native EventSource prototype/static behavior better than a wrapper
  // function while still rewriting the URL through Ingress.
  if (window.EventSource) {{
    const NativeEventSource = window.EventSource;
    class BridgeEventSource extends NativeEventSource {{
      constructor(url, options) {{
        super(rewrite(url), options);
      }}
    }}
    window.EventSource = BridgeEventSource;
  }}
}})();
</script>"""

    return original + extension


async def stream_upstream_response(
    request: web.Request,
    upstream,
    resource_id: str,
) -> web.StreamResponse:
    """Stream SSE/long-lived responses without buffering."""
    headers = main.copy_response_headers(upstream)
    main.add_rewritten_cookies(headers, upstream, request, resource_id)

    content_type = upstream.headers.get("Content-Type", "")
    is_sse = "text/event-stream" in content_type.lower()
    if is_sse:
        headers["Cache-Control"] = "no-cache"
        headers["X-Accel-Buffering"] = "no"

    response = web.StreamResponse(
        status=upstream.status,
        reason=upstream.reason,
        headers=headers,
    )
    await response.prepare(request)

    chunks = 0
    total_bytes = 0
    if is_sse:
        main.LOGGER.info(
            "SSE stream opened for resource %s path %s",
            resource_id,
            request.path,
        )

    try:
        async for chunk in upstream.content.iter_any():
            if chunk:
                chunks += 1
                total_bytes += len(chunk)
                await response.write(chunk)
    except (ConnectionResetError, asyncio.CancelledError):
        pass
    finally:
        if is_sse:
            main.LOGGER.info(
                "SSE stream closed for resource %s after %d chunk(s), %d byte(s)",
                resource_id,
                chunks,
                total_bytes,
            )
        try:
            await response.write_eof()
        except (ConnectionResetError, RuntimeError):
            pass

    return response


async def proxy_companion(request: web.Request) -> web.StreamResponse:
    """Relay a request to a server-approved companion origin."""
    if main.CLIENT is None:
        raise web.HTTPServiceUnavailable(text="Proxy client is not ready")

    resource_id = request.match_info["resource_id"]
    companion_key = request.match_info["companion_key"]
    tail = request.match_info.get("tail", "")
    resource = main.STORE.get(resource_id)
    if resource is None:
        raise web.HTTPNotFound(text="Unknown resource")

    origin = _companion_policy(resource["url"]).get(companion_key)
    if origin is None:
        raise web.HTTPForbidden(text="Companion origin is not approved for this resource")

    target = origin.rstrip("/") + "/" + tail.lstrip("/")
    if request.query_string:
        target += "?" + request.query_string
    body = await request.read() if request.can_read_body else None

    try:
        upstream = await main.CLIENT.request(
            request.method,
            target,
            headers=companion_request_headers(request, resource),
            data=body,
            allow_redirects=False,
            timeout=ClientTimeout(total=30, connect=15, sock_connect=15),
        )
        try:
            raw_body = await upstream.read()
            headers = main.copy_response_headers(upstream)
            headers.popall("Access-Control-Allow-Origin", None)
            headers.popall("Access-Control-Allow-Credentials", None)
            headers.popall("Access-Control-Allow-Methods", None)
            headers.popall("Access-Control-Allow-Headers", None)

            if upstream.headers.get("Location"):
                location = urlparse(upstream.headers["Location"])
                if location.scheme and location.netloc:
                    allowed_origin = f"{location.scheme}://{location.netloc}"
                    allowed_key = next(
                        (key for key, value in _companion_policy(resource["url"]).items() if value == allowed_origin),
                        None,
                    )
                    if allowed_key:
                        location_path = location.path.lstrip("/")
                        query = f"?{location.query}" if location.query else ""
                        headers["Location"] = (
                            f"{main.ingress_prefix(request)}companion/{resource_id}/{allowed_key}/{location_path}{query}"
                        )

            main.LOGGER.info(
                "Companion request %s %s -> %s %s",
                request.method,
                companion_key,
                upstream.status,
                target,
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
        main.LOGGER.warning(
            "Companion request failed for %s/%s: %r",
            resource["name"],
            companion_key,
            err,
        )
        raise web.HTTPBadGateway(text=f"Unable to reach companion service: {err}") from err


_original_create_app = main.create_app


def create_app() -> web.Application:
    """Create the app and add the restricted companion-origin relay."""
    app = _original_create_app()
    app.router.add_route(
        "*",
        "/companion/{resource_id}/{companion_key}/{tail:.*}",
        proxy_companion,
    )
    return app


main.filtered_request_headers = filtered_request_headers
main.bridge_runtime_script = enhanced_bridge_runtime_script
main.stream_upstream_response = stream_upstream_response
main.INDEX_HTML = TABBED_INDEX_HTML
main.create_app = create_app

from server import _run  # noqa: E402


if __name__ == "__main__":
    asyncio.run(_run())
