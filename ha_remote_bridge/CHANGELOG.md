# Changelog

## 0.1.13

- Added an Edit action to each resource on the App dashboard.
- Added a validated `PUT /api/resources/{resource_id}` endpoint for updating resource name, URL, and TLS verification.
- Preserves the existing resource ID and any extra resource metadata when editing, keeping cookie/session isolation stable.
- Refreshes an already-open session tab against the edited target after saving changes.
- Shows the current TLS verification state on each resource card.

## 0.1.12

- Made the OPNsense widget-module compatibility path deterministic instead of relying on imported server bindings.
- Starts the patched compatibility app directly and logs `Compatibility runner 0.1.12 active` at startup.
- Cache-busts `opnsense_widget_manager.js` from rewritten OPNsense HTML so the browser cannot keep executing an older unmodified copy.
- Continues rewriting OPNsense native dynamic `import('/ui/js/widgets/...')` paths through the active resource proxy.
- Keeps the existing ESPHome SSE, MyIP companion-origin relay, tabbed UI, cookie handling, and general proxy behavior unchanged.

## 0.1.11

- Forces OPNsense `opnsense_widget_manager.js` rewriting by filename even when the upstream server uses an unexpected JavaScript MIME type.
- Disables conditional requests and browser caching for the rewritten widget-manager script so stale unmodified copies cannot keep loading `/ui/js/widgets/...` from the Home Assistant origin.
- Adds diagnostics showing how many OPNsense widget module roots were rewritten for each resource request.
- Keeps the existing ESPHome SSE, MyIP companion-origin relay, tabbed UI, cookie handling, and general proxy behavior unchanged.

## 0.1.10

- Added targeted JavaScript response rewriting for OPNsense dashboard widget modules loaded with native dynamic `import()`.
- Rewrites only the known `/ui/js/widgets/` module root through the active HA Remote Bridge resource path.
- Fixes widget imports such as `SystemInformation.js`, `Cpu.js`, `Interfaces.js`, `Traffic.js`, `Firewall.js`, and similar modules that otherwise escape to the Home Assistant host and return `404`.
- Keeps the ESPHome SSE, MyIP companion-origin relay, tabbed UI, cookies, and general proxy behavior unchanged.

## 0.1.9

- Added restricted companion-origin proxying for applications that fetch data from approved secondary hosts.
- Added MyIP companion endpoints for `https://ipv4.myip.dk` and `https://ipv6.myip.dk` so `/api/ip` requests stay inside the Home Assistant Ingress origin.
- Fixes browser CORS and network-access-policy failures when the proxied MyIP page fetches its IPv4/IPv6 JSON data.
- Companion destinations are resolved from a server-side allowlist keyed by the configured resource; browser code cannot supply an arbitrary proxy destination.
- Keeps the tabbed UI and ESPHome/OPNsense proxy behavior from 0.1.8 unchanged.

## 0.1.8

- Added a browser-style top tab bar to the HA Remote Bridge manager.
- Keeps a permanent Home tab for resource management.
- Opens each active proxied resource in its own session tab.
- Added an `X` close button to every resource session tab.
- Added Back, Forward, and Reload controls for the active resource session.
- Resource sessions use separate iframes so navigation history and live connections remain independent between tabs.
- Kept the proxy, ESPHome SSE, cookie, and request-rewrite behavior unchanged from 0.1.7.

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
