"""RutOS / Teltonika web UI compatibility for HA Remote Bridge.

Modern RutOS authenticates with an application Bearer token and uses a
history-mode SPA rooted at '/'.  HA Remote Bridge deliberately strips generic
Authorization headers and normally runs below an Ingress/proxy prefix, so both
behaviours need a narrow target-specific compatibility layer.
"""

from __future__ import annotations

import json
from urllib.parse import urlparse

import main


# Runtime-only detection. A resource is promoted to RutOS compatibility after
# requesting one of the characteristic RutOS API endpoints. This avoids
# forwarding Authorization to ordinary configured web resources.
_RUTOS_RESOURCES: set[str] = set()
_LOGGED_RESOURCES: set[str] = set()
# Application Bearer tokens are cached only in memory, never persisted. RutOS
# uses browser APIs such as EventSource for subscribe.lua, and those requests
# cannot attach a custom Authorization header themselves.
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

        # Normal RutOS XHR/fetch traffic carries the application token itself.
        # Remember it only in process memory so subscription requests that use
        # EventSource can reuse it without persisting credentials anywhere.
        authorization = request.headers.get("Authorization")
        if authorization:
            _RUTOS_AUTHORIZATION[resource_id] = authorization
            headers["Authorization"] = authorization
        elif _target_path(target) in _RUTOS_SUBSCRIPTION_PATHS:
            cached = _RUTOS_AUTHORIZATION.get(resource_id)
            if cached:
                headers["Authorization"] = cached
                main.LOGGER.debug(
                    "Reused in-memory RutOS authorization for subscription resource %s",
                    resource_id,
                )

        # Logging out invalidates the application token; do not carry an old
        # token into a later browser session.
        if _target_path(target) == "/api/logout":
            _RUTOS_AUTHORIZATION.pop(resource_id, None)

        return headers

    def rutos_bridge_runtime_script(prefix: str, resource_id: str, target_url: str) -> str:
        original = original_bridge_script(prefix, resource_id, target_url)
        bridge = f"{prefix}proxy/{resource_id}"

        # History-mode routers such as the RutOS Vue UI can call
        # pushState('/login'), which otherwise changes the browser URL to the HA
        # host root. Rebase root-relative history URLs beneath this resource.
        extension = f"""<script data-ha-remote-bridge-history>
(() => {{
  const bridge = {json.dumps(bridge)};
  const ingressPrefix = {json.dumps(prefix)};

  const rewriteNavigation = (value) => {{
    if (typeof value !== 'string' || !value.startsWith('/') || value.startsWith('//')) return value;
    if (value === bridge || value.startsWith(bridge + '/')) return value;
    if (ingressPrefix !== '/' && (value === ingressPrefix.slice(0, -1) || value.startsWith(ingressPrefix))) return value;
    return bridge + value;
  }};

  const nativePushState = history.pushState.bind(history);
  history.pushState = function(state, title, url) {{
    return nativePushState(state, title, rewriteNavigation(url));
  }};
  const nativeReplaceState = history.replaceState.bind(history);
  history.replaceState = function(state, title, url) {{
    return nativeReplaceState(state, title, rewriteNavigation(url));
  }};

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
