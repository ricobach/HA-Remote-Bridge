"""Paste clipboard text into an active tmux-backed SSH session.

Clipboard contents are accepted only for configured SSH resources and are passed
to tmux over stdin. The text is never placed in process arguments or logs.
"""

from __future__ import annotations

import asyncio
import json
import secrets

from aiohttp import web

import main
import ssh_support as ssh

MAX_PASTE_BYTES = 128 * 1024


async def _run_tmux(*args: str, stdin: bytes | None = None) -> tuple[int, bytes]:
    process = await asyncio.create_subprocess_exec(
        "tmux",
        *args,
        stdin=asyncio.subprocess.PIPE if stdin is not None else asyncio.subprocess.DEVNULL,
        stdout=asyncio.subprocess.DEVNULL,
        stderr=asyncio.subprocess.PIPE,
    )
    _stdout, stderr = await process.communicate(stdin)
    return process.returncode or 0, stderr


async def paste_ssh_session(request: web.Request) -> web.Response:
    resource_id = request.match_info["resource_id"]
    resource = main.STORE.get(resource_id)
    if resource is None or resource.get("resource_type") != "ssh":
        raise web.HTTPNotFound(text="Unknown SSH resource")

    try:
        payload = await request.json()
    except (json.JSONDecodeError, ValueError):
        raise web.HTTPBadRequest(text="Invalid JSON")

    text = payload.get("text", "")
    if not isinstance(text, str):
        raise web.HTTPBadRequest(text="Clipboard text must be a string")
    if "\x00" in text:
        raise web.HTTPBadRequest(text="Clipboard text cannot contain NUL characters")

    data = text.encode("utf-8")
    if len(data) > MAX_PASTE_BYTES:
        raise web.HTTPRequestEntityTooLarge(
            max_size=MAX_PASTE_BYTES,
            actual_size=len(data),
        )
    if not data:
        return web.Response(status=204)

    # The visible SSH frame should already have created the persistent session,
    # but ensure() is idempotent and safely creates it if required.
    await ssh.TTYD.ensure(resource)

    tmux_name = ssh.TTYD._tmux_name(resource_id)
    buffer_name = f"hrb-paste-{secrets.token_hex(8)}"

    load_code, load_err = await _run_tmux(
        "load-buffer", "-b", buffer_name, "-", stdin=data
    )
    if load_code:
        raise web.HTTPBadGateway(
            text=f"Unable to load SSH paste buffer: {load_err.decode(errors='replace')[:300]}"
        )

    try:
        paste_code, paste_err = await _run_tmux(
            "paste-buffer", "-b", buffer_name, "-t", tmux_name
        )
        if paste_code:
            raise web.HTTPBadGateway(
                text=f"Unable to paste into SSH session: {paste_err.decode(errors='replace')[:300]}"
            )
    finally:
        await _run_tmux("delete-buffer", "-b", buffer_name)

    main.LOGGER.info(
        "Pasted %d clipboard bytes into SSH session %s",
        len(data),
        resource.get("name", resource_id),
    )
    return web.Response(status=204)
