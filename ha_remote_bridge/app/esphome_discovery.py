"""Passive ESPHome web-server discovery for HA Remote Bridge.

The App listens for ESPHome's mDNS services instead of scanning the LAN.
`_esphomelib._tcp` identifies ESPHome nodes using the native API, while
`_http._tcp` supplies the web-server port. Current ESPHome firmware without
the native API also publishes identity TXT records on `_http._tcp`.
"""

from __future__ import annotations

import ipaddress
import threading
import time
from urllib.parse import urlparse

from zeroconf import ServiceBrowser, ServiceStateChange, Zeroconf

ESPHOME_SERVICE = "_esphomelib._tcp.local."
HTTP_SERVICE = "_http._tcp.local."


def _decode_properties(properties: dict[bytes, bytes | None]) -> dict[str, str]:
    decoded: dict[str, str] = {}
    for key, value in properties.items():
        key_text = key.decode("utf-8", errors="replace")
        decoded[key_text] = "" if value is None else value.decode("utf-8", errors="replace")
    return decoded


def _service_label(name: str, service_type: str) -> str:
    suffix = "." + service_type
    return name[: -len(suffix)] if name.endswith(suffix) else name.split(".", 1)[0]


def _host_for_url(server: str, addresses: list[str]) -> str:
    """Prefer IPv4, then IPv6, then the mDNS hostname."""
    for address in addresses:
        try:
            if ipaddress.ip_address(address.split("%", 1)[0]).version == 4:
                return address
        except ValueError:
            continue

    for address in addresses:
        try:
            if ipaddress.ip_address(address.split("%", 1)[0]).version == 6:
                return f"[{address}]"
        except ValueError:
            continue

    return server.rstrip(".")


class ESPHomeDiscovery:
    """Keep a live passive mDNS view of ESPHome web servers."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._zc: Zeroconf | None = None
        self._browser: ServiceBrowser | None = None
        self._services: dict[tuple[str, str], dict] = {}

    def start(self) -> None:
        if self._zc is not None:
            return
        self._zc = Zeroconf()
        self._browser = ServiceBrowser(
            self._zc,
            [ESPHOME_SERVICE, HTTP_SERVICE],
            handlers=[self._on_service_state_change],
        )

    def close(self) -> None:
        browser, zc = self._browser, self._zc
        self._browser = None
        self._zc = None
        if browser is not None:
            browser.cancel()
        if zc is not None:
            zc.close()
        with self._lock:
            self._services.clear()

    def _on_service_state_change(
        self,
        zeroconf: Zeroconf,
        service_type: str,
        name: str,
        state_change: ServiceStateChange,
    ) -> None:
        key = (service_type, name)
        if state_change is ServiceStateChange.Removed:
            with self._lock:
                self._services.pop(key, None)
            return

        info = zeroconf.get_service_info(service_type, name, timeout=1500)
        if info is None or not info.server:
            return

        record = {
            "service_type": service_type,
            "service_name": name,
            "label": _service_label(name, service_type),
            "server": info.server.rstrip(".").lower(),
            "port": int(info.port),
            "addresses": info.parsed_scoped_addresses(),
            "properties": _decode_properties(info.properties),
            "last_seen": time.time(),
        }
        with self._lock:
            self._services[key] = record

    def snapshot(self, configured_resources: list[dict]) -> list[dict]:
        """Return discovered ESPHome nodes with a confirmed HTTP service."""
        with self._lock:
            services = list(self._services.values())

        grouped: dict[str, dict] = {}
        for record in services:
            group = grouped.setdefault(
                record["server"],
                {"api": [], "http": []},
            )
            if record["service_type"] == ESPHOME_SERVICE:
                group["api"].append(record)
            elif record["service_type"] == HTTP_SERVICE:
                group["http"].append(record)

        configured_hosts: set[str] = set()
        configured_urls: set[tuple[str, int]] = set()
        for resource in configured_resources:
            parsed = urlparse(resource.get("url", ""))
            if parsed.hostname:
                host = parsed.hostname.lower().rstrip(".")
                configured_hosts.add(host)
                configured_urls.add((host, parsed.port or (443 if parsed.scheme == "https" else 80)))

        discovered: list[dict] = []
        for server, group in grouped.items():
            http_records = group["http"]
            if not http_records:
                continue

            api_records = group["api"]
            # Native API mDNS is definitive ESPHome identity. For nodes without
            # the API, current ESPHome publishes MAC/config_hash identity on HTTP.
            identity_http = [
                item
                for item in http_records
                if item["properties"].get("mac")
                and item["properties"].get("config_hash")
            ]
            if not api_records and not identity_http:
                continue

            http = max(http_records, key=lambda item: item["last_seen"])
            identity = max(api_records or identity_http, key=lambda item: item["last_seen"])
            addresses = list(dict.fromkeys(http["addresses"] + identity["addresses"]))
            url_host = _host_for_url(server, addresses)
            port = int(http["port"] or 80)
            port_suffix = "" if port == 80 else f":{port}"
            url = f"http://{url_host}{port_suffix}"

            props = identity["properties"]
            friendly_name = props.get("friendly_name") or identity["label"] or server.split(".", 1)[0]
            candidate_hosts = {server}
            for address in addresses:
                candidate_hosts.add(address.split("%", 1)[0].lower())

            already_configured = any(
                (host, port) in configured_urls or host in configured_hosts
                for host in candidate_hosts
            )
            if already_configured:
                continue

            discovered.append(
                {
                    "id": props.get("mac") or server,
                    "name": friendly_name,
                    "hostname": server,
                    "addresses": addresses,
                    "port": port,
                    "url": url,
                    "version": props.get("version", ""),
                    "mac": props.get("mac", ""),
                    "source": "mdns",
                }
            )

        discovered.sort(key=lambda item: item["name"].casefold())
        return discovered
