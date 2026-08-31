"""RutOS / Teltonika web UI compatibility for HA Remote Bridge.

Modern RutOS authenticates with an application Bearer token and uses a
history-mode SPA rooted at '/'. HA Remote Bridge deliberately strips generic
Authorization headers and normally runs below an Ingress/proxy prefix, so both
behaviours need a narrow target-specific compatibility layer.
"""

from __future__ import annotations

import json
from urllib.parse import urlparse

import main


_RUTOS_RESOURCES: set[str] = set()
_LOGGED_RESOURCES: set[str] = set()
_RUTOS_AUTHORIZATION: dict[str, str] = {}

_RUTOS_PATH_PREFIXES = (
    "/api/unauthorized/",
    "/api/session/",
    "/api/ui/config/",
    "/api/system/device/packages/",
)
_RUTOS_EXACT_PATHS = {
    "/api/login",
    "/api/logout",
}
_RUTOS_SUBSCRIPTION_PATHS = {
    "/cgi-bin/subscribe.lua",
}


def _target_path(target: str) -> str:
    return urlparse(target).path


def _looks_like_rutos_path(target: str) -> bool:
    path = _target_path(target)
    return (
        path in _RUTOS_EXACT_PATHS
        or path in _RUTOS_SUBSCRIPTION_PATHS
        or any(path.startswith(prefix) for prefix in _RUTOS_PATH_PREFIXES)
    )


def _mark_rutos(resource_id: str) -> None:
    _RUTOS_RESOURCES.add(resource_id)
    if resource_id not in _LOGGED_RESOURCES:
        resource = main.STORE.get(resource_id)
        main.LOGGER.info(
            "RutOS compatibility detected for resource %s (%s)",
            resource.get("name", resource_id) if resource else resource_id,
            resource_id,
        )
        _LOGGED_RESOURCES.add(resource_id)


def install() -> None:
    """Install the compatibility wrappers after the normal launcher stack."""
    original_headers = main.filtered_request_headers
    original_bridge_script = main.bridge_runtime_script

    def rutos_filtered_request_headers(request, target: str, resource_id: str) -> dict[str, str]:
        if _looks_like_rutos_path(target):
            _mark_rutos(resource_id)

        headers = original_headers(request, target, resource_id)
        if resource_id not in _RUTOS_RESOURCES:
            return headers

        target_path = _target_path(target)
        authorization = request.headers.get("Authorization")

        # Normal RutOS API calls use the application Bearer token. Keep this
        # behavior for XHR/fetch traffic and remember the token in process
        # memory only for diagnostics/session lifecycle purposes.
        if authorization and target_path not in _RUTOS_SUBSCRIPTION_PATHS:
            _RUTOS_AUTHORIZATION[resource_id] = authorization
            headers["Authorization"] = authorization

        if target_path in _RUTOS_SUBSCRIPTION_PATHS:
            # A native EventSource cannot set a custom Authorization header.
            # RutOS therefore has to authenticate subscribe.lua from the normal
            # same-origin browser/session context (cookie and/or query token).
            # Do not inject the Bearer token here: that can cause uhttpd/CGI to
            # reject an otherwise valid EventSource request with 403.
            headers.pop("Authorization", None)
            resource = main.STORE.get(resource_id)
            headers["Accept"] = "text/event-stream"
            headers["Accept-Encoding"] = "identity"
            headers["Cache-Control"] = "no-cache"
            headers.pop("Origin", None)
            if resource:
                headers["Referer"] = resource["url"].rstrip("/") + "/"

            main.LOGGER.info(
                "RutOS subscription request for %s: cookie=%s query=%s authorization=off",
                resource.get("name", resource_id) if resource else resource_id,
                "yes" if bool(headers.get("Cookie")) else "no",
                "yes" if bool(urlparse(target).query) else "no",
            )

        if target_path == "/api/logout":
            _RUTOS_AUTHORIZATION.pop(resource_id, None)

        return headers

    def rutos_bridge_runtime_script(prefix: str, resource_id: str, target_url: str) -> str:
        original = original_bridge_script(prefix, resource_id, target_url)
        bridge = f"{prefix}proxy/{resource_id}"
        target = urlparse(target_url)
        target_origin = f"{target.scheme}://{target.netloc}"

        extension = f"""<script data-ha-remote-bridge-history>
(() => {{
  const bridge = {json.dumps(bridge)};
  const ingressPrefix = {json.dumps(prefix)};
  const targetOrigin = {json.dumps(target_origin)};

  const rewriteNavigation = (value) => {{
    if (typeof value !== 'string' || !value.startsWith('/') || value.startsWith('//')) return value;
    if (value === bridge || value.startsWith(bridge + '/')) return value;
    if (ingressPrefix !== '/' && (value === ingressPrefix.slice(0, -1) || value.startsWith(ingressPrefix))) return value;
    return bridge + value;
  }};

  const previousXhrOpen = XMLHttpRequest.prototype.open;
  const normalizeXhrUrl = (value) => {{
    if (typeof value !== 'string') return value;
    try {{
      const u = new URL(value, window.location.href);
      const sameBrowserOrigin = u.origin === window.location.origin;
      if (sameBrowserOrigin && (u.pathname === bridge || u.pathname.startsWith(bridge + '/'))) {{
        const suffix = u.pathname.slice(bridge.length) || '/';
        return targetOrigin + suffix + u.search + u.hash;
      }}
    }} catch (_) {{}}
    return value;
  }};
  XMLHttpRequest.prototype.open = function(method, url, ...rest) {{
    return previousXhrOpen.call(this, method, normalizeXhrUrl(url), ...rest);
  }};

  const nativePushState = history.pushState.bind(history);
  history.pushState = function(state, title, url) {{
    return nativePushState(state, title, rewriteNavigation(url));
  }};
  const nativeReplaceState = history.replaceState.bind(history);
  history.replaceState = function(state, title, url) {{
    return nativeReplaceState(state, title, rewriteNavigation(url));
  }};

  const nativeSetAttribute = Element.prototype.setAttribute;
  Element.prototype.setAttribute = function(name, value) {{
    const attr = String(name || '').toLowerCase();
    if (attr === 'src' || attr === 'href' || attr === 'action' || attr === 'poster') {{
      value = rewriteNavigation(value);
    }}
    return nativeSetAttribute.call(this, name, value);
  }};

  const patchUrlProperty = (prototype, property) => {{
    if (!prototype) return;
    const descriptor = Object.getOwnPropertyDescriptor(prototype, property);
    if (!descriptor || !descriptor.set || !descriptor.get || descriptor.configurable === false) return;
    try {{
      Object.defineProperty(prototype, property, {{
        configurable: descriptor.configurable,
        enumerable: descriptor.enumerable,
        get: descriptor.get,
        set(value) {{ descriptor.set.call(this, rewriteNavigation(value)); }},
      }});
    }} catch (_) {{}}
  }};
  patchUrlProperty(window.HTMLImageElement && HTMLImageElement.prototype, 'src');
  patchUrlProperty(window.HTMLScriptElement && HTMLScriptElement.prototype, 'src');
  patchUrlProperty(window.HTMLLinkElement && HTMLLinkElement.prototype, 'href');
  patchUrlProperty(window.HTMLFormElement && HTMLFormElement.prototype, 'action');

  document.addEventListener('click', (event) => {{
    const anchor = event.target && event.target.closest ? event.target.closest('a[href]') : null;
    if (!anchor) return;
    const raw = anchor.getAttribute('href');
    const rewritten = rewriteNavigation(raw);
    if (rewritten !== raw) anchor.setAttribute('href', rewritten);
  }}, true);

  document.addEventListener('submit', (event) => {{
    const form = event.target;
    if (!form || !form.getAttribute) return;
    const raw = form.getAttribute('action');
    const rewritten = rewriteNavigation(raw);
    if (rewritten !== raw) form.setAttribute('action', rewritten);
  }}, true);

  const nativeOpen = window.open;
  if (nativeOpen) {{
    window.open = function(url, ...rest) {{
      return nativeOpen.call(window, rewriteNavigation(url), ...rest);
    }};
  }}
}})();
</script>"""
        return original + extension

    main.filtered_request_headers = rutos_filtered_request_headers
    main.bridge_runtime_script = rutos_bridge_runtime_script
