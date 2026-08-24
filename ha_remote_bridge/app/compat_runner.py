"""Compatibility runner for HA Remote Bridge.

Adds narrowly scoped JavaScript response rewriting for applications such as
OPNsense that use root-relative dynamic import() module paths. All existing
launcher proxy, ESPHome SSE, cookie, tab UI, and companion-origin behavior is
reused unchanged.
"""

from __future__ import annotations

import asyncio
from pathlib import PurePosixPath

from aiohttp import ClientError, ClientTimeout, web

import launcher  # applies the existing runtime patches before server startup
import main


_original_rewrite_text_body = main.rewrite_text_body


def _is_opnsense_widget_manager(tail: str) -> bool:
    """Return True for OPNsense's dynamic dashboard widget loader."""
    return PurePosixPath("/" + tail.lstrip("/")).name == "opnsense_widget_manager.js"


def rewrite_text_body(
    body: bytes,
    content_type: str,
    resource: dict,
    resource_id: str,
    prefix: str,
    *,
    force_opnsense_widgets: bool = False,
) -> bytes:
    """Rewrite normal text bodies plus OPNsense dynamic widget module roots."""
    lowered = content_type.lower()

    if not force_opnsense_widgets and "javascript" not in lowered and "ecmascript" not in lowered:
        return _original_rewrite_text_body(
            body,
            content_type,
            resource,
            resource_id,
            prefix,
        )

    text = body.decode("utf-8", errors="replace")
    bridge = f"{prefix}proxy/{resource_id}"

    # OPNsense's widget manager uses native dynamic import() with module URLs
    # rooted at /ui/js/widgets/. Native import() cannot be monkey-patched in
    # the browser, so rewrite this known module root before delivery.
    old = "/ui/js/widgets/"
    new = f"{bridge}/ui/js/widgets/"
    replacements = text.count(old)
    text = text.replace(old, new)

    if force_opnsense_widgets:
        main.LOGGER.info(
            "OPNsense widget manager rewrite for resource %s: %d occurrence(s)",
            resource_id,
            replacements,
        )

    return text.encode("utf-8", errors="replace")


async def proxy(request: web.Request) -> web.StreamResponse:
    """Proxy a resource, additionally rewriting targeted JavaScript bodies."""
    if main.CLIENT is None:
        raise web.HTTPServiceUnavailable(text="Proxy client is not ready")

    resource_id = request.match_info["resource_id"]
    tail = request.match_info.get("tail", "")
    resource = main.STORE.get(resource_id)
    if resource is None:
        raise web.HTTPNotFound(text="Unknown resource")

    if request.headers.get("Upgrade", "").lower() == "websocket":
        return await main.proxy_websocket(request, resource, resource_id, tail)

    target = main.upstream_url(resource, tail, request.query_string)
    body = await request.read() if request.can_read_body else None
    is_widget_manager = _is_opnsense_widget_manager(tail)
    request_headers = main.filtered_request_headers(request, target, resource_id)

    # The OPNsense asset URL is versioned but can remain unchanged across
    # HA Remote Bridge releases. Do not allow a 304 to make the browser reuse
    # an older, unrewritten copy of the widget manager.
    if is_widget_manager:
        for header in ("If-None-Match", "If-Modified-Since"):
            request_headers.pop(header, None)

    try:
        upstream = await main.CLIENT.request(
            request.method,
            target,
            headers=request_headers,
            data=body,
            allow_redirects=False,
            ssl=None if resource.get("verify_ssl", True) else False,
            timeout=ClientTimeout(total=None, connect=15, sock_connect=15, sock_read=None),
        )

        try:
            content_type = upstream.headers.get("Content-Type", "")
            if "text/event-stream" in content_type.lower():
                return await main.stream_upstream_response(request, upstream, resource_id)

            raw_body = await upstream.read()
            headers = main.copy_response_headers(upstream)
            main.add_rewritten_cookies(headers, upstream, request, resource_id)

            prefix = main.ingress_prefix(request)
            if upstream.headers.get("Location"):
                headers["Location"] = main.rewrite_location(
                    upstream.headers["Location"],
                    target,
                    resource,
                    resource_id,
                    prefix,
                )

            lowered = content_type.lower()
            if raw_body and (
                is_widget_manager
                or "text/html" in lowered
                or "text/css" in lowered
                or "javascript" in lowered
                or "ecmascript" in lowered
            ):
                raw_body = rewrite_text_body(
                    raw_body,
                    content_type,
                    resource,
                    resource_id,
                    prefix,
                    force_opnsense_widgets=is_widget_manager,
                )

            if is_widget_manager:
                # Ensure the rewritten script is used immediately after an App
                # update instead of a stale browser copy.
                headers["Cache-Control"] = "no-store, no-cache, must-revalidate"
                headers["Pragma"] = "no-cache"
                headers.popall("ETag", None)
                headers.popall("Last-Modified", None)

            return web.Response(
                status=upstream.status,
                reason=upstream.reason,
                headers=headers,
                body=b"" if request.method == "HEAD" else raw_body,
            )
        finally:
            upstream.release()
    except (ClientError, asyncio.TimeoutError) as err:
        main.LOGGER.warning("Proxy request failed for %s: %r", resource["name"], err)
        raise web.HTTPBadGateway(text=f"Unable to reach {resource['name']}: {err}") from err


# launcher.create_app calls the original main.create_app function. That function
# resolves its global `proxy` handler when it builds the router, so replacing it
# here keeps all launcher-added routes while installing this compatibility path.
main.rewrite_text_body = rewrite_text_body
main.proxy = proxy


if __name__ == "__main__":
    asyncio.run(launcher._run())
