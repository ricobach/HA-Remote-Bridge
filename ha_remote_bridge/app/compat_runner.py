"""Compatibility runner for HA Remote Bridge.

Adds narrowly scoped JavaScript response rewriting for applications such as
OPNsense that use root-relative dynamic import() module paths. All existing
launcher proxy, ESPHome SSE, cookie, tab UI, and companion-origin behavior is
reused unchanged.
"""

from __future__ import annotations

import asyncio

from aiohttp import ClientError, ClientTimeout, web

import launcher  # applies the existing runtime patches before server startup
import main


_original_rewrite_text_body = main.rewrite_text_body


def rewrite_text_body(
    body: bytes,
    content_type: str,
    resource: dict,
    resource_id: str,
    prefix: str,
) -> bytes:
    """Rewrite normal text bodies plus OPNsense dynamic widget module roots."""
    lowered = content_type.lower()

    if "javascript" not in lowered and "ecmascript" not in lowered:
        return _original_rewrite_text_body(
            body,
            content_type,
            resource,
            resource_id,
            prefix,
        )

    charset = "utf-8"
    try:
        text = body.decode(charset, errors="replace")
    except LookupError:
        text = body.decode("utf-8", errors="replace")

    bridge = f"{prefix}proxy/{resource_id}"

    # OPNsense's widget manager uses native dynamic import() with module URLs
    # rooted at /ui/js/widgets/. Native import() cannot be monkey-patched in
    # the browser, so rewrite only this known module root before delivery.
    text = text.replace("/ui/js/widgets/", f"{bridge}/ui/js/widgets/")

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

    try:
        upstream = await main.CLIENT.request(
            request.method,
            target,
            headers=main.filtered_request_headers(request, target, resource_id),
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
                "text/html" in lowered
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
                )

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
