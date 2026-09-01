# Changelog

This changelog keeps major milestones and user-visible changes. Fine-grained development history remains available in Git.

## 0.7.x — Functional source naming

### 0.7.0
- Replaced active `ui_shell_vXX.py` filenames with responsibility-based `dashboard_*` modules and a canonical `dashboard.py` entry point.
- Replaced active `smb_support_vXX.py` filenames with responsibility-based SMB modules and a canonical `smb_service.py` entry point.
- Renamed the generic `compat_runner.py` Web/ESPHome compatibility module to `web_proxy_compat.py`.
- Preserved the existing UI and SMB implementation byte-for-byte during the physical rename; canonical loaders provide in-memory legacy aliases only while composing the proven layers.
- No release-numbered runner, UI-shell or SMB-support filenames remain in the active App tree.

## 0.6.x — Runtime consolidation

### 0.6.0
- Replaced the version-numbered `compat_runner_vXX.py` startup chain with one canonical `runtime.py` entry point.
- Runtime features are now composed explicitly by responsibility instead of release number.
- Preserved the current Web, SSH, VNC, SMB, discovery, RutOS, Swagger/OpenAPI and Virtual Host/SNI behavior.
- `run.sh` now starts `/app/runtime.py` directly.

## 0.5.x — Discovery, API relay and virtual hosts

- Added targeted single-host Web/SSH/SMB/VNC discovery and per-host Rescan.
- Expanded Docker-oriented Web probing with common `8xxx` ports.
- Added per-SSH-connection saved password authentication.
- Added Swagger/OpenAPI Try-it-out relay through HA Remote Bridge, including endpoint-root handling for `/api-docs` applications.
- Made hostname/IP the canonical grouping identity.
- Added per-Web Virtual Host/SNI support and persistent address-bar indication.

## 0.4.x — Dashboard and complex Web compatibility

- Added compact Home Assistant-style host cards, service collapsing, sorting and filtering.
- Added clickable SMB breadcrumbs and improved file navigation.
- Added a read-only endpoint address bar.
- Added Teltonika/RutOS compatibility for authentication, SPA routing, dynamic assets and reload handling.
- Hardened already-proxied URL handling to prevent duplicate Ingress/proxy prefixes.

## 0.3.x — SMB file viewer

- Added inline SMB previews for images, PDFs, text/code, audio and video.
- Added Previous/Next navigation and path-aware Back/Up behavior.
- Added inline ZIP browsing with nested folders and bounded previews.

## 0.2.x — SSH, VNC, SMB and grouping

- Added SSH with ttyd/OpenSSH, reusable keys, known-host tracking and tmux-backed sessions.
- Added mixed-protocol host/group cards.
- Added VNC/noVNC support with View Only mode and keyboard controls.
- Added SMB resources, reusable credentials, browsing and downloads.
- Added persistent browser session tabs.

## 0.1.x — Initial Web proxy and ESPHome discovery

- Initial Ingress-only HTTP/HTTPS reverse proxy.
- Added isolated cookies, redirects, WebSockets, Fetch/XHR/EventSource compatibility and SSE streaming.
- Added tabbed sessions with Back/Forward/Reload controls.
- Added passive ESPHome mDNS discovery and Online/Offline health checks.
- Added targeted OPNsense/companion-origin compatibility and the Home Assistant-style dashboard.
