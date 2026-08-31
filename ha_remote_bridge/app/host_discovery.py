"""Targeted single-host service discovery for HA Remote Bridge.

This intentionally is not a subnet/network scanner. A user supplies one host
and the App probes a bounded list of common HA Remote Bridge service ports,
plus up to 20 explicitly requested extra ports. Results are protocol-probed
before being offered to the dashboard.
"""

from __future__ import annotations

import asyncio
import ipaddress
import re
import time
from urllib.parse import urlparse

from aiohttp import ClientError, ClientSession, ClientTimeout, web

import launcher
import main

DEFAULT_WEB_PORTS: tuple[tuple[int, str], ...] = (
    (80, "http"),
    (443, "https"),
    (3000, "http"),
    (5000, "http"),
    (5001, "https"),
    (8000, "http"),
    (8008, "http"),
    (8080, "http"),
    (8081, "http"),
    (8123, "http"),
    (8443, "https"),
    (8888, "http"),
    (9000, "http"),
    (9090, "http"),
    (9443, "https"),
)
SSH_PORTS = {22, 2222}
SMB_PORTS = {139, 445}
VNC_PORTS = set(range(5900, 5906))
MAX_EXTRA_PORTS = 20
MAX_TOTAL_PORTS = 48

_HOST_RE = re.compile(r"^[A-Za-z0-9_.-]+$")
_TITLE_RE = re.compile(r"<title[^>]*>(.*?)</title>", re.I | re.S)
_INSTALLED = False
_ORIGINAL_CREATE_APP = None


def _clean_host(value: object) -> str:
    host = str(value or "").strip()
    if host.startswith("[") and host.endswith("]"):
        host = host[1:-1]
    if not host or len(host) > 255:
        raise web.HTTPBadRequest(text="A hostname or IP address is required")
    if any(ch in host for ch in "/\\@?#\r\n\t ") or "://" in host:
        raise web.HTTPBadRequest(text="Enter only a hostname or IP address, not a URL")
    try:
        ipaddress.ip_address(host)
    except ValueError:
        if not _HOST_RE.fullmatch(host):
            raise web.HTTPBadRequest(text="Invalid hostname")
    return host


def _extra_ports(value: object) -> list[int]:
    if value in (None, ""):
        return []
    if not isinstance(value, list):
        raise web.HTTPBadRequest(text="extra_ports must be a list")
    if len(value) > MAX_EXTRA_PORTS:
        raise web.HTTPBadRequest(text=f"At most {MAX_EXTRA_PORTS} extra ports may be scanned")
    ports: list[int] = []
    for item in value:
        try:
            port = int(item)
        except (TypeError, ValueError):
            raise web.HTTPBadRequest(text="Extra ports must be numeric")
        if not 1 <= port <= 65535:
            raise web.HTTPBadRequest(text="Ports must be between 1 and 65535")
        if port not in ports:
            ports.append(port)
    return ports


def _host_for_url(host: str) -> str:
    return f"[{host}]" if ":" in host and not host.startswith("[") else host


def _normalized_host(host: object) -> str:
    return str(host or "").strip().strip("[]").lower().rstrip(".")


def _resource_matches(kind: str, host: str, port: int, scheme: str | None = None) -> bool:
    wanted_host = _normalized_host(host)
    for resource in main.STORE.resources:
        rkind = str(resource.get("resource_type", "")).lower()
        if kind == "ssh" and rkind == "ssh":
            if _normalized_host(resource.get("ssh_host")) == wanted_host and int(resource.get("ssh_port", 22)) == port:
                return True
        elif kind == "smb" and rkind == "smb":
            if _normalized_host(resource.get("smb_host")) == wanted_host and int(resource.get("smb_port", 445)) == port:
                return True
        elif kind == "vnc" and rkind == "vnc":
            if _normalized_host(resource.get("vnc_host")) == wanted_host and int(resource.get("vnc_port", 5900)) == port:
                return True
        elif kind == "web" and rkind not in {"ssh", "smb", "vnc"}:
            try:
                parsed = urlparse(str(resource.get("url", "")))
                rport = parsed.port or (443 if parsed.scheme == "https" else 80)
                if (
                    _normalized_host(parsed.hostname) == wanted_host
                    and rport == port
                    and (scheme is None or parsed.scheme == scheme)
                ):
                    return True
            except (TypeError, ValueError):
                pass
    return False


def _suggested_ssh_user(host: str) -> str | None:
    wanted = _normalized_host(host)
    for resource in main.STORE.resources:
        if resource.get("resource_type") == "ssh" and _normalized_host(resource.get("ssh_host")) == wanted:
            user = str(resource.get("ssh_user", "")).strip()
            if user:
                return user
    return None


async def _open_tcp(host: str, port: int, timeout: float = 1.1):
    try:
        return await asyncio.wait_for(asyncio.open_connection(host, port), timeout=timeout)
    except (asyncio.TimeoutError, OSError):
        return None


async def _read_banner(host: str, port: int) -> str:
    conn = await _open_tcp(host, port)
    if conn is None:
        return ""
    reader, writer = conn
    try:
        try:
            data = await asyncio.wait_for(reader.read(256), timeout=0.55)
        except asyncio.TimeoutError:
            return ""
        return data.decode("utf-8", errors="replace").strip()
    finally:
        writer.close()
        try:
            await writer.wait_closed()
        except OSError:
            pass


async def _tcp_is_open(host: str, port: int) -> bool:
    conn = await _open_tcp(host, port)
    if conn is None:
        return False
    _, writer = conn
    writer.close()
    try:
        await writer.wait_closed()
    except OSError:
        pass
    return True


async def _probe_smb(host: str, port: int) -> tuple[bool, str, str]:
    if not await _tcp_is_open(host, port):
        return False, "", ""
    try:
        proc = await asyncio.create_subprocess_exec(
            "smbclient",
            "-g",
            "-N",
            "-m", "SMB3",
            "-p", str(port),
            "-L", f"//{host}",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        try:
            out, err = await asyncio.wait_for(proc.communicate(), timeout=3.0)
        except asyncio.TimeoutError:
            proc.kill()
            await proc.wait()
            return True, "probable", "TCP service reachable on SMB port"
        text = (out + err).decode("utf-8", errors="replace")
        upper = text.upper()
        if "NT_STATUS" in upper or "DISK|" in upper or "IPC|" in upper or "SMB" in upper:
            detail = "SMB server responded"
            if "NT_STATUS_LOGON_FAILURE" in upper or "NT_STATUS_ACCESS_DENIED" in upper:
                detail += " · authentication required"
            return True, "confirmed", detail
    except (OSError, asyncio.SubprocessError):
        pass
    return True, "probable", "TCP service reachable on SMB port"


async def _probe_web(session: ClientSession, host: str, port: int, preferred: str) -> dict | None:
    schemes = [preferred, "https" if preferred == "http" else "http"]
    url_host = _host_for_url(host)
    for scheme in schemes:
        default_port = 443 if scheme == "https" else 80
        authority = url_host if port == default_port else f"{url_host}:{port}"
        url = f"{scheme}://{authority}/"
        try:
            async with session.get(
                url,
                allow_redirects=False,
                ssl=False,
                headers={"User-Agent": "HA-Remote-Bridge-Discovery/1", "Accept": "text/html,*/*;q=0.2"},
            ) as response:
                body = await response.content.read(4096)
                text = body.decode(response.charset or "utf-8", errors="replace")
                match = _TITLE_RE.search(text)
                title = re.sub(r"\s+", " ", match.group(1)).strip()[:100] if match else ""
                server = str(response.headers.get("Server", "")).strip()[:100]
                detail_parts = [f"HTTP {response.status}"]
                if title:
                    detail_parts.append(title)
                elif server:
                    detail_parts.append(server)
                return {
                    "kind": "web",
                    "service": "HTTPS" if scheme == "https" else "HTTP",
                    "scheme": scheme,
                    "port": port,
                    "confidence": "confirmed",
                    "detail": " · ".join(detail_parts),
                    "url": url,
                    "already_configured": _resource_matches("web", host, port, scheme),
                }
        except (ClientError, asyncio.TimeoutError, OSError, UnicodeError):
            continue
    return None


async def _probe_port(session: ClientSession, host: str, port: int, preferred_web: str) -> dict | None:
    # SSH and RFB both send a clear server banner immediately, including on
    # non-standard ports supplied through the optional extra-port field.
    banner = await _read_banner(host, port)
    if banner.startswith("SSH-"):
        first = banner.splitlines()[0][:120]
        return {
            "kind": "ssh",
            "service": "SSH",
            "port": port,
            "confidence": "confirmed",
            "detail": first,
            "already_configured": _resource_matches("ssh", host, port),
            "suggested_username": _suggested_ssh_user(host) or "root",
        }
    if banner.startswith("RFB "):
        first = banner.splitlines()[0][:40]
        return {
            "kind": "vnc",
            "service": "VNC",
            "port": port,
            "confidence": "confirmed",
            "detail": first,
            "already_configured": _resource_matches("vnc", host, port),
        }

    if port in SMB_PORTS:
        found, confidence, detail = await _probe_smb(host, port)
        if found:
            return {
                "kind": "smb",
                "service": "SMB",
                "port": port,
                "confidence": confidence,
                "detail": detail,
                "already_configured": _resource_matches("smb", host, port),
            }

    # Avoid an extra HTTP timeout when the port is definitely closed.
    if not await _tcp_is_open(host, port):
        return None
    return await _probe_web(session, host, port, preferred_web)


async def scan_host(request: web.Request) -> web.Response:
    try:
        payload = await request.json()
    except ValueError:
        raise web.HTTPBadRequest(text="Invalid JSON")

    host = _clean_host(payload.get("host"))
    extras = _extra_ports(payload.get("extra_ports"))

    preferred: dict[int, str] = {port: scheme for port, scheme in DEFAULT_WEB_PORTS}
    ports = set(preferred) | SSH_PORTS | SMB_PORTS | VNC_PORTS | set(extras)
    if len(ports) > MAX_TOTAL_PORTS:
        raise web.HTTPBadRequest(text=f"At most {MAX_TOTAL_PORTS} ports may be probed in one scan")
    for port in ports:
        preferred.setdefault(port, "https" if port in {443, 8443, 9443, 5001} else "http")

    started = time.monotonic()
    timeout = ClientTimeout(total=2.5, connect=1.25, sock_connect=1.25, sock_read=1.25)
    connector_limit = min(16, max(4, len(ports)))
    async with ClientSession(timeout=timeout, connector=None) as session:
        semaphore = asyncio.Semaphore(connector_limit)

        async def limited(port: int):
            async with semaphore:
                return await _probe_port(session, host, port, preferred[port])

        raw = await asyncio.gather(*(limited(port) for port in sorted(ports)))

    results = [item for item in raw if item is not None]
    order = {"web": 0, "ssh": 1, "smb": 2, "vnc": 3}
    results.sort(key=lambda item: (order.get(item["kind"], 9), item["port"]))

    main.LOGGER.info(
        "Host discovery for %s probed %d port(s), found %d supported service(s) in %d ms",
        host,
        len(ports),
        len(results),
        round((time.monotonic() - started) * 1000),
    )
    return web.json_response(
        {
            "host": host,
            "scanned_ports": len(ports),
            "duration_ms": round((time.monotonic() - started) * 1000),
            "services": results,
        }
    )


def install() -> None:
    """Add the discovery API to the existing App factory exactly once."""
    global _INSTALLED, _ORIGINAL_CREATE_APP
    if _INSTALLED:
        return
    _INSTALLED = True
    _ORIGINAL_CREATE_APP = launcher.create_app

    def create_app() -> web.Application:
        app = _ORIGINAL_CREATE_APP()
        app.router.add_post("/api/discovery/host", scan_host)
        return app

    launcher.create_app = create_app
