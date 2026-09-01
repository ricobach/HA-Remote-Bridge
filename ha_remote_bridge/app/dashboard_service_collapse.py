"""Collapsible multi-service host cards for HA Remote Bridge 0.4.3."""

from ui_shell_v15 import INDEX_HTML as BASE_INDEX_HTML

INDEX_HTML = BASE_INDEX_HTML

COLLAPSE_CSS = r'''
    /* 0.4.3: keep multi-service host cards compact in the main dashboard. */
    .connection-row.hrb-service-hidden { display:none !important; }
    .hrb-service-expander {
      width:100%;
      min-height:34px;
      border:0;
      border-top:1px solid var(--border);
      background:color-mix(in srgb,var(--surface) 96%,var(--text) 4%);
      color:var(--ha-blue);
      padding:7px 12px;
      text-align:left;
      font-size:11px;
      font-weight:600;
      cursor:pointer;
    }
    .hrb-service-expander:hover {
      background:color-mix(in srgb,var(--surface) 91%,var(--ha-blue) 9%);
    }
    .hrb-service-expander .hrb-expander-chevron {
      display:inline-block;
      width:16px;
      transition:transform .15s ease;
    }
    .hrb-service-expander.expanded .hrb-expander-chevron { transform:rotate(90deg); }
'''
INDEX_HTML = INDEX_HTML.replace("  </style>", COLLAPSE_CSS + "\n  </style>", 1)

COLLAPSE_JS = r'''
<script>
(function installServiceCollapse(){
  const STORAGE_KEY='ha_remote_bridge.service_groups.v1';
  let decorating=false;

  function loadState(){
    try{return JSON.parse(localStorage.getItem(STORAGE_KEY)||'{}')||{};}catch(_){return {};}
  }
  function saveState(state){
    try{localStorage.setItem(STORAGE_KEY,JSON.stringify(state));}catch(_){}
  }
  function cardKey(card){
    const name=(card.querySelector('.group-name')?.textContent||'').trim().toLowerCase();
    const host=(card.querySelector('.group-host')?.textContent||'').trim().toLowerCase();
    return name+'|'+host;
  }
  function servicePriority(row){
    const mark=(row.querySelector('.protocol-mark')?.textContent||'').trim().toUpperCase();
    const meta=(row.querySelector('.connection-meta')?.textContent||'').trim().toUpperCase();
    if(meta.startsWith('ESPHOME'))return 0;
    if(mark==='WEB')return 1;
    if(mark==='SSH')return 2;
    if(mark==='SMB')return 3;
    if(mark==='VNC')return 4;
    return 10;
  }
  function orderRows(card,rows){
    const ordered=[...rows].sort((a,b)=>servicePriority(a)-servicePriority(b));
    const expander=card.querySelector('.hrb-service-expander');
    for(const row of ordered)card.insertBefore(row,expander||null);
    return ordered;
  }
  function decorateCard(card,state){
    const old=card.querySelector('.hrb-service-expander');
    if(old)old.remove();
    let rows=[...card.querySelectorAll(':scope > .connection-row')];
    rows.forEach(row=>row.classList.remove('hrb-service-hidden'));
    if(rows.length<=1)return;

    rows=orderRows(card,rows);
    const key=cardKey(card);
    const expanded=state[key]===true;
    rows.forEach((row,index)=>row.classList.toggle('hrb-service-hidden',!expanded&&index>0));

    const button=document.createElement('button');
    button.type='button';
    button.className='hrb-service-expander'+(expanded?' expanded':'');
    const hiddenCount=rows.length-1;
    button.innerHTML='<span class="hrb-expander-chevron">›</span><span></span>';
    button.querySelector('span:last-child').textContent=expanded?'Hide services':('Show '+hiddenCount+' more');
    button.setAttribute('aria-expanded',expanded?'true':'false');
    button.addEventListener('click',()=>{
      const nowExpanded=button.getAttribute('aria-expanded')!=='true';
      state[key]=nowExpanded;
      saveState(state);
      rows.forEach((row,index)=>row.classList.toggle('hrb-service-hidden',!nowExpanded&&index>0));
      button.setAttribute('aria-expanded',nowExpanded?'true':'false');
      button.classList.toggle('expanded',nowExpanded);
      button.querySelector('span:last-child').textContent=nowExpanded?'Hide services':('Show '+hiddenCount+' more');
    });
    card.appendChild(button);
  }
  function decorate(){
    if(decorating)return;
    decorating=true;
    try{
      const state=loadState();
      document.querySelectorAll('#resources > .connection-group-card').forEach(card=>decorateCard(card,state));
    }finally{decorating=false;}
  }
  window.hrbDecorateServiceGroups=decorate;

  const resources=document.getElementById('resources');
  if(resources){
    const observer=new MutationObserver(()=>{if(!decorating)setTimeout(decorate,0);});
    observer.observe(resources,{childList:true});
  }
  setTimeout(decorate,0);
})();
</script>
'''
INDEX_HTML = INDEX_HTML.replace("</body>", COLLAPSE_JS + "\n</body>", 1)

for required in (
    "ha_remote_bridge.service_groups.v1",
    "hrb-service-expander",
    "Show '+hiddenCount+' more",
    "servicePriority(row)",
):
    if required not in INDEX_HTML:
        raise RuntimeError(f"Service-collapse UI composition failed: missing {required}")
