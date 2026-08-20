# HA Remote Bridge App

HA Remote Bridge is the Home Assistant App companion for the HA Remote Bridge HACS integration.

The App provides a Home Assistant Ingress UI and reverse proxy for selected local HTTP and HTTPS resources. Home Assistant handles the remote user authentication before traffic reaches the App.

## Current features

- Home Assistant Ingress UI.
- Add and remove local HTTP/HTTPS resources.
- Persistent resource configuration in `/data/resources.json`.
- HTTP methods proxied to the selected target.
- HTTP redirect rewriting.
- Best-effort HTML and CSS root-path rewriting.
- Browser shim for root-relative `fetch`, XHR and WebSocket connections.
- WebSocket bridging.
- Optional TLS verification for self-signed local HTTPS services.
- Ingress-only listener; no LAN or Internet-facing port is published.

## Current limitations

This is an early `0.1.0` implementation. Complex web applications can still break when they generate hard-coded absolute paths, use unusual browser APIs, or depend on authentication cookies. SSH support is planned for a later release.
