"""Runtime launcher for HA Remote Bridge.

Keeps Home Assistant Ingress header handling separate from the deliberately
small set of headers forwarded to LAN resources.
"""

from __future__ import annotations

import asyncio
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


main.filtered_request_headers = filtered_request_headers

from server import _run  # noqa: E402


if __name__ == "__main__":
    asyncio.run(_run())
