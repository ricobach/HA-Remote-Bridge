"""Per-connection SSH TERM override for HA Remote Bridge.

The default value, ``auto``, deliberately preserves the existing behaviour: the
remote SSH server receives the TERM value inherited from the tmux session. A
connection can instead advertise a conservative terminal type such as
``xterm-256color`` for appliances that do not understand ``tmux-256color``.
"""

from __future__ import annotations

import asyncio
import json
import shlex

from aiohttp import web

import main
import ssh_password_auth
import ssh_support as ssh

TERMINAL_TYPES = {"auto", "xterm-256color", "xterm", "vt100"}


def terminal_type_from_payload(payload: dict) -> str:
    value = str(payload.get("ssh_terminal_type", "auto")).strip().lower() or "auto"
    if value not in TERMINAL_TYPES:
        raise web.HTTPBadRequest(
            text="SSH terminal type must be auto, xterm-256color, xterm, or vt100"
        )
    return value


def terminal_type_for_resource(resource: dict) -> str:
    value = str(resource.get("ssh_terminal_type", "auto")).strip().lower() or "auto"
    return value if value in TERMINAL_TYPES else "auto"


class TerminalTypeTTYDManager(ssh_password_auth.PasswordAwarePersistentTTYDManager):
    """Password-aware persistent terminal manager with remote TERM override."""

    @staticmethod
    def _signature(resource: dict) -> tuple:
        return (
            *ssh_password_auth.PasswordAwarePersistentTTYDManager._signature(resource),
            terminal_type_for_resource(resource),
        )

    async def ensure(self, resource: dict) -> int:
        resource_id = resource["id"]
        signature = self._signature(resource)
        async with self._lock:
            existing = self._sessions.get(resource_id)
            if existing and existing["process"].returncode is None and existing["signature"] == signature:
                return existing["port"]

            if existing:
                changed = existing["signature"] != signature
                await self._stop_ttyd_locked(resource_id)
                if changed:
                    self._kill_tmux(resource_id)

            ssh._ensure_storage()
            ssh_password_auth._ensure_password_storage()
            port = self._free_port()
            mode = ssh_password_auth.auth_mode_for_resource(resource)
            terminal_type = terminal_type_for_resource(resource)
            credential = ssh.VAULT.get(resource.get("ssh_credential_id")) if mode == "key" else None

            ssh_command = [
                "ssh",
                "-tt",
                "-p", str(resource.get("ssh_port", 22)),
                "-o", f"UserKnownHostsFile={ssh.KNOWN_HOSTS_FILE}",
                "-o", "StrictHostKeyChecking=accept-new",
                "-o", "ServerAliveInterval=30",
                "-o", "ServerAliveCountMax=3",
            ]

            command_prefix: list[str] = []
            if mode == "key":
                if not credential:
                    raise web.HTTPBadRequest(text="The configured SSH key no longer exists")
                ssh_command.extend(["-i", credential["key_path"], "-o", "IdentitiesOnly=yes"])
            elif mode == "password":
                secret_path = ssh_password_auth.password_path(resource_id)
                if not ssh_password_auth.has_saved_password(resource_id):
                    raise web.HTTPBadRequest(text="This SSH connection has no saved password")
                command_prefix = ["sshpass", "-f", str(secret_path)]
                ssh_command.extend([
                    "-o", "PreferredAuthentications=keyboard-interactive,password",
                    "-o", "PubkeyAuthentication=no",
                    "-o", "PasswordAuthentication=yes",
                    "-o", "KbdInteractiveAuthentication=yes",
                    "-o", "NumberOfPasswordPrompts=1",
                ])

            ssh_command.append(f"{resource['ssh_user']}@{resource['ssh_host']}")

            # Keep tmux's own TERM untouched. Only the ssh process gets an
            # override, which controls the TERM value advertised to the remote
            # host. ``auto`` intentionally leaves the historic command intact.
            if terminal_type == "auto":
                effective_ssh_command = [*command_prefix, *ssh_command]
            else:
                effective_ssh_command = [
                    *command_prefix,
                    "env", f"TERM={terminal_type}",
                    *ssh_command,
                ]

            tmux_command = [
                "tmux", "new-session", "-A",
                "-s", self._tmux_name(resource_id),
                shlex.join(effective_ssh_command),
            ]
            command = [
                "ttyd",
                "-i", "127.0.0.1",
                "-p", str(port),
                "-b", f"/ssh/{resource_id}",
                "-W",
                *tmux_command,
            ]
            process = await asyncio.create_subprocess_exec(
                *command,
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.PIPE,
            )
            self._sessions[resource_id] = {
                "process": process,
                "port": port,
                "signature": signature,
            }

            for _ in range(30):
                if process.returncode is not None:
                    stderr = await process.stderr.read() if process.stderr else b""
                    self._sessions.pop(resource_id, None)
                    raise web.HTTPBadGateway(
                        text=f"SSH terminal failed to start: {stderr.decode(errors='replace')[:500]}"
                    )
                try:
                    _reader, writer = await asyncio.open_connection("127.0.0.1", port)
                    writer.close()
                    await writer.wait_closed()
                    main.LOGGER.info(
                        "Persistent SSH terminal ready for %s (tmux %s, auth=%s, TERM=%s)",
                        resource["name"],
                        self._tmux_name(resource_id),
                        mode,
                        terminal_type,
                    )
                    return port
                except OSError:
                    await asyncio.sleep(0.05)

            await self._stop_ttyd_locked(resource_id)
            raise web.HTTPGatewayTimeout(text="SSH terminal did not start in time")


def _apply_terminal_type(resource: dict, terminal_type: str) -> None:
    if terminal_type == "auto":
        resource.pop("ssh_terminal_type", None)
    else:
        resource["ssh_terminal_type"] = terminal_type


def install_runtime_handlers(base_runtime) -> None:
    """Install terminal-type persistence after the SSH authentication layer."""
    ssh.TTYD = TerminalTypeTTYDManager()

    original_add = base_runtime.add_resource
    original_update = base_runtime.update_resource

    async def add_resource(request: web.Request) -> web.Response:
        try:
            payload = await request.json()
        except Exception:
            raise web.HTTPBadRequest(text="Invalid JSON")
        if str(payload.get("resource_type", "")).strip().lower() != "ssh":
            return await original_add(request)

        terminal_type = terminal_type_from_payload(payload)
        response = await original_add(request)
        data = json.loads(response.text)
        resource = main.STORE.get(str(data.get("id", "")))
        if resource is None:
            return response
        _apply_terminal_type(resource, terminal_type)
        await main.STORE.save()
        return web.json_response(resource, status=response.status)

    async def update_resource(request: web.Request) -> web.Response:
        resource_id = request.match_info["resource_id"]
        resource = main.STORE.get(resource_id)
        if resource is None:
            raise web.HTTPNotFound(text="Unknown resource")
        try:
            payload = await request.json()
        except Exception:
            raise web.HTTPBadRequest(text="Invalid JSON")

        payload_type = str(payload.get("resource_type", "")).strip().lower()
        current_type = str(resource.get("resource_type", "")).strip().lower()
        if current_type != "ssh" and payload_type != "ssh":
            return await original_update(request)

        terminal_type = terminal_type_from_payload(payload)
        response = await original_update(request)
        resource = main.STORE.get(resource_id)
        if resource is None:
            return response
        _apply_terminal_type(resource, terminal_type)
        await main.STORE.save()
        return web.json_response(resource, status=response.status)

    base_runtime.add_resource = add_resource
    base_runtime.update_resource = update_resource
    main.add_resource = add_resource
    import launcher
    launcher.update_resource = update_resource
