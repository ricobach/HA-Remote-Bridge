# HA Remote Bridge

HA Remote Bridge is a Home Assistant App for securely accessing selected LAN services through Home Assistant Ingress and Nabu Casa.

The project is App-only. Home Assistant handles remote authentication; HA Remote Bridge then connects from the App container to preconfigured local endpoints.

> **Current version:** 0.5.9  
> **Status:** Experimental

## What it supports

### Web / HTTP / HTTPS

- Reverse proxy for configured HTTP and HTTPS endpoints.
- Redirect, root-path, SPA, Fetch/XHR, EventSource and WebSocket compatibility handling.
- Read-only endpoint address bar with Back, Forward and Reload controls.
- Optional TLS certificate verification.
- Per-connection **Virtual host / SNI** override. This allows a connection such as `https://192.168.140.3:8060` to be presented upstream as `www.example.com` while the address bar still shows the configured IP endpoint.
- Compatibility handling for complex applications including RutOS/Teltonika, OPNsense and Swagger/OpenAPI.
- Swagger/OpenAPI "Try it out" requests can be relayed through HA Remote Bridge to the configured API endpoint.

### SSH

- Browser SSH terminal through ttyd and OpenSSH.
- Persistent SSH sessions using tmux.
- Authentication modes:
  - prompt in terminal
  - reusable SSH key
  - saved password per connection
- Reusable key vault under `/data/ssh`.
- Known-host tracking with `StrictHostKeyChecking=accept-new`.

Saved passwords are kept separately from `resources.json` in App-private storage and are not returned to the browser/API.

### SMB

- SMB share and directory browser.
- Reusable SMB credentials or guest access.
- Clickable breadcrumbs and folder navigation.
- Inline file viewer with Previous/Next navigation.
- Image, PDF, text/code, audio and video previews.
- Inline ZIP browser with nested-folder navigation and bounded previews.

### VNC

- Browser-based noVNC sessions through Ingress.
- View-only mode.
- Keyboard focus helper and Ctrl-Alt-Del action.
- VNC traffic is restricted to configured resources.

### Discovery and host grouping

- Passive ESPHome mDNS discovery.
- Targeted single-host service discovery for Web, SSH, SMB and VNC.
- Expanded Docker-oriented Web probing, including common `8xxx` ports.
- Per-host **Rescan** action to find newly exposed services.
- Host/IP is the canonical grouping identity, with an optional friendly Group / Host name.
- Multiple services on one host collapse into one host card.
- Search, sorting, protocol filters and Online/Offline status.

## Architecture

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
      +--> HTTP / HTTPS / APIs
      +--> SSH
      +--> SMB
      +--> VNC
      +--> ESPHome
```

HA Remote Bridge publishes no separate LAN or Internet-facing App port.

## Install

1. In Home Assistant, go to **Settings > Apps > App store**.
2. Open the repositories menu.
3. Add:

   ```text
   https://github.com/ricobach/HA-Remote-Bridge
   ```

4. Install **HA Remote Bridge**.
5. Start the App.
6. Select **Open Web UI**.

The repository includes `repository.yaml`, so it can be added directly as a Home Assistant App repository.

## Typical examples

### Normal Web endpoint

```text
Name:       Proxmox
URL:        https://192.168.1.10:8006
Verify SSL: off
```

### Name-based virtual host / SNI

```text
Name:               Internal application
URL:                https://192.168.140.3:8060
Virtual host / SNI: www.example.com
```

The App connects to `192.168.140.3:8060` but sends `Host: www.example.com` and uses `www.example.com` for TLS SNI.

### Multiple services on one host

```text
Flamengo · 192.168.1.51
├── Web :3000
├── Web :8000
├── SSH :22
└── SMB :445
```

Use **Rescan** on the host card to look for additional services later.

## Security model

- Home Assistant Ingress is the external authentication boundary.
- The App panel is admin-only.
- Targets must be preconfigured; HA Remote Bridge is not an arbitrary/open proxy.
- Home Assistant authentication cookies and headers are not intentionally forwarded to LAN targets.
- HTTP credentials embedded directly in target URLs are rejected.
- SSH private keys and saved passwords are kept outside normal resource definitions with restrictive filesystem permissions.
- SMB passwords are stored in App-private storage and passed to Samba using protected credential files.
- VNC and SMB relays are constrained to configured resources.
- Companion-origin relays use server-side allowlists.

HA Remote Bridge is experimental. It should not be treated as the sole security boundary for highly sensitive systems.

## Repository layout

```text
HA-Remote-Bridge/
├── README.md
├── repository.yaml
├── archive/
│   └── legacy-docs/
└── ha_remote_bridge/
    ├── config.yaml
    ├── Dockerfile
    ├── run.sh
    ├── CHANGELOG.md
    ├── icon.png
    └── app/
```

### About the numbered runtime files

The current runtime is intentionally layered: `compat_runner_v33.py` imports earlier compatibility layers, and the latest UI similarly builds on previous `ui_shell_v*` modules. Those files may look historical, but many are still part of the active import graph and therefore should not be moved or deleted until the runtime is consolidated into a new canonical module.

## Development

Home Assistant App slug:

```text
ha_remote_bridge
```

Development currently happens directly on `main`.
