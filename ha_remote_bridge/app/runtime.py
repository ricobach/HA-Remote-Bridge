"""Canonical HA Remote Bridge runtime.

This module replaces the historical compat_runner_vXX startup chain. Feature
modules remain independently testable, but runtime composition is explicit here
so startup no longer depends on release-numbered runner modules.
"""

from __future__ import annotations

import asyncio
import json
import secrets
import sys
import time

from aiohttp import ClientError, ClientTimeout, web

# Importing compat_runner installs the mature generic Web proxy/rewrite layer
# and standalone ESPHome discovery. It is a feature module here, not a runtime
# parent; this module owns application startup.
import compat_runner as web_compat
import host_discovery
import host_discovery_expanded
import launcher
import main
import openapi_proxy_compat
import rutos_bootstrap
import rutos_compat
import same_origin_web_compat
import smb_support_v8 as smb
import ssh_password_auth
import ssh_persistence  # noqa: F401 - installs the persistent SSH manager base
import ssh_support as ssh
import swagger_request_compat
import virtual_host_support
import vnc_support as vnc
from ui_shell_v24 import INDEX_HTML

BRIDGE_UI_VERSION = "0.5.9"


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
    elif resource_type == "vnc":
        name, host, port, view_only = vnc.validate_vnc_payload(payload)
        resource = {
            "id": secrets.token_hex(8),
            "name": name,
            "url": vnc.vnc_resource_url(host, port),
            "verify_ssl": False,
            "resource_type": "vnc",
            "vnc_host": host,
            "vnc_port": port,
            "vnc_view_only": view_only,
        }
    elif resource_type == "smb":
        await smb.VAULT.load()
        name, host, port, credential_id = smb.validate_smb_payload(payload)
        resource = {
            "id": secrets.token_hex(8),
            "name": name,
            "url": smb.smb_resource_url(host, port),
            "verify_ssl": False,
            "resource_type": "smb",
            "smb_host": host,
            "smb_port": port,
            "smb_credential_id": credential_id,
        }
    else:
        name, url, verify_ssl = main.validate_resource_payload(payload)
        resource = {"id": secrets.token_hex(8), "name": name, "url": url, "verify_ssl": verify_ssl}
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
        resource["name"], resource["url"], resource.get("resource_type", "http"), resource.get("group_name", "auto"),
    )
    return web.json_response(resource, status=201)


async def update_resource(request: web.Request) -> web.Response:
    resource_id = request.match_info["resource_id"]
    resource = main.STORE.get(resource_id)
    if resource is None:
        raise web.HTTPNotFound(text="Unknown resource")
    try:
        payload = await request.json()
    except (json.JSONDecodeError, ValueError):
        raise web.HTTPBadRequest(text="Invalid JSON")

    payload_type = str(payload.get("resource_type", "")).strip().lower()
    current_type = str(resource.get("resource_type", "")).strip().lower()
    if current_type == "ssh" or payload_type == "ssh":
        await ssh.VAULT.load()
        name, host, port, username, credential_id = ssh.validate_ssh_payload(payload)
        resource.update({
            "name": name, "url": ssh.ssh_resource_url(host, port, username), "verify_ssl": False,
            "resource_type": "ssh", "ssh_host": host, "ssh_port": port,
            "ssh_user": username, "ssh_credential_id": credential_id,
        })
        await ssh.TTYD.stop(resource_id)
    elif current_type == "vnc" or payload_type == "vnc":
        name, host, port, view_only = vnc.validate_vnc_payload(payload)
        resource.update({
            "name": name, "url": vnc.vnc_resource_url(host, port), "verify_ssl": False,
            "resource_type": "vnc", "vnc_host": host, "vnc_port": port, "vnc_view_only": view_only,
        })
    elif current_type == "smb" or payload_type == "smb":
        await smb.VAULT.load()
        name, host, port, credential_id = smb.validate_smb_payload(payload)
        resource.update({
            "name": name, "url": smb.smb_resource_url(host, port), "verify_ssl": False,
            "resource_type": "smb", "smb_host": host, "smb_port": port, "smb_credential_id": credential_id,
        })
    else:
        name, url, verify_ssl = main.validate_resource_payload(payload)
        resource.update({"name": name, "url": url, "verify_ssl": verify_ssl})

    _apply_group_name(resource, payload)
    await main.STORE.save()
    main.LOGGER.info("Updated resource %s -> %s (group=%s)", resource["name"], resource["url"], resource.get("group_name", "auto"))
    return web.json_response(resource)


async def delete_resource(request: web.Request) -> web.Response:
    resource_id = request.match_info["resource_id"]
    resource = main.STORE.get(resource_id)
    if resource is None:
        raise web.HTTPNotFound(text="Unknown resource")
    if resource.get("resource_type") == "ssh":
        await ssh.TTYD.stop(resource_id)
    main.STORE.resources = [item for item in main.STORE.resources if item.get("id") != resource_id]
    await main.STORE.save()
    main.LOGGER.info("Deleted resource %s", resource.get("name", resource_id))
    return web.Response(status=204)


async def close_ssh_session(request: web.Request) -> web.Response:
    resource_id = request.match_info["resource_id"]
    resource = main.STORE.get(resource_id)
    if resource is None or resource.get("resource_type") != "ssh":
        raise web.HTTPNotFound(text="Unknown SSH resource")
    await ssh.TTYD.stop(resource_id)
    main.LOGGER.info("Closed persistent SSH session for %s", resource.get("name", resource_id))
    return web.Response(status=204)


async def _probe_resource(resource: dict) -> tuple[str, dict]:
    resource_id = resource["id"]
    if resource.get("resource_type") == "ssh":
        return resource_id, await ssh.probe_ssh_resource(resource)
    if resource.get("resource_type") == "vnc":
        return resource_id, await vnc.probe_vnc_resource(resource)
    if resource.get("resource_type") == "smb":
        return resource_id, await smb.probe_smb_resource(resource)

    started = time.monotonic()
    if main.CLIENT is None:
        return resource_id, {"online": False, "status": None, "latency_ms": None}
    try:
        upstream = await main.CLIENT.request(
            "GET", resource["url"],
            headers={"Accept": "text/html,*/*;q=0.1", "User-Agent": "HA-Remote-Bridge-Health/1", "Connection": "close"},
            allow_redirects=False,
            ssl=None if resource.get("verify_ssl", True) else False,
            timeout=ClientTimeout(total=4, connect=2, sock_connect=2, sock_read=2),
        )
        try:
            return resource_id, {
                "online": True, "status": upstream.status,
                "latency_ms": round((time.monotonic() - started) * 1000),
            }
        finally:
            upstream.release()
    except (ClientError, asyncio.TimeoutError, OSError):
        return resource_id, {
            "online": False, "status": None,
            "latency_ms": round((time.monotonic() - started) * 1000),
        }


async def resource_status(request: web.Request) -> web.Response:
    results = await asyncio.gather(*(_probe_resource(resource) for resource in main.STORE.resources))
    return web.json_response(dict(results))


def _install_runtime() -> None:
    """Compose current features in historical order without runner inheritance."""
    # Base CRUD handlers must exist before auth/virtual-host decorators capture them.
    main.add_resource = add_resource
    main.delete_resource = delete_resource
    launcher.update_resource = update_resource
    main.INDEX_HTML = INDEX_HTML

    # Compatibility modules are deliberately ordered from broadest/oldest to
    # narrowest/newest so wrapping semantics match the former runner chain.
    rutos_compat.install()
    rutos_bootstrap.install()
    ssh_password_auth.install_runtime_handlers(sys.modules[__name__])
    host_discovery.install()
    same_origin_web_compat.install()
    openapi_proxy_compat.install()
    swagger_request_compat.install()
    host_discovery_expanded.install()
    virtual_host_support.install()


async def _run() -> None:
    await ssh.VAULT.load()
    await smb.VAULT.load()

    app = launcher.create_app()

    # Discovery and health.
    app.router.add_get("/api/discovery/esphome", web_compat.list_discovered_esphome)
    app.router.add_get("/api/resources/status", resource_status)

    # SSH.
    app.router.add_get("/api/ssh/credentials", ssh.list_credentials)
    app.router.add_post("/api/ssh/credentials", ssh.add_credential)
    app.router.add_post("/api/ssh/credentials/generate", ssh.generate_credential)
    app.router.add_delete("/api/ssh/credentials/{credential_id}", ssh.delete_credential)
    app.router.add_delete("/api/ssh/sessions/{resource_id}", close_ssh_session)
    app.router.add_route("*", "/ssh/{resource_id}/{tail:.*}", ssh.proxy_ssh_terminal)

    # VNC.
    app.router.add_get("/novnc-assets/{tail:.*}", vnc.novnc_asset)
    app.router.add_get("/vnc/{resource_id}/", vnc.vnc_page)
    app.router.add_get("/vnc/{resource_id}/websockify", vnc.vnc_websocket)

    # SMB core, diagnostics, viewer and ZIP APIs accumulated through 0.4.5.
    app.router.add_get("/api/smb/credentials", smb.list_credentials)
    app.router.add_post("/api/smb/credentials", smb.add_credential)
    app.router.add_delete("/api/smb/credentials/{credential_id}", smb.delete_credential)
    app.router.add_post("/api/smb/test", smb.test_connection)
    app.router.add_get("/api/smb/{resource_id}/shares", smb.list_shares)
    app.router.add_get("/api/smb/{resource_id}/list", smb.list_directory)
    app.router.add_get("/api/smb/{resource_id}/download", smb.download_file)
    app.router.add_get("/api/smb/{resource_id}/raw", smb.raw_file)
    app.router.add_get("/api/smb/{resource_id}/text", smb.text_preview)
    app.router.add_get("/api/smb/{resource_id}/zip/list", smb.zip_list)
    app.router.add_get("/api/smb/{resource_id}/zip/raw", smb.zip_raw)
    app.router.add_get("/api/smb/{resource_id}/zip/text", smb.zip_text)
    app.router.add_get("/smb/{resource_id}/", smb.smb_page)
    app.router.add_get("/smb/{resource_id}/view", smb.viewer_page)
    app.router.add_get("/smb/{resource_id}/zip-entry", smb.zip_entry_page)

    runner = web.AppRunner(
        app,
        access_log=main.LOGGER,
        max_line_size=64 * 1024,
        max_field_size=64 * 1024,
        max_headers=128 * 1024,
    )
    try:
        web_compat.DISCOVERY.start()
        main.LOGGER.info("ESPHome mDNS discovery active")
    except Exception as err:
        main.LOGGER.warning("Unable to start ESPHome mDNS discovery: %r", err)

    await runner.setup()
    site = web.TCPSite(runner, host="0.0.0.0", port=main.PORT)
    await site.start()
    main.LOGGER.info("HA Remote Bridge runtime %s active (Web + SSH + VNC + SMB)", BRIDGE_UI_VERSION)
    try:
        await asyncio.Event().wait()
    finally:
        web_compat.DISCOVERY.close()
        await ssh.TTYD.close()
        await runner.cleanup()


_install_runtime()

if __name__ == "__main__":
    asyncio.run(_run())
