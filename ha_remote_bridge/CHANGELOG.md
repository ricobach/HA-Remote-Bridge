# Changelog

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
