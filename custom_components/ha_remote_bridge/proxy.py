"""Authenticated HTTP/HTTPS proxy for HA Remote Bridge."""

from __future__ import annotations

import re
from urllib.parse import urljoin, urlparse

from aiohttp import ClientError, web

from homeassistant.components.http import HomeAssistantView
from homeassistant.const import CONF_URL
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import API_BASE, CONF_VERIFY_SSL, DEFAULT_VERIFY_SSL, DOMAIN

_HOP_BY_HOP_HEADERS = {
    "connection",
    "keep-alive",
    "proxy-authenticate",
    "proxy-authorization",
    "te",
    "trailers",
    "transfer-encoding",
    "upgrade",
    "host",
    "content-length",
}

_RESPONSE_HEADERS_TO_DROP = _HOP_BY_HOP_HEADERS | {
    "content-encoding",
    "content-length",
}


class HARemoteBridgeProxyView(HomeAssistantView):
    """Proxy requests to configured local resources."""

    url = API_BASE + "/{entry_id}/{path:.*}"
    name = "api:ha_remote_bridge:proxy"
    requires_auth = True

    async def get(self, request: web.Request, entry_id: str, path: str = "") -> web.Response:
        return await self._proxy(request, entry_id, path)

    async def post(self, request: web.Request, entry_id: str, path: str = "") -> web.Response:
        return await self._proxy(request, entry_id, path)

    async def put(self, request: web.Request, entry_id: str, path: str = "") -> web.Response:
        return await self._proxy(request, entry_id, path)

    async def patch(self, request: web.Request, entry_id: str, path: str = "") -> web.Response:
        return await self._proxy(request, entry_id, path)

    async def delete(self, request: web.Request, entry_id: str, path: str = "") -> web.Response:
        return await self._proxy(request, entry_id, path)

    async def head(self, request: web.Request, entry_id: str, path: str = "") -> web.Response:
        return await self._proxy(request, entry_id, path)

    async def _proxy(self, request: web.Request, entry_id: str, path: str) -> web.Response:
        """Forward an authenticated request to a configured target."""
        hass = request.app["hass"]
        user = request.get("hass_user")

        # MVP security model: only Home Assistant administrators may use bridges.
        if user is None or not user.is_admin:
            raise web.HTTPForbidden(text="HA Remote Bridge is currently admin-only")

        entry = hass.config_entries.async_get_entry(entry_id)
        if entry is None or entry.domain != DOMAIN:
            raise web.HTTPNotFound(text="Unknown HA Remote Bridge resource")

        base_url = entry.data[CONF_URL].rstrip("/")
        target_url = f"{base_url}/{path.lstrip('/')}"
        if request.query_string:
            target_url = f"{target_url}?{request.query_string}"

        if request.headers.get("Upgrade", "").lower() == "websocket":
            raise web.HTTPNotImplemented(text="WebSocket proxying is not implemented yet")

        headers = {
            key: value
            for key, value in request.headers.items()
            if key.lower() not in _HOP_BY_HOP_HEADERS
        }

        body = await request.read() if request.can_read_body else None
        session = async_get_clientsession(
            hass,
            verify_ssl=entry.data.get(CONF_VERIFY_SSL, DEFAULT_VERIFY_SSL),
        )

        try:
            async with session.request(
                request.method,
                target_url,
                headers=headers,
                data=body,
                allow_redirects=False,
            ) as upstream:
                raw_body = await upstream.read()
                response_headers = {
                    key: value
                    for key, value in upstream.headers.items()
                    if key.lower() not in _RESPONSE_HEADERS_TO_DROP
                }

                location = upstream.headers.get("Location")
                if location:
                    response_headers["Location"] = self._rewrite_location(
                        location,
                        target_url,
                        base_url,
                        entry_id,
                    )

                content_type = upstream.headers.get("Content-Type", "")
                if raw_body and "text/html" in content_type.lower():
                    raw_body = self._rewrite_html(raw_body, content_type, entry_id)

                return web.Response(
                    status=upstream.status,
                    headers=response_headers,
                    body=raw_body if request.method != "HEAD" else b"",
                )
        except ClientError as err:
            raise web.HTTPBadGateway(text=f"Unable to reach local resource: {err}") from err

    @staticmethod
    def _rewrite_location(location: str, current_url: str, base_url: str, entry_id: str) -> str:
        """Rewrite redirects that point back to the proxied resource."""
        resolved = urljoin(current_url, location)
        resolved_parts = urlparse(resolved)
        base_parts = urlparse(base_url)

        if (
            resolved_parts.scheme == base_parts.scheme
            and resolved_parts.netloc == base_parts.netloc
        ):
            path = resolved_parts.path or "/"
            query = f"?{resolved_parts.query}" if resolved_parts.query else ""
            return f"{API_BASE}/{entry_id}{path}{query}"

        return location

    @staticmethod
    def _rewrite_html(body: bytes, content_type: str, entry_id: str) -> bytes:
        """Best-effort rewrite of root-relative HTML links for the MVP."""
        charset = "utf-8"
        match = re.search(r"charset=([^;\s]+)", content_type, flags=re.IGNORECASE)
        if match:
            charset = match.group(1).strip("\"'")

        try:
            text = body.decode(charset, errors="replace")
        except LookupError:
            charset = "utf-8"
            text = body.decode(charset, errors="replace")

        prefix = f"{API_BASE}/{entry_id}"
        text = re.sub(
            r"(?i)(href|src|action)=(\"|')/(?!/)",
            rf"\1=\2{prefix}/",
            text,
        )
        return text.encode(charset, errors="replace")
