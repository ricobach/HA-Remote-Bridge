"""Runtime launcher for HA Remote Bridge.

Keeps Home Assistant Ingress header handling separate from the deliberately
small set of headers forwarded to LAN resources, while applying compatibility
rules for browser APIs such as EventSource.
"""

from __future__ import annotations

import asyncio
import json
from urllib.parse import urlparse

from aiohttp import web

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


def _is_event_stream_target(target: str) -> bool:
    """Return True for the conventional SSE events endpoint used by ESPHome."""
    return urlparse(target).path.rstrip("/").endswith("/events")


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


_original_bridge_runtime_script = main.bridge_runtime_script


def enhanced_bridge_runtime_script(prefix: str, resource_id: str, target_url: str) -> str:
    """Extend the browser shim for Request/URL objects and EventSource."""
    original = _original_bridge_runtime_script(prefix, resource_id, target_url)
    bridge = f"{prefix}proxy/{resource_id}"
    target = urlparse(target_url)
    target_origin = f"{target.scheme}://{target.netloc}"

    extension = f"""<script data-ha-remote-bridge-extended>
(() => {{
  const bridge = {json.dumps(bridge)};
  const targetOrigin = {json.dumps(target_origin)};

  const rewrite = (value) => {{
    if (value instanceof URL) value = value.href;
    if (typeof value !== 'string') return value;
    try {{
      const u = new URL(value, window.location.href);
      const target = new URL(targetOrigin);
      const alreadyBridged = u.origin === window.location.origin &&
        (u.pathname === bridge || u.pathname.startsWith(bridge + '/'));
      if (alreadyBridged) return u.href;

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
      return u.origin === window.location.origin &&
        (u.pathname === bridge || u.pathname.startsWith(bridge + '/'));
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


main.filtered_request_headers = filtered_request_headers
main.bridge_runtime_script = enhanced_bridge_runtime_script
main.stream_upstream_response = stream_upstream_response
main.INDEX_HTML = TABBED_INDEX_HTML

from server import _run  # noqa: E402


if __name__ == "__main__":
    asyncio.run(_run())
