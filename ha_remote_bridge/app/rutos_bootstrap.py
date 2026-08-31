"""Initial-route correction for RutOS/Teltonika SPAs behind Ingress."""

from __future__ import annotations

import json

import main


def install() -> None:
    """Append a narrow RutOS initial-route bootstrap to the browser shim."""
    previous_bridge_script = main.bridge_runtime_script

    def bridge_runtime_script(prefix: str, resource_id: str, target_url: str) -> str:
        original = previous_bridge_script(prefix, resource_id, target_url)
        bridge = f"{prefix}proxy/{resource_id}"
        extension = f'''<script data-ha-remote-bridge-rutos-bootstrap>
(() => {{
  const bridge = {json.dumps(bridge)};
  const initialBridgeRoot = window.location.pathname === bridge ||
    window.location.pathname === bridge + '/';
  if (!initialBridgeRoot) return;

  let completed = false;
  let attempts = 0;

  const looksLikeRutOS = () => {{
    if (document.querySelector('img[src*="tlt_networks_logo"], img[src*="teltonika"]')) return true;
    const text = (document.body && document.body.innerText || '').slice(0, 4000).toLowerCase();
    return text.includes('teltonika') && text.includes('realtime data');
  }};

  const findVueRouter = () => {{
    const candidates = [document.getElementById('app'), document.body];
    for (const node of candidates) {{
      if (!node) continue;
      if (node.__vue__ && node.__vue__.$router) return node.__vue__.$router;
      const descendants = node.querySelectorAll ? node.querySelectorAll('*') : [];
      for (let i = 0; i < descendants.length && i < 250; i++) {{
        const vm = descendants[i].__vue__;
        if (vm && vm.$router) return vm.$router;
      }}
    }}
    return null;
  }};

  const findOverviewControl = () => {{
    const direct = document.querySelector('a[href$="/status/overview"]');
    if (direct) return direct;
    const items = document.querySelectorAll('a,button,[role="button"]');
    for (const item of items) {{
      if ((item.textContent || '').trim().toLowerCase() === 'overview') return item;
    }}
    return null;
  }};

  const correctInitialRoute = () => {{
    if (completed) return;
    attempts += 1;
    if (!looksLikeRutOS()) {{
      if (attempts < 30) setTimeout(correctInitialRoute, 200);
      return;
    }}

    const router = findVueRouter();
    if (router) {{
      completed = true;
      try {{
        const result = router.replace('/status/overview');
        if (result && typeof result.catch === 'function') result.catch(() => {{}});
        return;
      }} catch (_) {{
        completed = false;
      }}
    }}

    const overview = findOverviewControl();
    if (overview) {{
      completed = true;
      overview.click();
      return;
    }}

    if (attempts < 30) setTimeout(correctInitialRoute, 200);
  }};

  if (document.readyState === 'loading') {{
    document.addEventListener('DOMContentLoaded', () => setTimeout(correctInitialRoute, 0), {{once:true}});
  }} else {{
    setTimeout(correctInitialRoute, 0);
  }}
}})();
</script>'''
        return original + extension

    main.bridge_runtime_script = bridge_runtime_script
