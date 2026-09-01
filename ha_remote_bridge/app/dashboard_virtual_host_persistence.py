"""Persistent virtual-host address prefix for HA Remote Bridge 0.5.9."""

from ui_shell_v23 import INDEX_HTML as BASE_INDEX_HTML

INDEX_HTML = BASE_INDEX_HTML

old_lookup = "const virtualHost=String((session.resource||{}).virtual_host||'').trim();"
new_lookup = "const canonicalResource=(Array.isArray(resourceData)?resourceData.find(r=>r&&session.resource&&r.id===session.resource.id):null)||session.resource||{};\n    const virtualHost=String(canonicalResource.virtual_host||'').trim();"

if old_lookup not in INDEX_HTML:
    raise RuntimeError("Virtual-host address persistence composition failed: lookup signature changed")
INDEX_HTML = INDEX_HTML.replace(old_lookup, new_lookup, 1)

for required in (
    "canonicalResource",
    "resourceData.find",
    "canonicalResource.virtual_host",
):
    if required not in INDEX_HTML:
        raise RuntimeError(f"Virtual-host address persistence composition failed: missing {required}")
