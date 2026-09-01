"""Compatibility runner for HA Remote Bridge.

Adds narrowly scoped response rewriting for applications such as OPNsense and
standalone passive ESPHome web-server discovery. Existing launcher proxy,
ESPHome SSE, cookies, tabs, edit UI, and companion-origin behavior are reused.
"""

from __future__ import annotations

import asyncio
import re
from pathlib import PurePosixPath

from aiohttp import ClientError, ClientTimeout, web

import launcher  # applies the existing runtime patches before server startup
import main
from esphome_discovery import ESPHomeDiscovery


BRIDGE_COMPAT_VERSION = "0.1.14"
_original_rewrite_text_body = main.rewrite_text_body
DISCOVERY = ESPHomeDiscovery()


def _is_opnsense_widget_manager(tail: str) -> bool:
    """Return True for OPNsense's dynamic dashboard widget loader."""
    return PurePosixPath("/" + tail.lstrip("/")).name == "opnsense_widget_manager.js"


def _cache_bust_widget_manager_html(text: str) -> str:
    """Force browsers to fetch the bridge-rewritten OPNsense manager script."""
    pattern = re.compile(r"opnsense_widget_manager\.js(?:\?[^\"'<>\s]*)?", re.IGNORECASE)

    def replace(match: re.Match[str]) -> str:
        value = match.group(0)
        if "hrb=" in value:
            return re.sub(r"([?&])hrb=[^&\"'<>\s]*", rf"\1hrb={BRIDGE_COMPAT_VERSION}", value)
        separator = "&" if "?" in value else "?"
        return f"{value}{separator}hrb={BRIDGE_COMPAT_VERSION}"

    return pattern.sub(replace, text)


def rewrite_text_body(
    body: bytes,
    content_type: str,
    resource: dict,
    resource_id: str,
    prefix: str,
    *,
    force_opnsense_widgets: bool = False,
) -> bytes:
    """Rewrite normal text bodies plus OPNsense dynamic widget module roots."""
    lowered = content_type.lower()

    if force_opnsense_widgets:
        text = body.decode("utf-8", errors="replace")
        bridge = f"{prefix}proxy/{resource_id}"
        old = "/ui/js/widgets/"
        new = f"{bridge}/ui/js/widgets/"
        replacements = text.count(old)
        text = text.replace(old, new)
        main.LOGGER.info(
            "OPNsense widget manager rewrite for resource %s: %d occurrence(s)",
            resource_id,
            replacements,
        )
        return text.encode("utf-8", errors="replace")

    rewritten = _original_rewrite_text_body(
        body,
        content_type,
        resource,
        resource_id,
        prefix,
    )

    if "text/html" in lowered:
        text = rewritten.decode("utf-8", errors="replace")
        updated = _cache_bust_widget_manager_html(text)
        if updated != text:
            main.LOGGER.info(
                "OPNsense widget manager cache-bust injected for resource %s",
                resource_id,
            )
        return updated.encode("utf-8", errors="replace")

    return rewritten


def _with_discovery_ui(html: str) -> str:
    """Add a discovered ESPHome section to the existing dashboard shell."""
    panel = """
        <section class="card">
          <div class="row">
            <div>
              <div class="resource-name">Discovered ESPHome devices</div>
              <div class="resource-meta">Passive mDNS discovery. Only ESPHome nodes advertising a usable web server are shown.</div>
            </div>
            <button id="refresh-discovery" class="action secondary" type="button">Refresh</button>
          </div>
          <div id="discovered-esphome" style="margin-top:14px"><div class="empty">Searching for ESPHome devices…</div></div>
        </section>
"""
    marker = '        <section id="resources"></section>'
    if marker in html:
        html = html.replace(marker, panel + "\n" + marker, 1)

    script = r"""

  async function loadDiscoveredESPHome() {
    const host = document.getElementById('discovered-esphome');
    if (!host) return;
    try {
      const response = await fetch(api('api/discovery/esphome'), {cache: 'no-store'});
      if (!response.ok) throw new Error(await response.text());
      const devices = await response.json();
      host.innerHTML = '';
      if (!devices.length) {
        host.innerHTML = '<div class="empty">No unconfigured ESPHome web servers discovered yet.</div>';
        return;
      }

      for (const device of devices) {
        const row = document.createElement('div');
        row.className = 'row';
        row.style.padding = '10px 0';
        row.style.borderTop = '1px solid #8882';

        const info = document.createElement('div');
        const name = document.createElement('div');
        name.className = 'resource-name';
        name.textContent = device.name;
        const url = document.createElement('div');
        url.className = 'resource-url';
        url.textContent = device.url;
        const meta = document.createElement('div');
        meta.className = 'resource-meta';
        const details = [];
        if (device.version) details.push('ESPHome ' + device.version);
        if (device.mac) details.push(device.mac);
        details.push(device.hostname);
        meta.textContent = details.join(' · ');
        info.append(name, url, meta);

        const add = document.createElement('button');
        add.type = 'button';
        add.className = 'action';
        add.textContent = 'Add';
        add.onclick = async () => {
          add.disabled = true;
          const result = await fetch(api('api/resources'), {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
              name: device.name,
              url: device.url,
              verify_ssl: false,
            }),
          });
          if (!result.ok) {
            add.disabled = false;
            alert(await result.text());
            return;
          }
          await load();
          await loadDiscoveredESPHome();
        };

        row.append(info, add);
        host.append(row);
      }
    } catch (error) {
      host.innerHTML = '<div class="empty">ESPHome discovery unavailable: ' + String(error) + '</div>';
    }
  }

  const discoveryRefresh = document.getElementById('refresh-discovery');
  if (discoveryRefresh) discoveryRefresh.addEventListener('click', loadDiscoveredESPHome);
  loadDiscoveredESPHome();
  setInterval(loadDiscoveredESPHome, 10000);
"""
    final_marker = "\n  load();\n</script>"
    if final_marker in html:
        html = html.replace(final_marker, script + final_marker, 1)
    return html


async def list_discovered_esphome(request: web.Request) -> web.Response:
    """Return unconfigured ESPHome web servers currently visible via mDNS."""
    return web.json_response(DISCOVERY.snapshot(main.STORE.resources))


async def proxy(request: web.Request) -> web.StreamResponse:
    """Proxy a resource, additionally rewriting targeted OPNsense assets."""
    if main.CLIENT is None:
        raise web.HTTPServiceUnavailable(text="Proxy client is not ready")

    resource_id = request.match_info["resource_id"]
    tail = request.match_info.get("tail", "")
    resource = main.STORE.get(resource_id)
    if resource is None:
        raise web.HTTPNotFound(text="Unknown resource")

    if request.headers.get("Upgrade", "").lower() == "websocket":
        return await main.proxy_websocket(request, resource, resource_id, tail)

    target = main.upstream_url(resource, tail, request.query_string)
    body = await request.read() if request.can_read_body else None
    is_widget_manager = _is_opnsense_widget_manager(tail)
    request_headers = main.filtered_request_headers(request, target, resource_id)

    if is_widget_manager:
        for header in ("If-None-Match", "If-Modified-Since"):
            request_headers.pop(header, None)

    try:
        upstream = await main.CLIENT.request(
            request.method,
            target,
            headers=request_headers,
            data=body,
            allow_redirects=False,
            ssl=None if resource.get("verify_ssl", True) else False,
            timeout=ClientTimeout(total=None, connect=15, sock_connect=15, sock_read=None),
        )

        try:
            content_type = upstream.headers.get("Content-Type", "")
            if "text/event-stream" in content_type.lower():
                return await main.stream_upstream_response(request, upstream, resource_id)

            raw_body = await upstream.read()
            headers = main.copy_response_headers(upstream)
            main.add_rewritten_cookies(headers, upstream, request, resource_id)

            prefix = main.ingress_prefix(request)
            if upstream.headers.get("Location"):
                headers["Location"] = main.rewrite_location(
                    upstream.headers["Location"],
                    target,
                    resource,
                    resource_id,
                    prefix,
                )

            lowered = content_type.lower()
            if raw_body and (
                is_widget_manager
                or "text/html" in lowered
                or "text/css" in lowered
                or "javascript" in lowered
                or "ecmascript" in lowered
            ):
                raw_body = rewrite_text_body(
                    raw_body,
                    content_type,
                    resource,
                    resource_id,
                    prefix,
                    force_opnsense_widgets=is_widget_manager,
                )

            if is_widget_manager:
                headers["Cache-Control"] = "no-store, no-cache, must-revalidate"
                headers["Pragma"] = "no-cache"
                headers.popall("ETag", None)
                headers.popall("Last-Modified", None)

            return web.Response(
                status=upstream.status,
                reason=upstream.reason,
                headers=headers,
                body=b"" if request.method == "HEAD" else raw_body,
            )
        finally:
            upstream.release()
    except (ClientError, asyncio.TimeoutError) as err:
        main.LOGGER.warning("Proxy request failed for %s: %r", resource["name"], err)
        raise web.HTTPBadGateway(text=f"Unable to reach {resource['name']}: {err}") from err


main.rewrite_text_body = rewrite_text_body
main.proxy = proxy
main.INDEX_HTML = _with_discovery_ui(main.INDEX_HTML)


async def _run() -> None:
    """Start the patched app and standalone ESPHome mDNS discovery."""
    app = launcher.create_app()
    app.router.add_get("/api/discovery/esphome", list_discovered_esphome)
    runner = web.AppRunner(
        app,
        access_log=main.LOGGER,
        max_line_size=64 * 1024,
        max_field_size=64 * 1024,
        max_headers=128 * 1024,
    )

    try:
        DISCOVERY.start()
        main.LOGGER.info("ESPHome mDNS discovery active")
    except Exception as err:  # discovery failure must never stop the proxy
        main.LOGGER.warning("Unable to start ESPHome mDNS discovery: %r", err)

    await runner.setup()
    site = web.TCPSite(runner, host="0.0.0.0", port=main.PORT)
    await site.start()
    main.LOGGER.info("Compatibility runner %s active", BRIDGE_COMPAT_VERSION)

    try:
        await asyncio.Event().wait()
    finally:
        DISCOVERY.close()
        await runner.cleanup()


if __name__ == "__main__":
    asyncio.run(_run())
