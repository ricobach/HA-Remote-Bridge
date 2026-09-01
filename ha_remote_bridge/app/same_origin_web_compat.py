"""Same-origin browser request compatibility for proxied Web applications.

Applications such as Swagger UI often construct absolute API URLs from
window.location.origin. Under Home Assistant Ingress that origin is Home
Assistant, not the configured upstream endpoint. Normalize those synthetic
same-browser-origin URLs back to the configured endpoint origin before passing
them through the existing HA Remote Bridge wrappers.
"""

from __future__ import annotations

import json
from urllib.parse import urlparse

import main

_INSTALLED = False


def install() -> None:
    """Wrap the browser shim at install time so composition order is explicit."""
    global _INSTALLED
    if _INSTALLED:
        return
    _INSTALLED = True

    previous_bridge_runtime_script = main.bridge_runtime_script

    def bridge_runtime_script(prefix: str, resource_id: str, target_url: str) -> str:
        original = previous_bridge_runtime_script(prefix, resource_id, target_url)
        bridge = f"{prefix}proxy/{resource_id}"
        target = urlparse(target_url)
        target_origin = f"{target.scheme}://{target.netloc}"

        extension = f"""<script data-ha-remote-bridge-same-origin>
(() => {{
  const bridgePath = {json.dumps(bridge)};
  const targetOrigin = {json.dumps(target_origin)};

  const normalizeBrowserOrigin = (value) => {{
    try {{
      const raw = value instanceof Request ? value.url : (value instanceof URL ? value.href : value);
      if (typeof raw !== 'string') return raw;
      const u = new URL(raw, window.location.href);

      const browserScheme = window.location.protocol;
      const browserHttpOrigin = window.location.origin;
      const browserWsOrigin = (browserScheme === 'https:' ? 'wss://' : 'ws://') + window.location.host;
      const sameBrowserOrigin = u.origin === browserHttpOrigin || u.origin === browserWsOrigin;
      const alreadyBridged = u.pathname === bridgePath || u.pathname.startsWith(bridgePath + '/');
      if (!sameBrowserOrigin || alreadyBridged) return raw;

      const target = new URL(targetOrigin);
      const scheme = (u.protocol === 'ws:' || u.protocol === 'wss:')
        ? (target.protocol === 'https:' ? 'wss:' : 'ws:')
        : target.protocol;
      return scheme + '//' + target.host + u.pathname + u.search + u.hash;
    }} catch (_) {{
      return value;
    }}
  }};

  const previousFetch = window.fetch;
  window.fetch = function(input, init) {{
    if (input instanceof Request) {{
      const normalized = normalizeBrowserOrigin(input);
      if (normalized !== input.url) input = new Request(normalized, input);
    }} else if (input instanceof URL) {{
      const normalized = normalizeBrowserOrigin(input);
      if (normalized !== input.href) input = new URL(normalized);
    }} else if (typeof input === 'string') {{
      input = normalizeBrowserOrigin(input);
    }}
    return previousFetch.call(this, input, init);
  }};

  const previousOpen = XMLHttpRequest.prototype.open;
  XMLHttpRequest.prototype.open = function(method, url, ...rest) {{
    return previousOpen.call(this, method, normalizeBrowserOrigin(url), ...rest);
  }};

  if (window.EventSource) {{
    const PreviousEventSource = window.EventSource;
    class SameOriginEventSource extends PreviousEventSource {{
      constructor(url, options) {{ super(normalizeBrowserOrigin(url), options); }}
    }}
    window.EventSource = SameOriginEventSource;
  }}

  if (window.WebSocket) {{
    const PreviousWebSocket = window.WebSocket;
    function SameOriginWebSocket(url, protocols) {{
      const normalized = normalizeBrowserOrigin(url);
      return protocols === undefined
        ? new PreviousWebSocket(normalized)
        : new PreviousWebSocket(normalized, protocols);
    }}
    SameOriginWebSocket.prototype = PreviousWebSocket.prototype;
    Object.setPrototypeOf(SameOriginWebSocket, PreviousWebSocket);
    window.WebSocket = SameOriginWebSocket;
  }}
}})();
</script>"""
        return original + extension

    main.bridge_runtime_script = bridge_runtime_script
