# Changelog

This changelog keeps the major milestones and user-visible changes. Fine-grained development history remains available in Git.

## 0.5.x — Discovery, API relay and virtual hosts

### 0.5.9
- Keep the configured Virtual host / SNI prefix visible in the read-only address bar across navigation, reloads and restored sessions.

### 0.5.8
- Added per-Web-connection **Virtual host / SNI** support.
- Connect to an IP/port while presenting another hostname through the HTTP `Host` header and TLS SNI.
- Virtual-host redirects, Fetch/XHR, EventSource and WebSocket references remain inside the bridge.

### 0.5.7
- Added per-host **Rescan** from the main dashboard.
- Expanded targeted Web discovery with common Docker-oriented `8xxx` ports while retaining bounded single-host scanning.

### 0.5.6
- Added an origin-root Swagger/OpenAPI relay so API operations are forwarded to the endpoint root instead of being incorrectly resolved below an `/api-docs` path.

### 0.5.5
- Added Swagger UI request interception so **Try it out** calls travel through HA Remote Bridge instead of going directly to the Home Assistant origin.

### 0.5.2
- Made hostname/IP the canonical host-group identity so discovered and manually configured services for the same endpoint are shown on one card.

### 0.5.1
- Added targeted single-host service discovery for Web, SSH, SMB and VNC.
- Added protocol probing, duplicate detection and selective creation of discovered connections.

### 0.5.0
- Added per-SSH-connection saved password authentication.
- Passwords are stored separately from resource definitions with restrictive permissions and used through `sshpass -f`.

## 0.4.x — Dashboard and complex Web application compatibility

- Added compact Home Assistant-style host cards, service collapsing, sorting and filtering.
- Added clickable SMB breadcrumbs and improved file navigation.
- Added a read-only endpoint address bar.
- Added Teltonika/RutOS compatibility for Bearer authentication, SPA routing, dynamic assets, reload handling and initial route bootstrap.
- Added safer handling for already-proxied URLs to avoid duplicate Ingress/proxy prefixes.

## 0.3.x — SMB file viewer

- Added inline SMB file viewing for images, PDFs, text/code, audio and video.
- Added Previous/Next file navigation while preserving the containing directory.
- Added inline ZIP browsing with nested folders and bounded previews.
- Added path-aware Back/Up behavior and clickable directory navigation.

## 0.2.x — SSH, VNC, SMB and grouping

- Added first-class SSH resources with ttyd/OpenSSH, reusable key credentials, persistent known-hosts and tmux-backed sessions.
- Added host/group cards for multiple services on one device.
- Added VNC/noVNC support with View Only mode, keyboard focus controls and lower-latency proxy tuning.
- Added first-class SMB resources, reusable SMB credentials, share/directory browsing and downloads.
- Added persistent browser session tabs.

## 0.1.x — Initial Web proxy and ESPHome discovery

- Initial Home Assistant Ingress-only HTTP/HTTPS reverse proxy.
- Added resource-scoped cookie rewriting, redirects, WebSockets, Fetch/XHR/EventSource compatibility and SSE streaming.
- Added tabbed resource sessions with Back/Forward/Reload controls.
- Added passive ESPHome mDNS discovery and Online/Offline health checks.
- Added targeted compatibility for applications such as OPNsense and approved companion-origin requests.
- Added the Home Assistant/ESPHome-style management dashboard.
