"""Modern HA Remote Bridge runtime entrypoint.

Reuses the proven proxy compatibility layer while replacing the injected
legacy dashboard with the first-class modern UI and preserving ESPHome
metadata when discovered devices are added.
"""

from __future__ import annotations

import asyncio
import json
import secrets
import time

from aiohttp import ClientError, ClientTimeout, web

import compat_runner as compat
import launcher
import main
from ui_shell_v3 import INDEX_HTML

BRIDGE_UI_VERSION = "0.1.17"


async def add_resource(request: web.Request) -> web.Response:
    """Create a resource and retain safe optional classification metadata."""
    try:
        payload = await request.json()
    except (json.JSONDecodeError, ValueError):
        raise web.HTTPBadRequest(text="Invalid JSON")

    name, url, verify_ssl = main.validate_resource_payload(payload)
    resource = {
        "id": secrets.token_hex(8),
        "name": name,
        "url": url,
        "verify_ssl": verify_ssl,
    }

    resource_type = str(payload.get("resource_type", "")).strip().lower()
    if resource_type in {"esphome", "generic"}:
        resource["resource_type"] = resource_type

    discovery_key = str(payload.get("discovery_key", "")).strip()
    if resource_type == "esphome" and discovery_key:
        resource["discovery_key"] = discovery_key[:255]

    main.STORE.resources.append(resource)
    await main.STORE.save()
    main.LOGGER.info("Added resource %s -> %s%s", name, url, f" ({resource_type})" if resource_type else "")
    return web.json_response(resource, status=201)


async def _probe_resource(resource: dict) -> tuple[str, dict]:
    """Return a short reachability result for one configured resource."""
    resource_id = resource["id"]
    started = time.monotonic()

    if main.CLIENT is None:
        return resource_id, {"online": False, "status": None, "latency_ms": None}

    try:
        upstream = await main.CLIENT.request(
            "GET",
            resource["url"],
            headers={
                "Accept": "text/html,*/*;q=0.1",
                "User-Agent": "HA-Remote-Bridge-Health/1",
                "Connection": "close",
            },
            allow_redirects=False,
            ssl=None if resource.get("verify_ssl", True) else False,
            timeout=ClientTimeout(total=4, connect=2, sock_connect=2, sock_read=2),
        )
        try:
            latency_ms = round((time.monotonic() - started) * 1000)
            return resource_id, {
                "online": True,
                "status": upstream.status,
                "latency_ms": latency_ms,
            }
        finally:
            upstream.release()
    except (ClientError, asyncio.TimeoutError, OSError):
        return resource_id, {
            "online": False,
            "status": None,
            "latency_ms": round((time.monotonic() - started) * 1000),
        }


async def resource_status(request: web.Request) -> web.Response:
    """Probe all configured resources concurrently for dashboard status chips."""
    results = await asyncio.gather(*(_probe_resource(resource) for resource in main.STORE.resources))
    return web.json_response(dict(results))


main.add_resource = add_resource
main.INDEX_HTML = INDEX_HTML


async def _run() -> None:
    """Start the modern dashboard, discovery service, and compatibility proxy."""
    app = launcher.create_app()
    app.router.add_get("/api/discovery/esphome", compat.list_discovered_esphome)
    app.router.add_get("/api/resources/status", resource_status)

    runner = web.AppRunner(
        app,
        access_log=main.LOGGER,
        max_line_size=64 * 1024,
        max_field_size=64 * 1024,
        max_headers=128 * 1024,
    )

    try:
        compat.DISCOVERY.start()
        main.LOGGER.info("ESPHome mDNS discovery active")
    except Exception as err:
        main.LOGGER.warning("Unable to start ESPHome mDNS discovery: %r", err)

    await runner.setup()
    site = web.TCPSite(runner, host="0.0.0.0", port=main.PORT)
    await site.start()
    main.LOGGER.info("Modern dashboard %s active", BRIDGE_UI_VERSION)

    try:
        await asyncio.Event().wait()
    finally:
        compat.DISCOVERY.close()
        await runner.cleanup()


if __name__ == "__main__":
    asyncio.run(_run())
