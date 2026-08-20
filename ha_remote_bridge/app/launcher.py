"""Runtime launcher for HA Remote Bridge.

Keeps Home Assistant Ingress header handling separate from the deliberately
small set of headers forwarded to LAN resources.
"""

from __future__ import annotations

import asyncio
import json
from urllib.parse import urlparse

from aiohttp import web

import main

_UPSTREAM_HEADER_ALLOWLIST = {
    "accept",
    "accept-encoding",
    "accept-language",
    "cache-control",
    "content-type",
    "if-modified-since",
    "if-none-match",
    "pragma",
    "range",
    "user-agent",
    "x-csrftoken",
    "x-requested-with",
}


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
      const sameTarget = u.host === target.host;
      const rootRelative = value.startsWith('/');
      if (sameTarget || rootRelative) {{
        return window.location.protocol + '//' + window.location.host + bridge + u.pathname + u.search + u.hash;
      }}
    }} catch (_) {{}}
    return value;
  }};

  // The base shim handles plain string fetch URLs. Extend it for modern
  // frameworks that pass Request or URL objects instead.
  const previousFetch = window.fetch;
  window.fetch = function(input, init) {{
    if (input instanceof Request) {{
      const rewritten = rewrite(input.url);
      if (rewritten !== input.url) {{
        input = new Request(rewritten, input);
      }}
    }} else if (input instanceof URL) {{
      input = rewrite(input);
    }}
    return previousFetch.call(this, input, init);
  }};

  // EventSource is common for live embedded-device UIs and some SPAs.
  if (window.EventSource) {{
    const NativeEventSource = window.EventSource;
    window.EventSource = function(url, options) {{
      return new NativeEventSource(rewrite(url), options);
    }};
    window.EventSource.prototype = NativeEventSource.prototype;
  }}
}})();
</script>"""

    return original + extension


main.filtered_request_headers = filtered_request_headers
main.bridge_runtime_script = enhanced_bridge_runtime_script

from server import _run  # noqa: E402


if __name__ == "__main__":
    asyncio.run(_run())
