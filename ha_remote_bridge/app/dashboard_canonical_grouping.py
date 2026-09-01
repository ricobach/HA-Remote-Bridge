"""Canonical host grouping for HA Remote Bridge 0.5.2.

A Group / Host value is a friendly display label. The actual grouping identity
is the endpoint hostname/IP so an auto-grouped existing connection and a newly
discovered connection with an explicit friendly group cannot split into two
cards for the same physical host.
"""

from ui_shell_v20 import INDEX_HTML as BASE_INDEX_HTML

INDEX_HTML = BASE_INDEX_HTML

HOST_GROUPING_JS = r'''
<script>
(function installCanonicalHostGrouping(){
  if(typeof resourceHost!=='function' || typeof groupKey!=='function')return;

  // Host/IP is the canonical device identity. Explicit Group / Host remains a
  // presentation label selected by renderResources() when one is available.
  // Resources without a resolvable host retain the old friendly-name/id
  // fallback so unusual connection definitions still render deterministically.
  groupKey=function(resource){
    const host=String(resourceHost(resource)||'').trim().toLowerCase();
    if(host)return 'host:'+host;
    const explicit=String(resource.group_name||'').trim().toLowerCase();
    return explicit?'name:'+explicit:'resource:'+resource.id;
  };

  // Re-render once after this final composition layer has replaced groupKey.
  // resourceData may still be loading, in which case the normal load callback
  // will render using the new function later.
  try{if(Array.isArray(resourceData)&&resourceData.length)renderResources();}catch(_){}
})();
</script>
'''

INDEX_HTML = INDEX_HTML.replace("</body>", HOST_GROUPING_JS + "\n</body>", 1)

for required in (
    "installCanonicalHostGrouping",
    "return 'host:'+host",
    "groupKey=function(resource)",
):
    if required not in INDEX_HTML:
        raise RuntimeError(f"Canonical host grouping composition failed: missing {required}")
