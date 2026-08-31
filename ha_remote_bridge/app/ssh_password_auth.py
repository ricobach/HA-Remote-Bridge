"""Per-connection saved-password authentication for HA Remote Bridge SSH.

Passwords are stored separately from resource definitions under /data/ssh/passwords
with restrictive filesystem permissions. They are never returned by the API and are
passed to OpenSSH via sshpass -f so the secret does not appear in process arguments.
"""

from __future__ import annotations

import asyncio
import os
import secrets
import shlex
import subprocess
from pathlib import Path

from aiohttp import web

import launcher
import main
import ssh_persistence
import ssh_support as ssh

PASSWORD_DIR = ssh.SSH_DIR / "passwords"
AUTH_MODES = {"prompt", "key", "password"}


def _ensure_password_storage() -> None:
    ssh._ensure_storage()
    PASSWORD_DIR.mkdir(parents=True, exist_ok=True)
    os.chmod(PASSWORD_DIR, 0o700)


def password_path(resource_id: str) -> Path:
    return PASSWORD_DIR / resource_id


def has_saved_password(resource_id: str) -> bool:
    path = password_path(resource_id)
    return path.is_file() and path.stat().st_size > 0


def save_password(resource_id: str, password: str) -> None:
    if not isinstance(password, str):
        raise web.HTTPBadRequest(text="SSH password must be text")
    if not password:
        raise web.HTTPBadRequest(text="SSH password is required")
    if "\x00" in password or "\n" in password or "\r" in password:
        raise web.HTTPBadRequest(text="SSH password cannot contain line breaks or NUL characters")
    if len(password.encode("utf-8")) > 4096:
        raise web.HTTPBadRequest(text="SSH password is too long")

    _ensure_password_storage()
    path = password_path(resource_id)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(password + "\n", encoding="utf-8")
    os.chmod(tmp, 0o600)
    os.replace(tmp, path)
    os.chmod(path, 0o600)


def delete_password(resource_id: str) -> None:
    password_path(resource_id).unlink(missing_ok=True)


def auth_mode_from_payload(payload: dict, credential_id: str | None) -> str:
    raw = str(payload.get("ssh_auth_mode", "")).strip().lower()
    mode = raw or ("key" if credential_id else "prompt")
    if mode not in AUTH_MODES:
        raise web.HTTPBadRequest(text="SSH authentication mode must be prompt, key, or password")
    if mode == "key" and not credential_id:
        raise web.HTTPBadRequest(text="Select an SSH key for key authentication")
    return mode


def auth_mode_for_resource(resource: dict) -> str:
    raw = str(resource.get("ssh_auth_mode", "")).strip().lower()
    if raw in AUTH_MODES:
        return raw
    return "key" if resource.get("ssh_credential_id") else "prompt"


class PasswordAwarePersistentTTYDManager(ssh_persistence.PersistentTTYDManager):
    """Persistent ttyd/tmux manager with optional per-resource password auth."""

    @staticmethod
    def _signature(resource: dict) -> tuple:
        resource_id = str(resource.get("id", ""))
        path = password_path(resource_id)
        try:
            password_stamp = path.stat().st_mtime_ns
        except OSError:
            password_stamp = None
        return (
            resource.get("ssh_host"),
            resource.get("ssh_port", 22),
            resource.get("ssh_user"),
            resource.get("ssh_credential_id"),
            auth_mode_for_resource(resource),
            password_stamp,
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
            _ensure_password_storage()
            port = self._free_port()
            mode = auth_mode_for_resource(resource)
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
                secret_path = password_path(resource_id)
                if not has_saved_password(resource_id):
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
            effective_ssh_command = [*command_prefix, *ssh_command]

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
                        "Persistent SSH terminal ready for %s (tmux %s, auth=%s)",
                        resource["name"],
                        self._tmux_name(resource_id),
                        mode,
                    )
                    return port
                except OSError:
                    await asyncio.sleep(0.05)

            await self._stop_ttyd_locked(resource_id)
            raise web.HTTPGatewayTimeout(text="SSH terminal did not start in time")


def install_runtime_handlers(base_runtime) -> None:
    """Install resource CRUD and terminal hooks on the composed runtime."""
    ssh.TTYD = PasswordAwarePersistentTTYDManager()

    original_add = base_runtime.add_resource
    original_update = base_runtime.update_resource
    original_delete = base_runtime.delete_resource

    async def add_resource(request: web.Request) -> web.Response:
        try:
            payload = await request.json()
        except Exception:
            raise web.HTTPBadRequest(text="Invalid JSON")
        if str(payload.get("resource_type", "")).strip().lower() != "ssh":
            return await original_add(request)

        await ssh.VAULT.load()
        name, host, port, username, credential_id = ssh.validate_ssh_payload(payload)
        mode = auth_mode_from_payload(payload, credential_id)
        if mode != "key":
            credential_id = None

        resource_id = secrets.token_hex(8)
        password = str(payload.get("ssh_password", ""))
        if mode == "password":
            if not password:
                raise web.HTTPBadRequest(text="Enter a password for saved-password authentication")
            save_password(resource_id, password)

        resource = {
            "id": resource_id,
            "name": name,
            "url": ssh.ssh_resource_url(host, port, username),
            "verify_ssl": False,
            "resource_type": "ssh",
            "ssh_host": host,
            "ssh_port": port,
            "ssh_user": username,
            "ssh_credential_id": credential_id,
            "ssh_auth_mode": mode,
            "ssh_has_password": mode == "password" and has_saved_password(resource_id),
        }
        base_runtime._apply_group_name(resource, payload)
        main.STORE.resources.append(resource)
        try:
            await main.STORE.save()
        except Exception:
            delete_password(resource_id)
            main.STORE.resources = [r for r in main.STORE.resources if r.get("id") != resource_id]
            raise
        main.LOGGER.info(
            "Added SSH resource %s -> %s (auth=%s, group=%s)",
            resource["name"], resource["url"], mode, resource.get("group_name", "auto"),
        )
        return web.json_response(resource, status=201)

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

        await ssh.VAULT.load()
        name, host, port, username, credential_id = ssh.validate_ssh_payload(payload)
        mode = auth_mode_from_payload(payload, credential_id)
        password = str(payload.get("ssh_password", ""))

        await ssh.TTYD.stop(resource_id)
        if mode == "password":
            credential_id = None
            if password:
                save_password(resource_id, password)
            elif not has_saved_password(resource_id):
                raise web.HTTPBadRequest(text="Enter a password for saved-password authentication")
        else:
            delete_password(resource_id)

        resource.update({
            "name": name,
            "url": ssh.ssh_resource_url(host, port, username),
            "verify_ssl": False,
            "resource_type": "ssh",
            "ssh_host": host,
            "ssh_port": port,
            "ssh_user": username,
            "ssh_credential_id": credential_id if mode == "key" else None,
            "ssh_auth_mode": mode,
            "ssh_has_password": mode == "password" and has_saved_password(resource_id),
        })
        base_runtime._apply_group_name(resource, payload)
        await main.STORE.save()
        main.LOGGER.info(
            "Updated SSH resource %s -> %s (auth=%s, group=%s)",
            resource["name"], resource["url"], mode, resource.get("group_name", "auto"),
        )
        return web.json_response(resource)

    async def delete_resource(request: web.Request) -> web.Response:
        resource_id = request.match_info["resource_id"]
        resource = main.STORE.get(resource_id)
        if resource is None or resource.get("resource_type") != "ssh":
            return await original_delete(request)
        await ssh.TTYD.stop(resource_id)
        delete_password(resource_id)
        main.STORE.resources = [item for item in main.STORE.resources if item.get("id") != resource_id]
        await main.STORE.save()
        main.LOGGER.info("Deleted SSH resource %s and its saved password", resource.get("name", resource_id))
        return web.Response(status=204)

    base_runtime.add_resource = add_resource
    base_runtime.update_resource = update_resource
    base_runtime.delete_resource = delete_resource
    main.add_resource = add_resource
    main.delete_resource = delete_resource
    launcher.update_resource = update_resource
