# HA Remote Bridge

HA Remote Bridge provides secure remote access to selected local network resources through Home Assistant.

The project now contains two components:

1. **HA Remote Bridge App (recommended for browser access)** — a Home Assistant App/add-on with Ingress, a resource manager UI, HTTP/HTTPS reverse proxying and WebSocket bridging.
2. **HA Remote Bridge HACS integration** — an experimental custom integration for Home Assistant-native configuration, entities and future device discovery.

> **Status:** Experimental `0.1.0` development release.

## Goal

```text
Remote browser
      |
      v
Home Assistant / Nabu Casa
      |
      v
Home Assistant Ingress
      |
      v
HA Remote Bridge App
      |
      +--> ESPHome web UI
      +--> Router / switch / NAS
      +--> Camera / local web service
      +--> SSH terminal (planned)
```

The local device does not need to be exposed directly to the Internet. Home Assistant authenticates the user and Ingress forwards the request internally to HA Remote Bridge.

## Home Assistant App / add-on

The App is the recommended way to use HA Remote Bridge for browser-based remote access.

### Current App features

- Home Assistant Ingress.
- Browser-friendly resource launcher.
- Add/delete local HTTP and HTTPS targets from the App UI.
- Persistent configuration in the App `/data` volume.
- HTTP method forwarding.
- Redirect rewriting.
- Best-effort HTML and CSS path rewriting.
- Browser shim for root-relative `fetch`, XMLHttpRequest and WebSocket URLs.
- WebSocket bridging.
- Optional TLS verification for self-signed local HTTPS resources.
- No published LAN or Internet port.
- App panel restricted to Home Assistant administrators in this release.

### Install the App

In Home Assistant:

1. Go to **Settings > Apps > App store**.
2. Open the repositories menu.
3. Add:

   ```text
   https://github.com/ricobach/HA-Remote-Bridge
   ```

4. Install **HA Remote Bridge**.
5. Start the App.
6. Select **Open Web UI**.

The repository contains the required `repository.yaml`, so Home Assistant can use the same GitHub repository as an App repository.

### Add a resource

Examples:

```text
Kitchen ESPHome
http://192.168.1.51
```

```text
Proxmox
https://192.168.1.10:8006
```

Disable **Verify SSL** only when the local HTTPS resource uses a certificate that cannot be verified by the App.

Select **Open** beside a resource to access it through the current Home Assistant Ingress session.

## HACS integration

The HACS integration remains in the repository for Home Assistant-native configuration and future discovery/management features.

### Install with HACS

1. Open HACS.
2. Add this repository as a custom repository.
3. Select **Integration** as the repository type.
4. Install **HA Remote Bridge**.
5. Restart Home Assistant.
6. Go to **Settings > Devices & services > Add integration**.
7. Search for **HA Remote Bridge**.

The current HACS integration exposes an authenticated `/api/ha_remote_bridge/...` proxy proof of concept and status entities. For interactive browser access, use the Ingress App instead.

## Architecture

```text
Home Assistant frontend
        |
        | authenticated Ingress
        v
+-------------------------------+
| HA Remote Bridge App          |
|                               |
| Resource manager              |
| HTTP/HTTPS reverse proxy      |
| Path/redirect rewriting       |
| WebSocket bridge              |
+---------------+---------------+
                |
                | local network
        +-------+--------+---------+
        |                |         |
        v                v         v
     ESPHome          Proxmox    Router
```

The App listens internally on port `8099`, the Home Assistant Ingress default. No host port is published.

## Security model

- External authentication is handled by Home Assistant Ingress.
- The App panel is administrator-only in `0.1.0`.
- The App rejects direct requests that are not delivered by the Home Assistant Ingress proxy (localhost is retained only for container-local diagnostics).
- HA Remote Bridge does not publish a TCP port to the LAN or Internet.
- Incoming Home Assistant `Authorization` and `Cookie` headers are not forwarded to local resources.
- Credentials embedded directly in target URLs are rejected.

HA Remote Bridge is still experimental. Do not use this first release as the sole security boundary for highly sensitive administrative systems.

## Compatibility notes

Simple local web interfaces should work directly. HA Remote Bridge rewrites common root-relative paths and includes a browser-side compatibility shim for common API and WebSocket calls.

Some applications may still fail when they:

- hard-code absolute external origins in unusual ways;
- require complex cookie authentication;
- use browser APIs not yet rewritten by HA Remote Bridge;
- intentionally prevent reverse proxying or framing;
- make assumptions that the application is hosted at `/`.

These compatibility cases will be improved incrementally.

## Roadmap

### Phase 1 — HACS integration

- [x] HACS repository structure
- [x] Config flow
- [x] HTTP/HTTPS target configuration
- [x] Authenticated API proxy proof of concept
- [x] Status entity
- [ ] Options/reconfigure flow
- [ ] Health checking
- [ ] ESPHome discovery
- [ ] App/integration configuration synchronization

### Phase 2 — Home Assistant App / add-on

- [x] App repository structure
- [x] Home Assistant Ingress
- [x] Browser resource launcher
- [x] Persistent resource manager
- [x] HTTP/HTTPS reverse proxy
- [x] Redirect/path rewriting
- [x] WebSocket proxying
- [ ] Edit existing resources
- [ ] Resource health status
- [ ] Improved cookie isolation/authentication support
- [ ] Per-resource access controls

### Phase 3 — Remote terminal

- [ ] Browser SSH terminal
- [ ] SSH key management
- [ ] Password/key authentication options
- [ ] Session timeout and cleanup
- [ ] Device-aware SSH targets

### Later

- [ ] VNC
- [ ] RDP
- [ ] Additional TCP-based local services

## Repository layout

```text
HA-Remote-Bridge/
├── repository.yaml
├── ha_remote_bridge/
│   ├── config.yaml
│   ├── Dockerfile
│   ├── run.sh
│   ├── README.md
│   ├── DOCS.md
│   ├── CHANGELOG.md
│   └── app/
│       └── main.py
├── hacs.json
└── custom_components/
    └── ha_remote_bridge/
```

## Development

Home Assistant App slug:

```text
ha_remote_bridge
```

HACS integration domain:

```text
ha_remote_bridge
```

The project is currently developed directly on `main`.
