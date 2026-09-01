"""Expanded single-host discovery defaults for Docker-heavy hosts.

The original host discovery remains intentionally single-host only. This layer
adds a wider set of common 8xxx Web ports while keeping the scan bounded and
retaining room for the existing 20 user-supplied extra ports.
"""

import host_discovery as discovery

_EXTRA_8XXX_WEB_PORTS = (
    (8001, "http"),
    (8002, "http"),
    (8003, "http"),
    (8004, "http"),
    (8005, "http"),
    (8006, "http"),
    (8009, "http"),
    (8010, "http"),
    (8020, "http"),
    (8040, "http"),
    (8050, "http"),
    (8060, "http"),
    (8070, "http"),
    (8082, "http"),
    (8083, "http"),
    (8088, "http"),
    (8090, "http"),
    (8181, "http"),
    (8200, "http"),
    (8280, "http"),
    (8384, "http"),
    (8880, "http"),
    (8989, "http"),
)


def install() -> None:
    """Expand discovery defaults before the aiohttp app is created."""
    existing = {port: scheme for port, scheme in discovery.DEFAULT_WEB_PORTS}
    for port, scheme in _EXTRA_8XXX_WEB_PORTS:
        existing.setdefault(port, scheme)
    discovery.DEFAULT_WEB_PORTS = tuple(sorted(existing.items()))

    # Base/default probes now total 48 ports. Keep enough headroom for the
    # already-supported 20 explicitly requested extra ports.
    discovery.MAX_TOTAL_PORTS = 68
