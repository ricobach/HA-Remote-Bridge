"""Targeted host service discovery UI for HA Remote Bridge 0.5.1."""

from ui_shell_v19 import INDEX_HTML as BASE_INDEX_HTML

INDEX_HTML = BASE_INDEX_HTML

DISCOVERY_CSS = r'''
    /* 0.5.1: targeted host service discovery. */
    #host-discovery-dialog { width:min(720px,calc(100vw - 24px)); }
    #host-discovery-dialog .dialog-body { max-height:calc(100vh - 24px); overflow:auto; }
    .host-discovery-grid { display:grid; grid-template-columns:minmax(0,1fr) minmax(0,1fr); gap:10px; }
    .host-discovery-actions { display:flex; align-items:end; gap:8px; }
    .host-discovery-status { min-height:20px; color:var(--muted); font-size:11px; line-height:1.4; }
    .host-discovery-results { display:grid; gap:7px; margin-top:4px; }
    .host-discovery-result {
      display:grid; grid-template-columns:auto 40px minmax(0,1fr) auto; gap:9px; align-items:center;
      padding:9px 10px; border:1px solid var(--border); border-radius:8px; background:var(--surface);
    }
    .host-discovery-result.existing { opacity:.62; }
    .host-discovery-result input[type=checkbox] { width:18px; height:18px; }
    .host-discovery-service { min-width:0; }
    .host-discovery-service strong { display:block; font-size:12px; }
    .host-discovery-service span { display:block; margin-top:2px; color:var(--muted); font-size:10px; overflow-wrap:anywhere; }
    .host-discovery-port { color:var(--muted); font-size:11px; white-space:nowrap; }
    .host-discovery-confidence { display:inline-flex; align-items:center; min-height:22px; padding:0 7px; border-radius:11px; font-size:9px; white-space:nowrap; background:#e5f7eb; color:#218c4c; }
    .host-discovery-confidence.probable { background:#fff3d6; color:#9a6500; }
    .host-discovery-confidence.existing { background:#eee; color:#666; }
    .host-discovery-ssh-user { grid-column:3 / 5; display:flex; align-items:center; gap:8px; }
    .host-discovery-ssh-user label { flex:1; }
    .host-discovery-ssh-user input { width:100%; }
    @media (max-width:620px) {
      .host-discovery-grid { grid-template-columns:1fr; }
      .host-discovery-result { grid-template-columns:auto 34px minmax(0,1fr); }
      .host-discovery-result > .host-discovery-confidence { grid-column:3; justify-self:start; }
      .host-discovery-ssh-user { grid-column:2 / 4; }
    }
'''
INDEX_HTML = INDEX_HTML.replace("  </style>", DISCOVERY_CSS + "\n  </style>", 1)

DISCOVERY_JS = r'''
<script>
(function installHostDiscovery(){
  const addMenu=document.getElementById('compact-add-menu');
  if(!addMenu || typeof api!=='function')return;

  const dialog=document.createElement('dialog');
  dialog.id='host-discovery-dialog';
  dialog.innerHTML=`
    <div class="dialog-body">
      <div class="dialog-head">
        <h2>Discover services on host</h2>
        <div class="dialog-head-spacer"></div>
        <button id="host-discovery-close" class="icon-button" type="button">×</button>
      </div>
      <div class="edit-form">
        <div class="host-discovery-grid">
          <label>Host / IP
            <input id="host-discovery-host" type="text" placeholder="192.168.1.10" autocomplete="off">
          </label>
          <label>Group / Host name
            <input id="host-discovery-group" type="text" placeholder="e.g. Santos">
          </label>
        </div>
        <div class="host-discovery-grid">
          <label>Extra ports <span style="font-weight:400">(optional, max 20)</span>
            <input id="host-discovery-extra" type="text" placeholder="2222, 10443">
          </label>
          <div class="host-discovery-actions">
            <button id="host-discovery-scan" class="tool-button primary" type="button">Scan host</button>
          </div>
        </div>
        <div class="ssh-security-note"><span>⌕</span><div><strong>Targeted probe</strong><br>Only this host is scanned. HA Remote Bridge checks a bounded set of common Web, SSH, SMB and VNC ports plus any extra ports entered above. No subnet scan is performed.</div></div>
        <div id="host-discovery-status" class="host-discovery-status"></div>
        <div id="host-discovery-results" class="host-discovery-results"></div>
        <div class="dialog-actions ssh-dialog-actions">
          <button id="host-discovery-cancel" class="tool-button" type="button">Cancel</button>
          <button id="host-discovery-add" class="tool-button primary" type="button" disabled>Add selected</button>
        </div>
      </div>
    </div>`;
  document.body.appendChild(dialog);

  const hostInput=document.getElementById('host-discovery-host');
  const groupInput=document.getElementById('host-discovery-group');
  const extraInput=document.getElementById('host-discovery-extra');
  const scanButton=document.getElementById('host-discovery-scan');
  const addButton=document.getElementById('host-discovery-add');
  const status=document.getElementById('host-discovery-status');
  const results=document.getElementById('host-discovery-results');
  let scanData=null;

  const discoverButton=document.createElement('button');
  discoverButton.type='button';
  discoverButton.textContent='Discover host services';
  discoverButton.onclick=event=>{
    event.stopPropagation();
    if(typeof closeCompactMenus==='function')closeCompactMenus();
    status.textContent='';results.innerHTML='';scanData=null;addButton.disabled=true;
    dialog.showModal();
    setTimeout(()=>hostInput.focus(),0);
  };
  addMenu.insertBefore(discoverButton,addMenu.firstChild);

  function closeDialog(){if(dialog.open)dialog.close();}
  document.getElementById('host-discovery-close').onclick=closeDialog;
  document.getElementById('host-discovery-cancel').onclick=closeDialog;

  function parseExtraPorts(){
    const raw=extraInput.value.trim();
    if(!raw)return [];
    const values=raw.split(/[\s,;]+/).filter(Boolean);
    const ports=[];
    for(const value of values){
      const port=Number(value);
      if(!Number.isInteger(port)||port<1||port>65535)throw new Error('Extra ports must be numbers between 1 and 65535.');
      if(!ports.includes(port))ports.push(port);
    }
    if(ports.length>20)throw new Error('At most 20 extra ports may be scanned at once.');
    return ports;
  }

  function protocolMark(candidate){
    if(candidate.kind==='web')return candidate.scheme==='https'?'HTTPS':'HTTP';
    return String(candidate.service||candidate.kind||'').toUpperCase();
  }

  function renderResults(data){
    results.innerHTML='';
    const services=Array.isArray(data.services)?data.services:[];
    if(!services.length){
      results.innerHTML='<div class="empty">No supported Web, SSH, SMB or VNC services were detected on the scanned ports.</div>';
      addButton.disabled=true;return;
    }
    let selectable=0;
    services.forEach((candidate,index)=>{
      const row=document.createElement('div');row.className='host-discovery-result'+(candidate.already_configured?' existing':'');row.dataset.index=String(index);
      const checkbox=document.createElement('input');checkbox.type='checkbox';checkbox.checked=!candidate.already_configured;checkbox.disabled=Boolean(candidate.already_configured);checkbox.className='host-discovery-select';checkbox.dataset.index=String(index);
      if(!candidate.already_configured)selectable++;
      const mark=document.createElement('div');mark.className='protocol-mark';mark.textContent=protocolMark(candidate).slice(0,5);
      const info=document.createElement('div');info.className='host-discovery-service';const strong=document.createElement('strong');strong.textContent=candidate.service+' :'+candidate.port;const detail=document.createElement('span');detail.textContent=candidate.detail||'Service detected';info.append(strong,detail);
      const badge=document.createElement('span');badge.className='host-discovery-confidence '+(candidate.already_configured?'existing':candidate.confidence||'');badge.textContent=candidate.already_configured?'Already added':(candidate.confidence==='probable'?'Probable':'Confirmed');
      row.append(checkbox,mark,info,badge);
      if(candidate.kind==='ssh'&&!candidate.already_configured){
        const userWrap=document.createElement('div');userWrap.className='host-discovery-ssh-user';const label=document.createElement('label');label.textContent='SSH username';const user=document.createElement('input');user.type='text';user.className='host-discovery-ssh-username';user.dataset.index=String(index);user.value=candidate.suggested_username||'root';user.placeholder='root';label.appendChild(user);userWrap.appendChild(label);row.appendChild(userWrap);
      }
      results.appendChild(row);
    });
    addButton.disabled=selectable===0;
  }

  scanButton.onclick=async()=>{
    const host=hostInput.value.trim();
    if(!host){status.textContent='Enter a hostname or IP address.';hostInput.focus();return;}
    let extraPorts;
    try{extraPorts=parseExtraPorts();}catch(error){status.textContent=error.message;return;}
    if(!groupInput.value.trim())groupInput.value=host;
    scanButton.disabled=true;addButton.disabled=true;results.innerHTML='';status.textContent='Scanning '+host+'…';
    try{
      const response=await fetch(api('api/discovery/host'),{
        method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({host,extra_ports:extraPorts}),cache:'no-store'
      });
      if(!response.ok)throw new Error((await response.text())||('Scan failed ('+response.status+')'));
      scanData=await response.json();
      status.textContent='Probed '+scanData.scanned_ports+' ports in '+scanData.duration_ms+' ms · found '+scanData.services.length+' supported service'+(scanData.services.length===1?'':'s')+'.';
      renderResults(scanData);
    }catch(error){scanData=null;status.textContent=error.message||String(error);results.innerHTML='';}
    finally{scanButton.disabled=false;}
  };

  function formattedUrl(candidate,host){
    const bracketed=host.includes(':')&&!host.startsWith('[')?'['+host+']':host;
    const defaultPort=candidate.scheme==='https'?443:80;
    return candidate.scheme+'://'+bracketed+(candidate.port===defaultPort?'':':'+candidate.port);
  }

  function serviceName(candidate,group,services){
    if(candidate.kind==='ssh')return group+' SSH';
    if(candidate.kind==='smb')return group+' Files';
    if(candidate.kind==='vnc'){
      const many=services.filter(x=>x.kind==='vnc'&&!x.already_configured).length>1;
      return group+' VNC'+(many?' :'+candidate.port:'');
    }
    const manyWeb=services.filter(x=>x.kind==='web'&&!x.already_configured).length>1;
    return group+' Web'+(manyWeb?' '+candidate.service+' :'+candidate.port:'');
  }

  addButton.onclick=async()=>{
    if(!scanData)return;
    const group=groupInput.value.trim()||scanData.host;
    const selected=[...results.querySelectorAll('.host-discovery-select:checked')];
    if(!selected.length){status.textContent='Select at least one discovered service.';return;}
    const payloads=[];
    for(const checkbox of selected){
      const index=Number(checkbox.dataset.index),candidate=scanData.services[index];
      const name=serviceName(candidate,group,scanData.services);
      if(candidate.kind==='ssh'){
        const user=results.querySelector('.host-discovery-ssh-username[data-index="'+index+'"]')?.value.trim();
        if(!user){status.textContent='Enter an SSH username before adding the SSH connection.';return;}
        payloads.push({resource_type:'ssh',name,group_name:group,ssh_host:scanData.host,ssh_port:candidate.port,ssh_user:user,ssh_auth_mode:'prompt',ssh_credential_id:''});
      }else if(candidate.kind==='smb'){
        payloads.push({resource_type:'smb',name,group_name:group,smb_host:scanData.host,smb_port:candidate.port,smb_credential_id:''});
      }else if(candidate.kind==='vnc'){
        payloads.push({resource_type:'vnc',name,group_name:group,vnc_host:scanData.host,vnc_port:candidate.port,vnc_view_only:false});
      }else if(candidate.kind==='web'){
        payloads.push({resource_type:'generic',name,group_name:group,url:formattedUrl(candidate,scanData.host),verify_ssl:false});
      }
    }

    addButton.disabled=true;scanButton.disabled=true;status.textContent='Adding '+payloads.length+' connection'+(payloads.length===1?'':'s')+'…';
    const errors=[];
    for(const payload of payloads){
      try{
        const response=await fetch(api('api/resources'),{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)});
        if(!response.ok)errors.push(payload.name+': '+((await response.text())||response.status));
      }catch(error){errors.push(payload.name+': '+(error.message||String(error)));}
    }
    try{await Promise.all([loadResources(),loadResourceStatus()]);}catch(_){}
    scanButton.disabled=false;
    if(errors.length){status.textContent='Some connections could not be added: '+errors.join(' · ');addButton.disabled=false;return;}
    closeDialog();
  };
})();
</script>
'''
INDEX_HTML = INDEX_HTML.replace("</body>", DISCOVERY_JS + "\n</body>", 1)

for required in (
    "Discover host services",
    "api('api/discovery/host')",
    "Add selected",
    "extra_ports:extraPorts",
    "ssh_auth_mode:'prompt'",
    "resource_type:'smb'",
    "resource_type:'vnc'",
):
    if required not in INDEX_HTML:
        raise RuntimeError(f"Host discovery UI composition failed: missing {required}")
