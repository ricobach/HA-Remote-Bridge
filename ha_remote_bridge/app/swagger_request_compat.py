"""Swagger UI request compatibility for HA Remote Bridge.

Swagger UI may build Try-it-out requests from the browser origin even when the
OpenAPI document itself is embedded in the HTML and therefore cannot be
server-side rewritten. Install a small browser shim before Swagger initializes
and inject a requestInterceptor into SwaggerUIBundle.

For resources configured with a base path (for example /api-docs), Swagger's
root-relative API paths must be forwarded against the endpoint origin root, not
relative to the configured document path. A private __hrb_root__ marker is used
inside the existing proxy route to preserve that distinction.
"""

from __future__ import annotations

import json
from urllib.parse import urlparse

import main

_INSTALLED = False
_ROOT_MARKER = "__hrb_root__"


def install() -> None:
    """Append the Swagger interceptor and origin-root relay handling."""
    global _INSTALLED
    if _INSTALLED:
        return
    _INSTALLED = True

    previous_bridge_script = main.bridge_runtime_script
    previous_upstream_url = main.upstream_url

    def upstream_url(resource: dict, tail: str, query: str) -> str:
        """Resolve marked Swagger API paths against the endpoint origin root."""
        marker = _ROOT_MARKER
        normalized = str(tail or "")
        if normalized == marker or normalized.startswith(marker + "/"):
            remainder = normalized[len(marker):].lstrip("/")
            parsed = urlparse(str(resource.get("url", "")))
            origin = f"{parsed.scheme}://{parsed.netloc}"
            target = origin + "/" + remainder
            if query:
                target += "?" + query
            main.LOGGER.info(
                "Swagger API relay %s -> %s",
                resource.get("name", resource.get("id", "resource")),
                target,
            )
            return target
        return previous_upstream_url(resource, tail, query)

    def bridge_runtime_script(prefix: str, resource_id: str, target_url: str) -> str:
        original = previous_bridge_script(prefix, resource_id, target_url)
        bridge = f"{prefix}proxy/{resource_id}"
        target = urlparse(target_url)
        target_origin = f"{target.scheme}://{target.netloc}"

        extension = f'''<script data-ha-remote-bridge-swagger>
(() => {{
  const bridgePath = {json.dumps(bridge)};
  const targetOrigin = {json.dumps(target_origin)};
  const rootMarker = {json.dumps('/' + _ROOT_MARKER)};

  const rewriteSwaggerRequest = (request) => {{
    if (!request || typeof request.url !== 'string') return request;
    try {{
      const u = new URL(request.url, window.location.href);
      const upstream = new URL(targetOrigin);
      const alreadyRootRelayed = u.origin === window.location.origin &&
        (u.pathname === bridgePath + rootMarker || u.pathname.startsWith(bridgePath + rootMarker + '/'));
      if (alreadyRootRelayed) return request;

      const alreadyBridged = u.origin === window.location.origin &&
        (u.pathname === bridgePath || u.pathname.startsWith(bridgePath + '/'));

      // Swagger API operation paths such as /session/getSessions are origin-root
      // paths. If Swagger already produced the normal bridge URL, strip the
      // bridge prefix back off and relay the operation via __hrb_root__ so a
      // resource configured at /api-docs does not become /api-docs/session/...
      let operationPath = u.pathname;
      if (alreadyBridged) {{
        operationPath = u.pathname.slice(bridgePath.length) || '/';
      }}

      const browserOrigin = u.origin === window.location.origin;
      const upstreamOrigin = u.host === upstream.host;
      if (browserOrigin || upstreamOrigin || alreadyBridged) {{
        if (!operationPath.startsWith('/')) operationPath = '/' + operationPath;
        request.url = window.location.origin + bridgePath + rootMarker + operationPath + u.search + u.hash;
      }}
    }} catch (_) {{}}
    return request;
  }};

  const wrapConfig = (config) => {{
    if (!config || typeof config !== 'object') return config;
    const previous = config.requestInterceptor;
    config.requestInterceptor = async (request) => {{
      let current = request;
      if (typeof previous === 'function') {{
        current = await previous(current) || current;
      }}
      return rewriteSwaggerRequest(current);
    }};
    return config;
  }};

  const wrapBundle = (nativeBundle) => {{
    if (typeof nativeBundle !== 'function' || nativeBundle.__hrbSwaggerWrapped) return nativeBundle;
    const wrapped = function(config) {{
      return nativeBundle.call(this, wrapConfig(config));
    }};
    try {{ Object.assign(wrapped, nativeBundle); }} catch (_) {{}}
    try {{ Object.setPrototypeOf(wrapped, nativeBundle); }} catch (_) {{}}
    Object.defineProperty(wrapped, '__hrbSwaggerWrapped', {{value:true}});
    return wrapped;
  }};

  let bundleValue = window.SwaggerUIBundle;
  if (bundleValue) bundleValue = wrapBundle(bundleValue);
  try {{
    const existing = Object.getOwnPropertyDescriptor(window, 'SwaggerUIBundle');
    if (!existing || existing.configurable) {{
      Object.defineProperty(window, 'SwaggerUIBundle', {{
        configurable:true,
        enumerable:true,
        get() {{ return bundleValue; }},
        set(value) {{ bundleValue = wrapBundle(value); }}
      }});
    }}
  }} catch (_) {{}}

  let attempts = 0;
  const timer = window.setInterval(() => {{
    attempts += 1;
    try {{
      const ui = window.ui;
      if (ui && typeof ui.getConfigs === 'function') {{
        const config = ui.getConfigs();
        if (config && !config.__hrbSwaggerRequestInterceptor) {{
          const previous = config.requestInterceptor;
          config.requestInterceptor = async (request) => {{
            let current = request;
            if (typeof previous === 'function') current = await previous(current) || current;
            return rewriteSwaggerRequest(current);
          }};
          config.__hrbSwaggerRequestInterceptor = true;
        }}
        window.clearInterval(timer);
      }}
    }} catch (_) {{}}
    if (attempts > 100) window.clearInterval(timer);
  }}, 100);
}})();
</script>'''
        return original + extension

    main.upstream_url = upstream_url
    main.bridge_runtime_script = bridge_runtime_script
