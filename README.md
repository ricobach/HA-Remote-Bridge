# HA Remote Bridge

HA Remote Bridge is a Home Assistant App for securely accessing selected LAN services through Home Assistant Ingress and Nabu Casa.

Home Assistant handles remote authentication; HA Remote Bridge connects from the App container to preconfigured local endpoints.

> **Current version:** 0.6.0  
> **Status:** Experimental

## What it supports

### Web / HTTP / HTTPS

- Reverse proxy for configured HTTP and HTTPS endpoints.
- Redirect, root-path, SPA, Fetch/XHR, EventSource and WebSocket compatibility handling.
- Read-only endpoint address bar with Back, Forward and Reload controls.
- Optional TLS certificate verification.
- Per-connection **Virtual host / SNI** override.
- Compatibility handling for RutOS/Teltonika, OPNsense and Swagger/OpenAPI.
- Swagger/OpenAPI "Try it out" requests can be relayed through HA Remote Bridge.

### SSH

- Browser SSH terminal through ttyd and OpenSSH.
- Persistent tmux-backed sessions.
- Prompt, reusable SSH key, or saved-password authentication.
- App-local key/password storage under `/data/ssh`.

### SMB

- Share and directory browser.
- Reusable credentials or guest access.
- Clickable breadcrumbs and file navigation.
- Inline image, PDF, text/code, audio and video previews.
- Inline ZIP browsing with bounded previews.

### VNC

- Browser-based noVNC sessions through Ingress.
- View-only mode, keyboard focus helper and Ctrl-Alt-Del.

### Discovery and grouping

- Passive ESPHome mDNS discovery.
- Targeted single-host Web/SSH/SMB/VNC discovery.
- Docker-oriented Web probing including common `8xxx` ports.
- Per-host **Rescan** action.
- Host/IP-based grouping with friendly Group / Host labels.
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
HA Remote Bridge
      |
      +--> HTTP / HTTPS / APIs
      +--> SSH
      +--> SMB
      +--> VNC
      +--> ESPHome
```

HA Remote Bridge publishes no separate LAN or Internet-facing App port.

## Install

1. Go to **Settings > Apps > App store** in Home Assistant.
2. Add this App repository:

   ```text
   https://github.com/ricobach/HA-Remote-Bridge
   ```

3. Install and start **HA Remote Bridge**.
4. Select **Open Web UI**.

## Examples

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

The App connects to `192.168.140.3:8060` while presenting `www.example.com` in the HTTP Host header and TLS SNI.

### Multiple services on one host

```text
Flamengo · 192.168.1.51
├── Web :3000
├── Web :8000
├── SSH :22
└── SMB :445
```

## Security model

- Home Assistant Ingress is the external authentication boundary.
- The App panel is admin-only.
- Targets must be preconfigured; HA Remote Bridge is not an arbitrary/open proxy.
- Home Assistant authentication cookies and headers are not intentionally forwarded to LAN targets.
- Credentials embedded directly in HTTP/HTTPS target URLs are rejected.
- SSH and SMB secrets are kept outside normal resource definitions with restrictive filesystem permissions.
- VNC, SMB and companion relays are constrained to configured/approved destinations.

HA Remote Bridge is experimental and should not be treated as the sole security boundary for highly sensitive systems.

## Runtime architecture

Version **0.6.0** replaces the historical `compat_runner_vXX.py` startup inheritance chain with one canonical entry point:

```text
run.sh
  └── runtime.py
      ├── Web proxy / ESPHome compatibility
      ├── RutOS compatibility
      ├── SSH password authentication
      ├── host discovery / rescan
      ├── same-origin Web compatibility
      ├── OpenAPI / Swagger compatibility
      └── virtual Host / SNI support
```

Feature modules are installed explicitly by responsibility. Release numbers are no longer used as runtime composition names.

The UI is still composed from the existing `ui_shell_v*` layers. Consolidating those into a canonical dashboard module can be done separately without coupling it to runtime startup.

## Repository layout

```text
HA-Remote-Bridge/
├── README.md
├── repository.yaml
├── archive/
│   ├── README.md
│   └── legacy-docs/
└── ha_remote_bridge/
    ├── config.yaml
    ├── Dockerfile
    ├── run.sh
    ├── CHANGELOG.md
    └── app/
        ├── runtime.py
        ├── main.py
        ├── launcher.py
        ├── *_support.py
        └── *_compat.py
```

Home Assistant App slug: `ha_remote_bridge`.
