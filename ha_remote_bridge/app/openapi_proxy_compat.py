"""OpenAPI/Swagger compatibility for HA Remote Bridge.

Swagger UI commonly uses the OpenAPI `servers` entry to decide where Try it out
requests are sent. When an upstream document advertises `/` (or another
same-origin relative URL), the browser resolves that against Home Assistant's
origin instead of the configured LAN endpoint. Rewrite those OpenAPI server
entries to this resource's HA Remote Bridge proxy base so Swagger's own request
machinery naturally stays inside Ingress.
"""

from __future__ import annotations

import json
from typing import Any
from urllib.parse import urlparse

from aiohttp import web

import main

_INSTALLED = False
_ORIGINAL_PROXY = None


def _bridge_base(request: web.Request, resource_id: str) -> str:
    """Return the browser-visible path for this configured resource."""
    return f"{main.ingress_prefix(request)}proxy/{resource_id}"


def _join_bridge(base: str, suffix: str) -> str:
    suffix = str(suffix or "").strip()
    if not suffix or suffix == "/":
        return base
    if suffix.startswith("/"):
        return base + suffix
    return base + "/" + suffix


def _is_same_upstream_server(url: str, resource: dict) -> bool:
    """Return True when an absolute OpenAPI server points at this endpoint."""
    try:
        server = urlparse(url)
        upstream = urlparse(str(resource.get("url", "")))
    except Exception:
        return False
    if not server.scheme or not server.netloc:
        return False
    return server.hostname == upstream.hostname and server.port == upstream.port


def _rewrite_openapi_document(
    document: Any,
    request: web.Request,
    resource: dict,
    resource_id: str,
) -> tuple[Any, bool]:
    if not isinstance(document, dict):
        return document, False

    is_openapi3 = bool(document.get("openapi"))
    is_swagger2 = str(document.get("swagger", "")).startswith("2.")
    if not (is_openapi3 or is_swagger2):
        return document, False

    changed = False
    bridge = _bridge_base(request, resource_id)

    if is_openapi3:
        servers = document.get("servers")
        if not isinstance(servers, list) or not servers:
            document["servers"] = [{"url": bridge, "description": "HA Remote Bridge"}]
            changed = True
        else:
            rewritten = []
            for entry in servers:
                if not isinstance(entry, dict):
                    rewritten.append(entry)
                    continue
                item = dict(entry)
                url = str(item.get("url", "")).strip()
                # Relative/root servers belong to the proxied application. Absolute
                # servers are rewritten only when they point back to this configured
                # endpoint; intentionally external API servers are preserved.
                if not url or url.startswith("/") or not urlparse(url).scheme:
                    item["url"] = _join_bridge(bridge, url)
                    item["description"] = item.get("description") or "HA Remote Bridge"
                    changed = True
                elif _is_same_upstream_server(url, resource):
                    parsed = urlparse(url)
                    item["url"] = _join_bridge(bridge, parsed.path or "/")
                    item["description"] = item.get("description") or "HA Remote Bridge"
                    changed = True
                rewritten.append(item)
            document["servers"] = rewritten

    if is_swagger2:
        # Swagger 2 builds the request origin from schemes/host/basePath. Removing
        # host/schemes makes it browser-origin relative; basePath then anchors it to
        # this resource's Ingress proxy route.
        if document.get("host"):
            document.pop("host", None)
            changed = True
        if document.get("schemes"):
            document.pop("schemes", None)
            changed = True
        old_base = str(document.get("basePath", "/") or "/")
        new_base = _join_bridge(bridge, old_base)
        if document.get("basePath") != new_base:
            document["basePath"] = new_base
            changed = True

    return document, changed


async def proxy(request: web.Request) -> web.StreamResponse:
    """Run the normal proxy, then rewrite OpenAPI JSON server metadata."""
    assert _ORIGINAL_PROXY is not None
    response = await _ORIGINAL_PROXY(request)

    if not isinstance(response, web.Response):
        return response
    if response.status < 200 or response.status >= 300 or not response.body:
        return response

    content_type = str(response.headers.get("Content-Type", "")).lower()
    if "json" not in content_type and "openapi" not in content_type:
        return response

    try:
        charset = response.charset or "utf-8"
        document = json.loads(response.body.decode(charset))
    except Exception:
        return response

    resource_id = request.match_info.get("resource_id", "")
    resource = main.STORE.get(resource_id)
    if resource is None:
        return response

    document, changed = _rewrite_openapi_document(document, request, resource, resource_id)
    if not changed:
        return response

    body = json.dumps(document, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    response.body = body
    response.headers["Content-Type"] = "application/json; charset=utf-8"
    response.headers["Cache-Control"] = "no-store"
    response.headers.pop("Content-Length", None)
    main.LOGGER.info("Rewrote OpenAPI server URL through bridge for %s", resource.get("name", resource_id))
    return response


def install() -> None:
    """Install before the aiohttp app/router is created."""
    global _INSTALLED, _ORIGINAL_PROXY
    if _INSTALLED:
        return
    _INSTALLED = True
    _ORIGINAL_PROXY = main.proxy
    main.proxy = proxy
