# HA Remote Bridge

HA Remote Bridge is a Home Assistant App for securely accessing selected local network resources through Home Assistant Ingress and Nabu Casa.

The project is App-only. The previous experimental HACS/custom integration has been removed; discovery, resource management, health checks, SSH, and VNC are all handled directly by the App.

> **Status:** Experimental

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
      +--> ESPHome web UI
      +--> Router / firewall / NAS
      +--> Local HTTP/HTTPS services
      +--> SSH terminals
      +--> VNC desktops
```

The local target does not need to be exposed directly to the Internet. Home Assistant authenticates the user and Ingress forwards the session internally to HA Remote Bridge.

## Current features

- Home Assistant Ingress with an admin-only panel.
- App-local dashboard styled to fit Home Assistant / ESPHome Device Builder.
- HTTP and HTTPS reverse proxying with redirect/path rewriting and WebSocket support.
- ESPHome mDNS discovery directly in the App, including a collapsible discovered-devices section.
- Resource grouping by host/name, allowing multiple Web, SSH, and VNC endpoints under one device card.
- Online/Offline reachability badges and filtering/search.
- Persistent session tabs with Back, Forward, Reload, and close controls.
- SSH terminals through ttyd/OpenSSH with reusable SSH key credentials.
- App-local SSH credential vault under `/data/ssh`; private key material is not returned by the API.
- Persistent SSH sessions using tmux so remote jobs can continue while the browser page is detached.
- VNC support through noVNC, including View Only mode, keyboard focus controls, Ctrl-Alt-Del, and Ingress-only WebSocket bridging.
- Optional TLS verification for self-signed local HTTPS resources.
- No published LAN or Internet service port.

## Install

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

The repository contains `repository.yaml`, so Home Assistant can use it directly as an App repository.

## Resource types

### Web / ESPHome

Examples:

```text
Kitchen ESPHome
http://192.168.1.51
```

```text
OPNsense
https://192.168.1.1
```

Disable **Verify SSL** only when the target uses a certificate the App cannot verify.

### SSH

SSH resources support:

- Session Name
- Group / Host
- Host / IP
- Port
- Username
- Reusable SSH key credentials

Generated or imported SSH keys are stored once in the App-local credential vault and can be reused by multiple SSH resources.

### VNC

VNC resources support:

- Session Name
- Group / Host
- Host / IP
- Port
- Optional View Only mode

VNC passwords are requested interactively by noVNC when needed and are not stored by HA Remote Bridge.

## ESPHome discovery

The App listens for ESPHome mDNS advertisements and shows compatible devices under **Discovered ESPHome devices**. Devices can be added directly from the dashboard; no separate Home Assistant integration is required.

## Security model

- External authentication is handled by Home Assistant Ingress.
- The App panel is restricted to Home Assistant administrators.
- HA authentication headers/cookies are not forwarded to proxied LAN targets.
- Credentials embedded directly in HTTP/HTTPS target URLs are rejected.
- SSH private keys are stored separately from normal resource definitions with restrictive permissions.
- VNC WebSockets are bound to preconfigured VNC targets only; HA Remote Bridge does not provide an arbitrary TCP proxy.
- Companion-origin HTTP proxying is restricted to server-side allowlists.

HA Remote Bridge is still experimental. Do not use it as the sole security boundary for highly sensitive systems.

## Repository layout

```text
HA-Remote-Bridge/
├── repository.yaml
├── README.md
└── ha_remote_bridge/
    ├── config.yaml
    ├── Dockerfile
    ├── run.sh
    ├── icon.png
    ├── icon.svg
    ├── CHANGELOG.md
    └── app/
```

## Development

Home Assistant App slug:

```text
ha_remote_bridge
```

Development currently happens directly on `main`.
