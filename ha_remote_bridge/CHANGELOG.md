# Changelog

## 0.2.7

- Hardened SMB browsing when used through Home Assistant Ingress and external reverse proxies.
- Added a short SMB TCP precheck before starting `smbclient`, so unreachable hosts fail quickly instead of holding the ingress request open.
- Reduced Samba client timeouts for share and directory discovery and made subprocess cancellation kill the underlying `smbclient` process cleanly.
- SMB share/list API failures now return compact JSON errors instead of raw HTML or long text responses.
- The SMB browser now detects reverse-proxy HTML errors such as Cloudflare 502 pages and shows a concise diagnostic instead of rendering the entire error document.
- Added a browser-side 12-second timeout for SMB list operations so stale ingress requests do not hang indefinitely.
- Corrected the runtime version banner to report the current release.

## 0.2.6

- Added first-class SMB resources with Session Name, Group / Host, Host / IP, Port, and reusable credential selection.
- Added an SMB file browser inside the normal session-tab UI with share discovery, folder navigation, file-size display, refresh/up navigation, and file downloads.
- Added reusable SMB credential profiles with friendly name, username, password, and optional domain/workgroup.
- SMB passwords are stored only in the App-local `/data/smb` vault with restrictive permissions and are omitted from API responses and normal resource definitions.
- Samba receives saved credentials through short-lived mode-0600 authentication files rather than command-line password arguments.
- Added Guest / anonymous SMB mode for shares that do not require authentication.
- Added SMB Online/Offline checks using the configured TCP port (default 445).
- Added SMB filtering and host grouping alongside Web, SSH, and VNC endpoints.
- SMB browsing is constrained to configured SMB resources; HA Remote Bridge does not expose a generic SMB mount or arbitrary TCP tunnel.
- Added the Alpine `samba-client` package to the App image.

## 0.2.5

- Improved VNC responsiveness by keeping the remote framebuffer size stable and scaling locally in noVNC instead of continuously requesting remote desktop resizes.
- Tuned noVNC for lower-latency interactive use with quality level 5 and compression level 1.
- Enabled TCP `TCP_NODELAY` on the App-to-VNC connection to reduce latency for small keyboard and mouse messages.
- Increased VNC read batching to reduce proxy overhead on framebuffer updates.
- Added explicit keyboard focus handling on pointer/touch interaction, reconnect, and when returning to the VNC page.
- Added a compact VNC toolbar with a `Keyboard` focus button and `Ctrl-Alt-Del` action.
- Added a visible keyboard-focus status indicator so it is clear whether keyboard input is being sent to the remote desktop.
- Changed noVNC asset caching to `no-cache` revalidation to avoid stale mixed-version ES modules after App upgrades.

## 0.2.4

- Added first-class VNC resources with Session Name, Group / Host, Host / IP, Port, and View Only settings.
- Added a browser-based noVNC client inside the normal HA Remote Bridge session-tab UI.
- VNC traffic is relayed only to the configured VNC resource; the App does not expose an arbitrary TCP/WebSocket proxy.
- Added VNC Online/Offline checks based on TCP reachability of the configured VNC port.
- Added VNC filtering and grouping alongside Web and SSH endpoints, so one host card can contain HTTP/HTTPS, SSH, and VNC connections on different ports.
- VNC passwords are requested interactively by noVNC when needed and are not stored by HA Remote Bridge.
- Added optional View Only mode to disable keyboard and mouse input for a VNC resource.
- Added the Alpine `novnc` package to the App image and serves its ES-module assets through Home Assistant Ingress.
- Switched the runtime to the current polished SSH UI plus VNC support.

## 0.2.3

- Reworked the SSH editor for narrow Home Assistant Ingress layouts.
- Removed horizontal overflow and made the modal viewport-safe with vertical scrolling only when needed.
- Simplified the SSH credential selector to friendly key names and moved fingerprint/type details into a compact summary.
- Improved Session Name, Group / Host, Host / IP, Port, Username, and credential field layout.
- Added a cleaner security note and sticky Save/Cancel actions.

## 0.2.2

- Added first-class connection grouping with an optional `Group / Host` name on Web and SSH resources.
- Resources with the same explicit group name are rendered together under one host card while keeping independent connection/session IDs.
- When no group name is set, resources that resolve to the same hostname or IP are grouped automatically.
- Group cards can contain mixed protocols and ports, such as HTTPS `:443`, HTTP `:8080`, and SSH `:22` for the same host.
- Each grouped endpoint keeps its own Online/Offline status, type badge, Open/Show, Edit, Delete, and session tab.
- Discovered ESPHome devices use the ESPHome device name as their default group name when added.
- Added Group / Host fields to Web add/edit and SSH add/edit dialogs.
- Global search now matches Group / Host names as well as resource names and URLs.

## 0.2.1

- Keeps session-tab labels tied to the configured Session/Resource Name instead of replacing them with the proxied page title.
- Persists the list of open session tabs and the active tab in browser local storage, so leaving HA Remote Bridge and returning restores the same tabs.
- Restores only non-sensitive session state (resource IDs and the selected tab); credentials are never stored in browser session state.
- Added `tmux`-backed SSH terminals. `ttyd` is now only the browser attachment layer, while the actual SSH client runs inside a persistent tmux session per SSH resource.
- SSH commands continue running when the HA Remote Bridge page or browser attachment is closed, as long as the HA Remote Bridge App/container itself remains running and the SSH connection stays alive.
- Reopening a restored SSH tab reattaches to the existing tmux-backed terminal instead of starting a new shell.
- Editing or deleting an SSH resource terminates its persistent tmux session so stale sessions cannot reconnect to an old target definition.

## 0.2.0

- Added first-class SSH resources alongside HTTP/HTTPS and ESPHome resources.
- Added browser-based interactive SSH terminals using `ttyd` and the system OpenSSH client, proxied entirely through Home Assistant Ingress.
- Added reusable SSH credential profiles so one private key can be shared by multiple SSH resources without re-entering it.
- Added an App-local SSH credential vault under `/data/ssh` with private key files stored separately from normal resource definitions and permissions restricted to the App.
- Private key material is never returned by the credential API; only safe metadata, fingerprints, and public keys are exposed to the dashboard.
- Added ED25519 key generation from the dashboard with one-click public-key copying for installation on target hosts.
- Added importing of existing OpenSSH/PEM private keys. Encrypted private keys remain encrypted and OpenSSH prompts for their passphrase when a session starts.
- Added persistent SSH `known_hosts` handling with `StrictHostKeyChecking=accept-new`, so first-seen host keys are recorded and later host-key changes are rejected.
- Added SSH resource creation/editing fields for host, port, username, and reusable credential selection.
- Added SSH filtering, Online/Offline reachability checks using the SSH TCP port, and session-tab integration.
- Added `openssh-client` and `ttyd` to the App image.

## 0.1.17

- Added real Online/Offline status badges to configured resource cards.
- Added a lightweight `/api/resources/status` endpoint that probes all configured targets concurrently from the App container.
- Treats any HTTP response as reachable/Online; connection failures and short timeouts are shown as Offline.
- Shows `Checking…` while a configured resource has not received its first health result yet.
- Marks currently discovered ESPHome mDNS devices as Online.
- Refreshes configured-resource health every 15 seconds and on manual dashboard refresh.

## 0.1.16

- Reworked the dashboard to visually align more closely with ESPHome Device Builder and Home Assistant.
- Added a compact Home Assistant-style blue header with HA Remote Bridge branding and discovery status.
- Added a single global device search field that filters configured and discovered devices together.
- Added grid/list view switching for configured resources and discovered ESPHome devices.
- Added an expandable Filters toolbar with configured-resource type filters and IPv4/IPv6 discovery filters.
- Redesigned configured resources and discovered devices into compact ESPHome-style device cards with chips, metadata, and action rows.
- Kept the Discovered ESPHome devices section collapsible.
- Kept Add Resource as an expandable inline panel.
- Preserved session tabs, close buttons, Back/Forward/Reload navigation, Edit/Delete, ESPHome mDNS discovery, ESPHome SSE support, MyIP companion proxying, and OPNsense compatibility behavior.

## 0.1.15

- Redesigned the App dashboard around a branded blue header and cleaner card/table layout inspired by the new HA Remote Bridge visual mockup.
- Added an inline HA Remote Bridge bridge/network brand mark and browser favicon, plus a reusable `icon.svg` branding asset in the App source tree.
- Added text filtering for both discovered ESPHome devices and configured resources.
- Added IPv4/IPv6 filtering for discovered ESPHome devices.
- Added ESPHome/HTTP/HTTPS filtering for configured resources.
- Added a collapsible `Discovered ESPHome devices` panel.
- Added a single Refresh action for configured resources and discovery results.
- Moved manual Add Resource into a compact expandable form.
- Preserves `resource_type: esphome` and a discovery key when a discovered ESPHome device is added, so later filtering and profile-specific behavior can identify it reliably.
- Keeps session tabs, Back/Forward/Reload navigation, Edit/Delete actions, mDNS discovery, ESPHome SSE support, MyIP companion proxying, and OPNsense compatibility behavior intact.

## 0.1.14

- Added standalone passive ESPHome discovery directly in the App; the Home Assistant integration is not required.
- Browses ESPHome mDNS services instead of scanning the LAN.
- Correlates `_esphomelib._tcp` identity with `_http._tcp` web-server advertisements so only ESPHome nodes with a usable web endpoint are offered.
- Added a `Discovered ESPHome devices` dashboard section with automatic refresh and one-click Add buttons.
- Filters devices that are already configured as resources.
- Supports ESPHome custom web-server ports and IPv4/IPv6 addresses.
- Added `py3-zeroconf` and host-network mode so multicast mDNS discovery works reliably from the App container.
- Discovery failure is isolated from the proxy; the existing resource proxy continues to start even if mDNS is unavailable.

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
