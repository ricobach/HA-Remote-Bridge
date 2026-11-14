"""Send selected navigation keys into an active tmux-backed SSH session."""

from __future__ import annotations

import asyncio
import json

from aiohttp import web

import main
import ssh_support as ssh

TMUX_KEYS = {
    "tab": "Tab",
    "left": "Left",
    "up": "Up",
    "down": "Down",
    "right": "Right",
}


async def send_ssh_key(request: web.Request) -> web.Response:
    resource_id = request.match_info["resource_id"]
    resource = main.STORE.get(resource_id)
    if resource is None or resource.get("resource_type") != "ssh":
        raise web.HTTPNotFound(text="Unknown SSH resource")

    try:
        payload = await request.json()
    except (json.JSONDecodeError, ValueError):
        raise web.HTTPBadRequest(text="Invalid JSON")

    key = str(payload.get("key", "")).strip().lower()
    tmux_key = TMUX_KEYS.get(key)
    if tmux_key is None:
        raise web.HTTPBadRequest(text="Unsupported SSH key")

    await ssh.TTYD.ensure(resource)
    tmux_name = ssh.TTYD._tmux_name(resource_id)

    process = await asyncio.create_subprocess_exec(
        "tmux",
        "send-keys",
        "-t",
        tmux_name,
        tmux_key,
        stdout=asyncio.subprocess.DEVNULL,
        stderr=asyncio.subprocess.PIPE,
    )
    _stdout, stderr = await process.communicate()
    if process.returncode:
        raise web.HTTPBadGateway(
            text=f"Unable to send SSH key: {stderr.decode(errors='replace')[:300]}"
        )

    return web.Response(status=204)
