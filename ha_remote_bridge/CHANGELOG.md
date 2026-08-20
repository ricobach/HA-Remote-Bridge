# Changelog

## 0.1.3

- Switched LAN target request forwarding to a small explicit header allowlist.
- Prevents Home Assistant/Ingress-specific and oversized browser headers from being sent to embedded web servers such as ESPHome.
- Preserves target-specific cookies plus rewritten `Origin`/`Referer` so login and CSRF flows such as OPNsense continue to work.
- Keeps the larger Ingress-facing header limits introduced in 0.1.2.

## 0.1.2

- Increased the aiohttp request-header limits for Home Assistant Ingress traffic.
- Fixes `431 Request Header Fields Too Large` errors seen with some proxied resources when the browser/Ingress request contains large cookies or headers.
- Keeps the larger headers on the Ingress-facing side only; proxied LAN resources still receive filtered headers.

## 0.1.1

- Added resource-scoped target cookie forwarding so login/session and CSRF flows can work through Ingress.
- Rewrites target `Set-Cookie` headers so cookies stay isolated to the selected bridged resource.
- Added proper streaming for `text/event-stream` responses such as Server-Sent Events.
- Removed the 60-second total upstream timeout for long-lived HTTP responses.
- Improved proxy timeout error logging.

## 0.1.0

- Initial Home Assistant App implementation.
- Added Home Assistant Ingress UI.
- Added persistent HTTP/HTTPS resource management.
- Added reverse proxy support for standard HTTP methods.
- Added redirect and common path rewriting.
- Added WebSocket proxying.
- Added optional TLS certificate verification.
- Restricted direct access to the Home Assistant Ingress network path.
