# HA Remote Bridge

HA Remote Bridge is an experimental Home Assistant project for accessing selected local network resources through your existing Home Assistant connection.

> **Status:** Early proof of concept. Version `0.1.0` implements the HACS/custom-integration side of the project. It is not yet a full Home Assistant Ingress replacement.

## Goal

The long-term goal is to make local resources available remotely without exposing each device directly to the Internet.

```text
Remote browser
      |
      v
Home Assistant / Nabu Casa
      |
      v
HA Remote Bridge
      |
      +--> ESPHome web UI
      +--> Router / switch / NAS
      +--> Camera / local web service
      +--> SSH terminal (planned)
```

## Current MVP

The first HACS draft provides:

- Home Assistant UI configuration through a config flow.
- One HTTP/HTTPS target per config entry.
- An authenticated Home Assistant API proxy endpoint.
- HTTP methods including GET, POST, PUT, PATCH and DELETE.
- Redirect rewriting for redirects back to the configured target.
- Best-effort rewriting of root-relative HTML links.
- Optional SSL certificate verification for local HTTPS services.
- An entity for each configured bridge with its proxy path in the `bridge_path` attribute.
- Administrator-only proxy access in the current MVP.

## Important limitation of the HACS-only MVP

Home Assistant API endpoints require authenticated API requests. A normal browser navigation to `/api/ha_remote_bridge/...` does not automatically attach the Home Assistant frontend access token.

That means this first version proves the proxy backend and configuration model, but **does not yet provide the final one-click browser experience** for arbitrary local web interfaces.

The intended next architectural step is a companion Home Assistant app/add-on using **Home Assistant Ingress**. The HACS integration can then provide discovery, configuration and entities while the app/add-on provides browser-friendly proxying, WebSockets and later SSH.

## Installation with HACS

1. Open HACS.
2. Add this repository as a custom repository.
3. Select **Integration** as the repository type.
4. Install **HA Remote Bridge**.
5. Restart Home Assistant.
6. Go to **Settings > Devices & services > Add integration**.
7. Search for **HA Remote Bridge**.

Repository:

```text
https://github.com/ricobach/HA-Remote-Bridge
```

## Add a resource

Example:

```text
Name: Kitchen ESPHome
Local URL: http://192.168.1.51
Verify SSL certificate: Yes
```

For a self-signed local HTTPS service you can disable certificate verification.

After setup, HA Remote Bridge creates a status entity. Its `bridge_path` attribute contains a path similar to:

```text
/api/ha_remote_bridge/01ABCDEF1234567890/
```

## Testing the MVP

Use a Home Assistant long-lived access token to test the proxy endpoint:

```bash
curl \
  -H "Authorization: Bearer YOUR_HOME_ASSISTANT_TOKEN" \
  "https://YOUR_HOME_ASSISTANT_URL/api/ha_remote_bridge/CONFIG_ENTRY_ID/"
```

Requests are forwarded from Home Assistant to the configured local URL.

## Current security model

- The target must first be configured as a Home Assistant config entry.
- The proxy endpoint requires Home Assistant authentication.
- The proxy additionally requires the authenticated Home Assistant user to be an administrator.
- The remote target is never intentionally exposed as a separate Internet-facing listener by this integration.

This project is experimental. Do not use it as the only security boundary for sensitive administrative interfaces yet.

## Roadmap

### Phase 1 — HACS integration

- [x] HACS repository structure
- [x] Config flow
- [x] HTTP/HTTPS target configuration
- [x] Authenticated proxy endpoint
- [x] Redirect rewriting
- [x] Basic root-relative HTML rewriting
- [x] Status entity
- [ ] Options/reconfigure flow
- [ ] Health checking
- [ ] ESPHome discovery

### Phase 2 — Home Assistant app/add-on

- [ ] Home Assistant Ingress
- [ ] Browser-friendly resource launcher
- [ ] WebSocket proxying
- [ ] Improved cookie/header/path rewriting
- [ ] Per-resource access controls

### Phase 3 — Remote terminal

- [ ] Browser SSH using ttyd or equivalent
- [ ] SSH key management
- [ ] Session timeout and cleanup
- [ ] Device-aware SSH targets

### Later

- [ ] VNC
- [ ] RDP
- [ ] Additional TCP-based local services

## Development

Integration domain:

```text
ha_remote_bridge
```

Source directory:

```text
custom_components/ha_remote_bridge/
```

The project is currently developed directly on `main`.
