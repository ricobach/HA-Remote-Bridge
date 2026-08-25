"""Modern HA Remote Bridge runtime entrypoint.

Reuses the proven proxy compatibility layer while replacing the injected
legacy dashboard with the first-class modern UI and preserving ESPHome
metadata when discovered devices are added.
"""

from __future__ import annotations

import asyncio
import json
import secrets

from aiohttp import web

import compat_runner as compat
import launcher
import main
from ui_shell_v2 import INDEX_HTML

BRIDGE_UI_VERSION = "0.1.15"


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


main.add_resource = add_resource
main.INDEX_HTML = INDEX_HTML


async def _run() -> None:
    """Start the modern dashboard, discovery service, and compatibility proxy."""
    app = launcher.create_app()
    app.router.add_get("/api/discovery/esphome", compat.list_discovered_esphome)

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
