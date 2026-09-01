"""Online/offline status enhancements for the HA-style dashboard."""

from ui_shell_v2 import INDEX_HTML as BASE_INDEX_HTML


INDEX_HTML = BASE_INDEX_HTML

# Add an explicit offline visual state alongside the existing HA-style status chips.
INDEX_HTML = INDEX_HTML.replace(
    ".status-chip.online { color:#218c4c; background:#e5f7eb; }",
    ".status-chip.online { color:#218c4c; background:#e5f7eb; }\n"
    "    .status-chip.offline { color:#c62828; background:#fde8e7; }",
)

# Keep the latest server-side health snapshot separate from the configured resource data.
INDEX_HTML = INDEX_HTML.replace(
    "  let discoveryData = [];\n  let viewMode = 'grid';",
    "  let discoveryData = [];\n  let resourceStatus = {};\n  let viewMode = 'grid';",
)

# A configured resource gets a real Online/Offline/Checking badge instead of the old
# decorative Configured badge. Any HTTP response counts as reachable; failures/timeouts
# are reported as Offline by the backend health endpoint.
INDEX_HTML = INDEX_HTML.replace(
    "const chips=document.createElement('div');chips.append(makeChip('Configured','online'));const type=document.createElement('span');",
    "const chips=document.createElement('div');const health=resourceStatus[r.id];"
    "chips.append(health?makeChip(health.online?'Online':'Offline',health.online?'online':'offline'):makeChip('Checking…','unknown'));"
    "const type=document.createElement('span');",
)

# A device currently present in passive ESPHome mDNS discovery is online by definition.
INDEX_HTML = INDEX_HTML.replace(
    "const chips=document.createElement('div');chips.append(makeChip('Discovered','discovered'));const type=document.createElement('span');",
    "const chips=document.createElement('div');chips.append(makeChip('Online','online'));const type=document.createElement('span');",
)

# Fetch all configured-resource health states in one request. Rendering again after the
# result arrives updates every visible card without rebuilding the surrounding UI state.
INDEX_HTML = INDEX_HTML.replace(
    "  async function loadResources(){const res=await fetch(api('api/resources'),{cache:'no-store'});resourceData=await res.json();renderResources();}\n",
    "  async function loadResources(){const res=await fetch(api('api/resources'),{cache:'no-store'});resourceData=await res.json();renderResources();}\n"
    "  async function loadResourceStatus(){try{const res=await fetch(api('api/resources/status'),{cache:'no-store'});if(!res.ok)throw new Error(await res.text());resourceStatus=await res.json();renderResources();}catch(_){resourceStatus={};renderResources();}}\n",
)

# Refresh health whenever the user explicitly refreshes or changes resource inventory.
INDEX_HTML = INDEX_HTML.replace(
    "Promise.all([loadResources(),loadDiscoveredESPHome()])",
    "Promise.all([loadResources(),loadDiscoveredESPHome(),loadResourceStatus()])",
)
INDEX_HTML = INDEX_HTML.replace(
    "closeEdit();updateNavigation();await loadResources();",
    "closeEdit();updateNavigation();await Promise.all([loadResources(),loadResourceStatus()]);",
)

# Initial health check plus a lightweight periodic refresh. Discovery keeps its own faster
# 10-second mDNS refresh; configured HTTP resources are probed every 15 seconds.
INDEX_HTML = INDEX_HTML.replace(
    "  loadResources();loadDiscoveredESPHome();setGridClass();setInterval(loadDiscoveredESPHome,10000);",
    "  loadResources();loadDiscoveredESPHome();loadResourceStatus();setGridClass();setInterval(loadDiscoveredESPHome,10000);setInterval(loadResourceStatus,15000);",
)
