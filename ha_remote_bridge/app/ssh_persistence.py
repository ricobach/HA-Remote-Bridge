"""Persistent SSH terminal sessions for HA Remote Bridge.

Each SSH resource owns one tmux session. ttyd is only the browser attachment
layer; disconnecting the browser detaches from tmux without terminating the
SSH client or commands running in that terminal.
"""

from __future__ import annotations

import asyncio
import socket
import subprocess

from aiohttp import web

import main
import ssh_support as ssh


class PersistentTTYDManager(ssh.TTYDManager):
    """Run ttyd attachments backed by persistent tmux sessions."""

    @staticmethod
    def _tmux_name(resource_id: str) -> str:
        return f"hrb_{resource_id}"

    @classmethod
    def _kill_tmux(cls, resource_id: str) -> None:
        try:
            subprocess.run(
                ["tmux", "kill-session", "-t", cls._tmux_name(resource_id)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=3,
                check=False,
            )
        except (OSError, subprocess.SubprocessError):
            pass

    async def ensure(self, resource: dict) -> int:
        resource_id = resource["id"]
        signature = self._signature(resource)
        async with self._lock:
            existing = self._sessions.get(resource_id)
            if existing and existing["process"].returncode is None and existing["signature"] == signature:
                return existing["port"]

            # A dead ttyd attachment does not imply a dead tmux/SSH session.
            # Preserve tmux when the resource definition is unchanged so a new
            # ttyd process can simply reattach to the existing terminal.
            if existing:
                changed = existing["signature"] != signature
                await self._stop_ttyd_locked(resource_id)
                if changed:
                    self._kill_tmux(resource_id)

            ssh._ensure_storage()
            port = self._free_port()
            credential = ssh.VAULT.get(resource.get("ssh_credential_id"))
            ssh_command = [
                "ssh",
                "-tt",
                "-p", str(resource.get("ssh_port", 22)),
                "-o", f"UserKnownHostsFile={ssh.KNOWN_HOSTS_FILE}",
                "-o", "StrictHostKeyChecking=accept-new",
                "-o", "ServerAliveInterval=30",
                "-o", "ServerAliveCountMax=3",
            ]
            if credential:
                ssh_command.extend(["-i", credential["key_path"], "-o", "IdentitiesOnly=yes"])
            ssh_command.append(f"{resource['ssh_user']}@{resource['ssh_host']}")

            tmux_command = [
                "tmux", "new-session", "-A",
                "-s", self._tmux_name(resource_id),
                "--",
                *ssh_command,
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
                    reader, writer = await asyncio.open_connection("127.0.0.1", port)
                    writer.close()
                    await writer.wait_closed()
                    main.LOGGER.info(
                        "Persistent SSH terminal ready for %s (tmux %s)",
                        resource["name"],
                        self._tmux_name(resource_id),
                    )
                    return port
                except OSError:
                    await asyncio.sleep(0.05)

            await self._stop_ttyd_locked(resource_id)
            raise web.HTTPGatewayTimeout(text="SSH terminal did not start in time")

    async def _stop_ttyd_locked(self, resource_id: str) -> None:
        session = self._sessions.pop(resource_id, None)
        if not session:
            return
        process = session["process"]
        if process.returncode is None:
            process.terminate()
            try:
                await asyncio.wait_for(process.wait(), timeout=2)
            except asyncio.TimeoutError:
                process.kill()
                await process.wait()

    async def _stop_locked(self, resource_id: str) -> None:
        """Stop both browser attachment and persistent SSH terminal."""
        await self._stop_ttyd_locked(resource_id)
        self._kill_tmux(resource_id)


# Replace the manager used by ssh_support.proxy_ssh_terminal at runtime.
ssh.TTYD = PersistentTTYDManager()
