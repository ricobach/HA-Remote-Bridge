# HA Remote Bridge

HA Remote Bridge is a Home Assistant App for securely accessing selected LAN services through Home Assistant Ingress and Nabu Casa.

The project is App-only. Home Assistant handles remote authentication; HA Remote Bridge then connects from the App container to preconfigured local endpoints.

> **Current version:** 0.7.1  
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
- Prompt, reusable SSH key, or saved password authentication.
- Per-connection **Terminal type** setting with Current/automatic, `xterm-256color`, `xterm`, and `vt100` choices.
- The default Current/automatic option preserves the existing tmux-derived TERM behaviour. A compatibility override such as `xterm-256color` can be used for systems that do not understand `tmux-256color`, including some Synology shells.
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

## Typical examples

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

## Runtime and source layout

Since 0.6.0 the App starts one canonical runtime:

```text
run.sh
  -> runtime.py
```

Version 0.7.0 also removes release-numbered UI and SMB filenames from the active App tree. The code is now named by responsibility.

```text
app/
├── runtime.py
├── dashboard.py
├── dashboard_base.py
├── dashboard_health.py
├── dashboard_host_grouping.py
├── dashboard_address_bar.py
├── dashboard_host_discovery.py
├── dashboard_virtual_host.py
├── smb_service.py
├── smb_core.py
├── smb_diagnostics.py
├── smb_directory_parser.py
├── smb_file_viewer.py
├── smb_zip_browser.py
├── web_proxy_compat.py
├── rutos_compat.py
├── swagger_request_compat.py
├── virtual_host_support.py
└── ...
```

`dashboard.py` and `smb_service.py` are the canonical entry modules. They preserve the proven composition order while allowing the physical source files to have meaningful names instead of `ui_shell_vXX.py` and `smb_support_vXX.py`.

Historical version-numbered source remains available through Git history.

## Development

Home Assistant App slug:

```text
ha_remote_bridge
```

Development currently happens directly on `main`.
