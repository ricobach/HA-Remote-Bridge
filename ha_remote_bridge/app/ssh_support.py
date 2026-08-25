"""SSH terminal and reusable credential support for HA Remote Bridge."""

from __future__ import annotations

import asyncio
import json
import os
import secrets
import socket
import subprocess
import time
from pathlib import Path
from urllib.parse import quote

from aiohttp import ClientError, ClientTimeout, WSMsgType, web

import main

DATA_DIR = Path("/data")
SSH_DIR = DATA_DIR / "ssh"
KEY_DIR = SSH_DIR / "keys"
CREDENTIALS_FILE = SSH_DIR / "credentials.json"
KNOWN_HOSTS_FILE = SSH_DIR / "known_hosts"


def _ensure_storage() -> None:
    SSH_DIR.mkdir(parents=True, exist_ok=True)
    KEY_DIR.mkdir(parents=True, exist_ok=True)
    os.chmod(SSH_DIR, 0o700)
    os.chmod(KEY_DIR, 0o700)
    if not KNOWN_HOSTS_FILE.exists():
        KNOWN_HOSTS_FILE.touch(mode=0o600)
    else:
        os.chmod(KNOWN_HOSTS_FILE, 0o600)


def _atomic_json_write(path: Path, value: object) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.chmod(tmp, 0o600)
    os.replace(tmp, path)
    os.chmod(path, 0o600)


class SSHCredentialVault:
    """Persist reusable SSH private keys separately from normal resources."""

    def __init__(self) -> None:
        self._lock = asyncio.Lock()
        self._loaded = False
        self._items: list[dict] = []

    async def load(self) -> None:
        async with self._lock:
            if self._loaded:
                return
            _ensure_storage()
            if CREDENTIALS_FILE.exists():
                try:
                    data = json.loads(CREDENTIALS_FILE.read_text(encoding="utf-8"))
                    if isinstance(data, list):
                        self._items = [item for item in data if isinstance(item, dict)]
                except (OSError, json.JSONDecodeError):
                    main.LOGGER.exception("Unable to load SSH credential vault")
                    self._items = []
            self._loaded = True

    async def list_public(self) -> list[dict]:
        await self.load()
        return [self._public(item) for item in self._items]

    def get(self, credential_id: str | None) -> dict | None:
        if not credential_id:
            return None
        return next((item for item in self._items if item.get("id") == credential_id), None)

    @staticmethod
    def _public(item: dict) -> dict:
        return {
            "id": item.get("id"),
            "name": item.get("name"),
            "kind": item.get("kind", "private_key"),
            "fingerprint": item.get("fingerprint"),
            "public_key": item.get("public_key"),
            "created_at": item.get("created_at"),
        }

    async def _save(self) -> None:
        _atomic_json_write(CREDENTIALS_FILE, self._items)

    async def add_private_key(self, name: str, private_key: str) -> dict:
        await self.load()
        name = name.strip()
        private_key = private_key.strip() + "\n"
        if not name:
            raise web.HTTPBadRequest(text="Credential name is required")
        if len(name) > 80:
            raise web.HTTPBadRequest(text="Credential name is too long")
        if len(private_key) > 128 * 1024:
            raise web.HTTPBadRequest(text="Private key is too large")
        if "PRIVATE KEY" not in private_key or "-----BEGIN " not in private_key:
            raise web.HTTPBadRequest(text="This does not look like an SSH private key")

        credential_id = secrets.token_hex(8)
        key_path = KEY_DIR / credential_id
        key_path.write_text(private_key, encoding="utf-8")
        os.chmod(key_path, 0o600)

        public_key = None
        fingerprint = None
        try:
            pub = subprocess.run(
                ["ssh-keygen", "-y", "-P", "", "-f", str(key_path)],
                capture_output=True,
                text=True,
                timeout=5,
                check=True,
            ).stdout.strip()
            if pub:
                public_key = pub
                check = subprocess.run(
                    ["ssh-keygen", "-lf", "-"],
                    input=pub + "\n",
                    capture_output=True,
                    text=True,
                    timeout=5,
                    check=True,
                ).stdout.strip()
                fingerprint = check.split()[1] if len(check.split()) > 1 else check
        except (subprocess.SubprocessError, OSError):
            # Encrypted keys are valid too; OpenSSH will prompt for the passphrase
            # inside the terminal session when they are used.
            pass

        item = {
            "id": credential_id,
            "name": name,
            "kind": "private_key",
            "key_path": str(key_path),
            "public_key": public_key,
            "fingerprint": fingerprint,
            "created_at": int(time.time()),
        }
        self._items.append(item)
        await self._save()
        main.LOGGER.info("Added reusable SSH key credential %s", name)
        return self._public(item)

    async def generate_ed25519(self, name: str) -> dict:
        await self.load()
        name = name.strip()
        if not name:
            raise web.HTTPBadRequest(text="Credential name is required")
        if len(name) > 80:
            raise web.HTTPBadRequest(text="Credential name is too long")

        credential_id = secrets.token_hex(8)
        key_path = KEY_DIR / credential_id
        try:
            subprocess.run(
                [
                    "ssh-keygen", "-q", "-t", "ed25519", "-N", "",
                    "-C", f"HA Remote Bridge: {name}", "-f", str(key_path),
                ],
                capture_output=True,
                text=True,
                timeout=10,
                check=True,
            )
            os.chmod(key_path, 0o600)
            public_key = key_path.with_suffix(".pub").read_text(encoding="utf-8").strip()
            key_path.with_suffix(".pub").unlink(missing_ok=True)
            check = subprocess.run(
                ["ssh-keygen", "-lf", "-"],
                input=public_key + "\n",
                capture_output=True,
                text=True,
                timeout=5,
                check=True,
            ).stdout.strip()
            fingerprint = check.split()[1] if len(check.split()) > 1 else check
        except (subprocess.SubprocessError, OSError) as err:
            key_path.unlink(missing_ok=True)
            raise web.HTTPInternalServerError(text=f"Unable to generate SSH key: {err}") from err

        item = {
            "id": credential_id,
            "name": name,
            "kind": "generated_ed25519",
            "key_path": str(key_path),
            "public_key": public_key,
            "fingerprint": fingerprint,
            "created_at": int(time.time()),
        }
        self._items.append(item)
        await self._save()
        main.LOGGER.info("Generated reusable ED25519 SSH key %s", name)
        return self._public(item)

    async def delete(self, credential_id: str) -> None:
        await self.load()
        item = self.get(credential_id)
        if item is None:
            raise web.HTTPNotFound(text="Unknown SSH credential")
        if any(resource.get("ssh_credential_id") == credential_id for resource in main.STORE.resources):
            raise web.HTTPConflict(text="This SSH key is still used by one or more resources")
        self._items.remove(item)
        Path(item.get("key_path", "")).unlink(missing_ok=True)
        await self._save()


VAULT = SSHCredentialVault()


def validate_ssh_payload(payload: dict) -> tuple[str, str, int, str, str | None]:
    name = str(payload.get("name", "")).strip()
    host = str(payload.get("ssh_host", "")).strip()
    username = str(payload.get("ssh_user", "")).strip()
    credential_id = str(payload.get("ssh_credential_id", "")).strip() or None
    try:
        port = int(payload.get("ssh_port", 22))
    except (TypeError, ValueError):
        raise web.HTTPBadRequest(text="SSH port must be a number")

    if not name:
        raise web.HTTPBadRequest(text="Name is required")
    if len(name) > 100:
        raise web.HTTPBadRequest(text="Name is too long")
    if not host or any(ch in host for ch in "/\\\r\n\t "):
        raise web.HTTPBadRequest(text="A valid SSH hostname or IP address is required")
    if len(host) > 255:
        raise web.HTTPBadRequest(text="SSH host is too long")
    if not username or any(ch in username for ch in "\r\n\t @"):
        raise web.HTTPBadRequest(text="A valid SSH username is required")
    if len(username) > 64:
        raise web.HTTPBadRequest(text="SSH username is too long")
    if not 1 <= port <= 65535:
        raise web.HTTPBadRequest(text="SSH port must be between 1 and 65535")
    if credential_id and VAULT.get(credential_id) is None:
        raise web.HTTPBadRequest(text="Unknown SSH credential")
    return name, host, port, username, credential_id


def ssh_resource_url(host: str, port: int, username: str) -> str:
    display_host = f"[{host}]" if ":" in host and not host.startswith("[") else host
    return f"ssh://{quote(username, safe='')}@{display_host}:{port}"


class TTYDManager:
    """Run one loopback-only ttyd/OpenSSH process per active SSH resource."""

    def __init__(self) -> None:
        self._lock = asyncio.Lock()
        self._sessions: dict[str, dict] = {}

    @staticmethod
    def _signature(resource: dict) -> tuple:
        return (
            resource.get("ssh_host"),
            resource.get("ssh_port", 22),
            resource.get("ssh_user"),
            resource.get("ssh_credential_id"),
        )

    @staticmethod
    def _free_port() -> int:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            sock.bind(("127.0.0.1", 0))
            return int(sock.getsockname()[1])
        finally:
            sock.close()

    async def ensure(self, resource: dict) -> int:
        resource_id = resource["id"]
        signature = self._signature(resource)
        async with self._lock:
            existing = self._sessions.get(resource_id)
            if existing and existing["process"].returncode is None and existing["signature"] == signature:
                return existing["port"]
            if existing:
                await self._stop_locked(resource_id)

            _ensure_storage()
            port = self._free_port()
            credential = VAULT.get(resource.get("ssh_credential_id"))
            ssh_command = [
                "ssh",
                "-tt",
                "-p", str(resource.get("ssh_port", 22)),
                "-o", f"UserKnownHostsFile={KNOWN_HOSTS_FILE}",
                "-o", "StrictHostKeyChecking=accept-new",
                "-o", "ServerAliveInterval=30",
                "-o", "ServerAliveCountMax=3",
            ]
            if credential:
                ssh_command.extend(["-i", credential["key_path"], "-o", "IdentitiesOnly=yes"])
            ssh_command.append(f"{resource['ssh_user']}@{resource['ssh_host']}")

            command = [
                "ttyd",
                "-i", "127.0.0.1",
                "-p", str(port),
                "-b", f"/ssh/{resource_id}",
                "-W",
                *ssh_command,
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

            # Give ttyd a moment to bind so the first browser request doesn't race it.
            for _ in range(20):
                if process.returncode is not None:
                    stderr = await process.stderr.read() if process.stderr else b""
                    self._sessions.pop(resource_id, None)
                    raise web.HTTPBadGateway(text=f"SSH terminal failed to start: {stderr.decode(errors='replace')[:500]}")
                try:
                    reader, writer = await asyncio.open_connection("127.0.0.1", port)
                    writer.close()
                    await writer.wait_closed()
                    main.LOGGER.info("SSH terminal ready for %s on local port %d", resource["name"], port)
                    return port
                except OSError:
                    await asyncio.sleep(0.05)
            await self._stop_locked(resource_id)
            raise web.HTTPGatewayTimeout(text="SSH terminal did not start in time")

    async def stop(self, resource_id: str) -> None:
        async with self._lock:
            await self._stop_locked(resource_id)

    async def _stop_locked(self, resource_id: str) -> None:
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

    async def close(self) -> None:
        async with self._lock:
            for resource_id in list(self._sessions):
                await self._stop_locked(resource_id)


TTYD = TTYDManager()


async def list_credentials(request: web.Request) -> web.Response:
    return web.json_response(await VAULT.list_public())


async def add_credential(request: web.Request) -> web.Response:
    try:
        payload = await request.json()
    except (json.JSONDecodeError, ValueError):
        raise web.HTTPBadRequest(text="Invalid JSON")
    item = await VAULT.add_private_key(str(payload.get("name", "")), str(payload.get("private_key", "")))
    return web.json_response(item, status=201)


async def generate_credential(request: web.Request) -> web.Response:
    try:
        payload = await request.json()
    except (json.JSONDecodeError, ValueError):
        raise web.HTTPBadRequest(text="Invalid JSON")
    item = await VAULT.generate_ed25519(str(payload.get("name", "")))
    return web.json_response(item, status=201)


async def delete_credential(request: web.Request) -> web.Response:
    await VAULT.delete(request.match_info["credential_id"])
    return web.Response(status=204)


async def _proxy_ttyd_websocket(request: web.Request, target: str) -> web.WebSocketResponse:
    if main.CLIENT is None:
        raise web.HTTPServiceUnavailable(text="Proxy client is not ready")
    protocols = [item.strip() for item in request.headers.get("Sec-WebSocket-Protocol", "").split(",") if item.strip()]
    browser_ws = web.WebSocketResponse(protocols=protocols)
    await browser_ws.prepare(request)
    ws_target = target.replace("http://", "ws://", 1)
    try:
        async with main.CLIENT.ws_connect(ws_target, protocols=protocols, timeout=20) as upstream_ws:
            async def browser_to_upstream() -> None:
                async for message in browser_ws:
                    if message.type == WSMsgType.TEXT:
                        await upstream_ws.send_str(message.data)
                    elif message.type == WSMsgType.BINARY:
                        await upstream_ws.send_bytes(message.data)
                    elif message.type in {WSMsgType.CLOSE, WSMsgType.CLOSED, WSMsgType.ERROR}:
                        break

            async def upstream_to_browser() -> None:
                async for message in upstream_ws:
                    if message.type == WSMsgType.TEXT:
                        await browser_ws.send_str(message.data)
                    elif message.type == WSMsgType.BINARY:
                        await browser_ws.send_bytes(message.data)
                    elif message.type in {WSMsgType.CLOSE, WSMsgType.CLOSED, WSMsgType.ERROR}:
                        break

            tasks = [asyncio.create_task(browser_to_upstream()), asyncio.create_task(upstream_to_browser())]
            done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
            for task in pending:
                task.cancel()
            await asyncio.gather(*pending, return_exceptions=True)
            for task in done:
                if task.exception():
                    raise task.exception()
    except (ClientError, asyncio.TimeoutError) as err:
        main.LOGGER.warning("SSH ttyd WebSocket bridge failed: %r", err)
    finally:
        if not browser_ws.closed:
            await browser_ws.close()
    return browser_ws


async def proxy_ssh_terminal(request: web.Request) -> web.StreamResponse:
    if main.CLIENT is None:
        raise web.HTTPServiceUnavailable(text="Proxy client is not ready")
    resource_id = request.match_info["resource_id"]
    tail = request.match_info.get("tail", "")
    resource = main.STORE.get(resource_id)
    if resource is None or resource.get("resource_type") != "ssh":
        raise web.HTTPNotFound(text="Unknown SSH resource")

    port = await TTYD.ensure(resource)
    path = f"/ssh/{resource_id}/" + tail.lstrip("/")
    target = f"http://127.0.0.1:{port}{path}"
    if request.query_string:
        target += "?" + request.query_string

    if request.headers.get("Upgrade", "").lower() == "websocket":
        return await _proxy_ttyd_websocket(request, target)

    headers = {
        key: value
        for key, value in request.headers.items()
        if key.lower() in {"accept", "accept-encoding", "accept-language", "cache-control", "content-type", "pragma", "range", "user-agent"}
    }
    body = await request.read() if request.can_read_body else None
    try:
        upstream = await main.CLIENT.request(
            request.method,
            target,
            headers=headers,
            data=body,
            allow_redirects=False,
            timeout=ClientTimeout(total=30, connect=5, sock_connect=5),
        )
        try:
            raw_body = await upstream.read()
            response_headers = main.copy_response_headers(upstream)
            return web.Response(
                status=upstream.status,
                reason=upstream.reason,
                headers=response_headers,
                body=b"" if request.method == "HEAD" else raw_body,
            )
        finally:
            upstream.release()
    except (ClientError, asyncio.TimeoutError) as err:
        raise web.HTTPBadGateway(text=f"Unable to reach SSH terminal: {err}") from err


async def probe_ssh_resource(resource: dict) -> dict:
    started = time.monotonic()
    try:
        reader, writer = await asyncio.wait_for(
            asyncio.open_connection(resource["ssh_host"], int(resource.get("ssh_port", 22))),
            timeout=3,
        )
        writer.close()
        await writer.wait_closed()
        return {"online": True, "status": "ssh", "latency_ms": round((time.monotonic() - started) * 1000)}
    except (OSError, asyncio.TimeoutError):
        return {"online": False, "status": None, "latency_ms": round((time.monotonic() - started) * 1000)}
