"""Modern HA Remote Bridge runtime entrypoint."""

from __future__ import annotations

import asyncio
import json
import secrets
import time

from aiohttp import ClientError, ClientTimeout, web

import compat_runner as compat
import launcher
import main
import ssh_support as ssh
import ssh_persistence  # noqa: F401  # replaces ssh.TTYD with tmux-backed manager
from ui_shell_v6 import INDEX_HTML

BRIDGE_UI_VERSION = "0.2.2"


def _group_name_from_payload(payload: dict) -> str | None:
    value = str(payload.get("group_name", "")).strip()
    if len(value) > 100:
        raise web.HTTPBadRequest(text="Group / Host name is too long")
    return value or None


def _apply_group_name(resource: dict, payload: dict) -> None:
    group_name = _group_name_from_payload(payload)
    if group_name:
        resource["group_name"] = group_name
    else:
        resource.pop("group_name", None)


async def add_resource(request: web.Request) -> web.Response:
    """Create HTTP/HTTPS/ESPHome or SSH resources."""
    try:
        payload = await request.json()
    except (json.JSONDecodeError, ValueError):
        raise web.HTTPBadRequest(text="Invalid JSON")

    resource_type = str(payload.get("resource_type", "")).strip().lower()
    if resource_type == "ssh":
        await ssh.VAULT.load()
        name, host, port, username, credential_id = ssh.validate_ssh_payload(payload)
        resource = {
            "id": secrets.token_hex(8),
            "name": name,
            "url": ssh.ssh_resource_url(host, port, username),
            "verify_ssl": False,
            "resource_type": "ssh",
            "ssh_host": host,
            "ssh_port": port,
            "ssh_user": username,
            "ssh_credential_id": credential_id,
        }
    else:
        name, url, verify_ssl = main.validate_resource_payload(payload)
        resource = {
            "id": secrets.token_hex(8),
            "name": name,
            "url": url,
            "verify_ssl": verify_ssl,
        }
        if resource_type in {"esphome", "generic"}:
            resource["resource_type"] = resource_type
        discovery_key = str(payload.get("discovery_key", "")).strip()
        if resource_type == "esphome" and discovery_key:
            resource["discovery_key"] = discovery_key[:255]

    _apply_group_name(resource, payload)
    main.STORE.resources.append(resource)
    await main.STORE.save()
    main.LOGGER.info(
        "Added resource %s -> %s (%s, group=%s)",
        resource["name"],
        resource["url"],
        resource.get("resource_type", "http"),
        resource.get("group_name", "auto"),
    )
    return web.json_response(resource, status=201)


async def update_resource(request: web.Request) -> web.Response:
    """Update a resource while preserving its stable id and metadata."""
    resource_id = request.match_info["resource_id"]
    resource = main.STORE.get(resource_id)
    if resource is None:
        raise web.HTTPNotFound(text="Unknown resource")
    try:
        payload = await request.json()
    except (json.JSONDecodeError, ValueError):
        raise web.HTTPBadRequest(text="Invalid JSON")

    if resource.get("resource_type") == "ssh" or str(payload.get("resource_type", "")).lower() == "ssh":
        await ssh.VAULT.load()
        name, host, port, username, credential_id = ssh.validate_ssh_payload(payload)
        resource.update({
            "name": name,
            "url": ssh.ssh_resource_url(host, port, username),
            "verify_ssl": False,
            "resource_type": "ssh",
            "ssh_host": host,
            "ssh_port": port,
            "ssh_user": username,
            "ssh_credential_id": credential_id,
        })
        await ssh.TTYD.stop(resource_id)
    else:
        name, url, verify_ssl = main.validate_resource_payload(payload)
        resource.update({"name": name, "url": url, "verify_ssl": verify_ssl})

    _apply_group_name(resource, payload)
    await main.STORE.save()
    main.LOGGER.info(
        "Updated resource %s -> %s (group=%s)",
        resource["name"],
        resource["url"],
        resource.get("group_name", "auto"),
    )
    return web.json_response(resource)


async def delete_resource(request: web.Request) -> web.Response:
    resource_id = request.match_info["resource_id"]
    resource = main.STORE.get(resource_id)
    if resource is None:
        raise web.HTTPNotFound(text="Unknown resource")
    await ssh.TTYD.stop(resource_id)
    main.STORE.resources = [item for item in main.STORE.resources if item.get("id") != resource_id]
    await main.STORE.save()
    main.LOGGER.info("Deleted resource %s", resource.get("name", resource_id))
    return web.Response(status=204)


async def close_ssh_session(request: web.Request) -> web.Response:
    """Explicitly terminate one persistent SSH/tmux session without deleting its resource."""
    resource_id = request.match_info["resource_id"]
    resource = main.STORE.get(resource_id)
    if resource is None or resource.get("resource_type") != "ssh":
        raise web.HTTPNotFound(text="Unknown SSH resource")
    await ssh.TTYD.stop(resource_id)
    main.LOGGER.info("Closed persistent SSH session for %s", resource.get("name", resource_id))
    return web.Response(status=204)


async def _probe_resource(resource: dict) -> tuple[str, dict]:
    """Return a short reachability result for one configured resource."""
    resource_id = resource["id"]
    if resource.get("resource_type") == "ssh":
        return resource_id, await ssh.probe_ssh_resource(resource)

    started = time.monotonic()
    if main.CLIENT is None:
        return resource_id, {"online": False, "status": None, "latency_ms": None}
    try:
        upstream = await main.CLIENT.request(
            "GET",
            resource["url"],
            headers={"Accept": "text/html,*/*;q=0.1", "User-Agent": "HA-Remote-Bridge-Health/1", "Connection": "close"},
            allow_redirects=False,
            ssl=None if resource.get("verify_ssl", True) else False,
            timeout=ClientTimeout(total=4, connect=2, sock_connect=2, sock_read=2),
        )
        try:
            return resource_id, {
                "online": True,
                "status": upstream.status,
                "latency_ms": round((time.monotonic() - started) * 1000),
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
    results = await asyncio.gather(*(_probe_resource(resource) for resource in main.STORE.resources))
    return web.json_response(dict(results))


main.add_resource = add_resource
main.delete_resource = delete_resource
launcher.update_resource = update_resource
main.INDEX_HTML = INDEX_HTML


async def _run() -> None:
    """Start dashboard, discovery, HTTP proxy and SSH terminal support."""
    await ssh.VAULT.load()
    app = launcher.create_app()
    app.router.add_get("/api/discovery/esphome", compat.list_discovered_esphome)
    app.router.add_get("/api/resources/status", resource_status)
    app.router.add_get("/api/ssh/credentials", ssh.list_credentials)
    app.router.add_post("/api/ssh/credentials", ssh.add_credential)
    app.router.add_post("/api/ssh/credentials/generate", ssh.generate_credential)
    app.router.add_delete("/api/ssh/credentials/{credential_id}", ssh.delete_credential)
    app.router.add_delete("/api/ssh/sessions/{resource_id}", close_ssh_session)
    app.router.add_route("*", "/ssh/{resource_id}/{tail:.*}", ssh.proxy_ssh_terminal)

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
        await ssh.TTYD.close()
        await runner.cleanup()


if __name__ == "__main__":
    asyncio.run(_run())
