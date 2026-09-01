"""Swagger UI request compatibility for HA Remote Bridge.

Swagger UI may build Try-it-out requests from the browser origin even when the
OpenAPI document itself is embedded in the HTML and therefore cannot be
server-side rewritten. Install a small browser shim before Swagger initializes
and inject a requestInterceptor into SwaggerUIBundle. The interceptor rewrites
same-browser-origin and same-upstream API URLs through this resource's bridge
path before Swagger sends them.
"""

from __future__ import annotations

import json
from urllib.parse import urlparse

import main

_INSTALLED = False


def install() -> None:
    """Append the Swagger interceptor to the per-resource browser shim."""
    global _INSTALLED
    if _INSTALLED:
        return
    _INSTALLED = True

    previous_bridge_script = main.bridge_runtime_script

    def bridge_runtime_script(prefix: str, resource_id: str, target_url: str) -> str:
        original = previous_bridge_script(prefix, resource_id, target_url)
        bridge = f"{prefix}proxy/{resource_id}"
        target = urlparse(target_url)
        target_origin = f"{target.scheme}://{target.netloc}"

        extension = f'''<script data-ha-remote-bridge-swagger>
(() => {{
  const bridgePath = {json.dumps(bridge)};
  const targetOrigin = {json.dumps(target_origin)};

  const rewriteSwaggerRequest = (request) => {{
    if (!request || typeof request.url !== 'string') return request;
    try {{
      const u = new URL(request.url, window.location.href);
      const upstream = new URL(targetOrigin);
      const alreadyBridged = u.origin === window.location.origin &&
        (u.pathname === bridgePath || u.pathname.startsWith(bridgePath + '/'));
      if (alreadyBridged) return request;

      const browserOrigin = u.origin === window.location.origin;
      const upstreamOrigin = u.host === upstream.host;
      if (browserOrigin || upstreamOrigin) {{
        request.url = window.location.origin + bridgePath + u.pathname + u.search + u.hash;
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

  // Swagger's bundle is normally assigned to window.SwaggerUIBundle by its UMD
  // script and then invoked by an inline initializer. Install a setter before
  // that happens so we can add the requestInterceptor to the initializer config.
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

  // Fallback for pages that initialized Swagger before assigning through the
  // normal global. getConfigs() returns the live config object in Swagger UI;
  // patch it once the UI becomes available.
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

    main.bridge_runtime_script = bridge_runtime_script
