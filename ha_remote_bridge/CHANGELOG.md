# Changelog

## 0.1.7

- Fixed duplicate Home Assistant Ingress path rewriting in the injected browser shim.
- Prevents already-proxied URLs such as ESPHome `/events` from being wrapped a second time into paths like `/proxy/<id>/api/hassio_ingress/.../proxy/<id>/events`.
- Makes EventSource rewriting idempotent for ESPHome Server-Sent Events.
- Hardens modern `fetch()` handling so already-bridged URLs bypass the older string-only rewrite path.

## 0.1.6

- Hardened ESPHome `/events` Server-Sent Events proxying.
- Preserves `Last-Event-ID` for native EventSource reconnect semantics.
- Forces `Accept: text/event-stream`, `Cache-Control: no-cache`, and `Accept-Encoding: identity` for `/events` requests to keep embedded-device traffic small and deterministic.
- Adds `Cache-Control: no-cache` and `X-Accel-Buffering: no` on streamed SSE responses.
- Replaced the EventSource wrapper with a native subclass-style shim for better browser compatibility.
- Added SSE open/close diagnostics including chunk and byte counts.

## 0.1.5

- Extended the injected browser compatibility shim to rewrite `fetch()` calls that use `Request` objects or `URL` objects, not only plain string URLs.
- Added `EventSource` URL rewriting for proxied applications using Server-Sent Events.
- Helps modern SPA applications whose HTML/JS shell loads through the bridge but whose data requests otherwise bypass the proxied resource path.

## 0.1.4

- Forward `X-CSRFToken` and `X-Requested-With` to bridged targets when the browser sends them.
- Fixes OPNsense AJAX POST/PUT/DELETE calls that returned `403` after the strict ESPHome-safe header allowlist was introduced.
- Keeps Home Assistant/Ingress-specific headers blocked so embedded targets such as ESPHome are not exposed to oversized proxy headers.

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
