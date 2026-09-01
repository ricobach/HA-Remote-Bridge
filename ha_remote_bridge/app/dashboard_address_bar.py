"""Read-only endpoint address bar for HA Remote Bridge 0.4.13."""

from ui_shell_v17 import INDEX_HTML as BASE_INDEX_HTML

INDEX_HTML = BASE_INDEX_HTML

ADDRESS_CSS = r'''
    /* 0.4.13: browser-style, read-only endpoint location display. */
    .nav-title {
      display:flex !important;
      align-items:center;
      min-width:0;
      flex:1 1 auto;
      height:30px;
      padding:0 11px;
      border:1px solid var(--border);
      border-radius:7px;
      background:color-mix(in srgb,var(--surface) 96%,var(--text) 4%);
      color:var(--muted);
      font-size:11px;
      line-height:30px;
      overflow:hidden;
      text-overflow:ellipsis;
      white-space:nowrap;
      user-select:text;
      cursor:text;
    }
    .nav-title.hrb-address-secure::before {
      content:'🔒';
      flex:0 0 auto;
      margin-right:6px;
      font-size:10px;
      line-height:1;
    }
    .nav-title.hrb-address-plain::before {
      content:'○';
      flex:0 0 auto;
      margin-right:6px;
      color:var(--muted);
      font-size:11px;
      line-height:1;
    }
    @media (max-width:760px) {
      .nav-title {
        display:flex !important;
        font-size:10px;
        padding:0 8px;
      }
      .nav-title.hrb-address-secure::before,
      .nav-title.hrb-address-plain::before { margin-right:4px; }
    }
'''
INDEX_HTML = INDEX_HTML.replace("  </style>", ADDRESS_CSS + "\n  </style>", 1)

ADDRESS_JS = r'''
<script>
(function installReadOnlyEndpointAddress(){
  const address=document.getElementById('nav-title');
  if(!address)return;
  address.setAttribute('role','textbox');
  address.setAttribute('aria-readonly','true');
  address.setAttribute('title','Current endpoint location (read only)');

  function cleanQuery(search){
    try{
      const params=new URLSearchParams(search||'');
      params.delete('_hrb_reload');
      const value=params.toString();
      return value?'?'+value:'';
    }catch(_){return search||'';}
  }

  function webAddress(session){
    const resource=session.resource||{};
    let configured;
    try{configured=new URL(resource.url);}catch(_){return resource.url||resource.name||'';}

    try{
      const current=new URL(session.frame.contentWindow.location.href);
      const marker='/proxy/'+resource.id;
      const at=current.pathname.indexOf(marker);
      if(at>=0){
        let suffix=current.pathname.slice(at+marker.length)||'/';
        if(!suffix.startsWith('/'))suffix='/'+suffix;
        const basePath=(configured.pathname||'').replace(/\/$/,'');
        const path=(basePath||'')+(suffix==='/'?'/':suffix);
        return configured.origin+path+cleanQuery(current.search)+current.hash;
      }
    }catch(_){}

    return configured.href.replace(/\/$/,'')+'/';
  }

  function locationFor(session){
    if(!session||!session.resource)return '';
    const resource=session.resource;
    const kind=resourceKind(resource);
    if(kind==='http'||kind==='https'||kind==='esphome')return webAddress(session);
    if(kind==='ssh')return resource.url||('ssh://'+(resource.ssh_user?resource.ssh_user+'@':'')+(resource.ssh_host||'')+':'+(resource.ssh_port||22));
    if(kind==='vnc')return resource.url||('vnc://'+(resource.vnc_host||'')+':'+(resource.vnc_port||5900));
    if(kind==='smb')return resource.url||('smb://'+(resource.smb_host||'')+':'+(resource.smb_port||445));
    return resource.url||resource.name||'';
  }

  let last='';
  function updateAddress(){
    const session=typeof currentSession==='function'?currentSession():null;
    if(!session){
      last='';
      address.textContent='HA Remote Bridge';
      address.classList.remove('hrb-address-secure','hrb-address-plain');
      return;
    }
    const value=locationFor(session);
    if(value!==last){
      last=value;
      address.textContent=value;
      address.title=value+' — read only';
      address.classList.toggle('hrb-address-secure',value.startsWith('https://'));
      address.classList.toggle('hrb-address-plain',!value.startsWith('https://'));
    }
  }

  window.hrbUpdateEndpointAddress=updateAddress;
  setInterval(updateAddress,250);
  document.addEventListener('visibilitychange',()=>{if(!document.hidden)updateAddress();});
  updateAddress();
})();
</script>
'''
INDEX_HTML = INDEX_HTML.replace("</body>", ADDRESS_JS + "\n</body>", 1)

for required in (
    "installReadOnlyEndpointAddress",
    "Current endpoint location (read only)",
    "'/proxy/'+resource.id",
    "hrb-address-secure",
    "aria-readonly",
):
    if required not in INDEX_HTML:
        raise RuntimeError(f"Endpoint address UI composition failed: missing {required}")
