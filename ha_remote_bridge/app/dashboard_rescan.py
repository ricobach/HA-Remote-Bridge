"""Host-card rescan controls for HA Remote Bridge 0.5.7."""

from ui_shell_v21 import INDEX_HTML as BASE_INDEX_HTML

INDEX_HTML = BASE_INDEX_HTML

RESCAN_CSS = r'''
    /* 0.5.7: per-host targeted rescan action. */
    .group-rescan-button {
      height:28px; padding:0 9px; border:1px solid var(--border); border-radius:7px;
      background:var(--surface); color:var(--muted); font-size:10px; white-space:nowrap;
    }
    .group-rescan-button:hover { color:var(--ha-blue); border-color:color-mix(in srgb,var(--ha-blue) 45%,var(--border)); }
    @media (max-width:620px) {
      .group-rescan-button { width:28px; padding:0; font-size:0; }
      .group-rescan-button::before { content:'↻'; font-size:15px; }
    }
'''
INDEX_HTML = INDEX_HTML.replace("  </style>", RESCAN_CSS + "\n  </style>", 1)

RESCAN_JS = r'''
<script>
(function installHostRescan(){
  if(typeof renderResources!=='function')return;
  const previousRenderResources=renderResources;

  function openRescan(host,group){
    const dialog=document.getElementById('host-discovery-dialog');
    const hostInput=document.getElementById('host-discovery-host');
    const groupInput=document.getElementById('host-discovery-group');
    const extraInput=document.getElementById('host-discovery-extra');
    const scanButton=document.getElementById('host-discovery-scan');
    const addButton=document.getElementById('host-discovery-add');
    const status=document.getElementById('host-discovery-status');
    const results=document.getElementById('host-discovery-results');
    if(!dialog||!hostInput||!groupInput||!scanButton)return;

    hostInput.value=host||'';
    groupInput.value=group||host||'';
    if(extraInput)extraInput.value='';
    if(status)status.textContent='';
    if(results)results.innerHTML='';
    if(addButton)addButton.disabled=true;
    if(!dialog.open)dialog.showModal();
    window.setTimeout(()=>scanButton.click(),0);
  }

  function decorateHostCards(){
    document.querySelectorAll('.connection-group-card').forEach(card=>{
      if(card.querySelector('.group-rescan-button'))return;
      const head=card.querySelector('.group-head');
      const host=card.querySelector('.group-host')?.textContent?.trim()||'';
      const group=card.querySelector('.group-name')?.textContent?.trim()||host;
      if(!head||!host)return;
      // Only offer targeted rescans for concrete hosts/IPs. Resource URLs are
      // not expected here after canonical host grouping, but guard anyway.
      if(host.includes('://'))return;
      const button=document.createElement('button');
      button.type='button';
      button.className='group-rescan-button';
      button.textContent='↻ Rescan';
      button.title='Rescan '+host+' for Web, SSH, SMB and VNC services';
      button.onclick=event=>{
        event.stopPropagation();
        if(typeof closeCompactMenus==='function')closeCompactMenus();
        openRescan(host,group);
      };
      const health=head.querySelector('.group-health');
      if(health)head.insertBefore(button,health);else head.appendChild(button);
    });
  }

  renderResources=function(){
    previousRenderResources();
    decorateHostCards();
  };

  try{decorateHostCards();}catch(_){}
})();
</script>
'''

INDEX_HTML = INDEX_HTML.replace("</body>", RESCAN_JS + "\n</body>", 1)

for required in (
    "group-rescan-button",
    "↻ Rescan",
    "host-discovery-dialog",
    "scanButton.click()",
):
    if required not in INDEX_HTML:
        raise RuntimeError(f"Host rescan UI composition failed: missing {required}")
