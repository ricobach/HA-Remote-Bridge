"""Runtime launcher for HA Remote Bridge.

Keeps the Ingress-facing server permissive enough for Home Assistant while
forwarding a deliberately small set of browser headers to LAN resources.
"""

from __future__ import annotations

from urllib.parse import urlparse

from aiohttp import web

import main

# Headers that a normal embedded/local web application may reasonably need.
# Home Assistant Ingress, proxy, forwarding and authorization headers are
# intentionally excluded. aiohttp generates Host for the actual target URL.
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

    # Login/CSRF flows such as OPNsense can validate Origin/Referer. Recreate
    # those values for the actual LAN target instead of forwarding HA's URL.
    parsed = urlparse(target)
    origin = f"{parsed.scheme}://{parsed.netloc}"
    headers["Origin"] = origin
    headers["Referer"] = target

    # Only cookies previously issued by this specific bridged resource are
    # restored. Home Assistant and other bridged-resource cookies stay out.
    cookie = main.upstream_cookie_header(request, resource_id)
    if cookie:
        headers["Cookie"] = cookie

    return headers


# Override the proxy module's forwarding policy without duplicating its
# resource, cookie, rewrite, WebSocket and SSE implementation.
main.filtered_request_headers = filtered_request_headers


if __name__ == "__main__":
    web.run_app(
        main.create_app(),
        host="0.0.0.0",
        port=main.PORT,
        access_log=main.LOGGER,
        handler_cancellation=True,
        max_line_size=64 * 1024,
        max_field_size=64 * 1024,
    )
