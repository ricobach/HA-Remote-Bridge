"""SMB browser UI extensions for HA Remote Bridge."""

from ui_shell_v10 import INDEX_HTML as BASE_INDEX_HTML

INDEX_HTML = BASE_INDEX_HTML

INDEX_HTML = INDEX_HTML.replace(
    '<button id="add-vnc" class="tool-button" type="button">▣ Add VNC</button>',
    '<button id="add-vnc" class="tool-button" type="button">▣ Add VNC</button>\n'
    '          <button id="smb-credentials" class="tool-button" type="button">🔐 SMB credentials</button>\n'
    '          <button id="add-smb" class="tool-button" type="button">▤ Add SMB</button>',
)
INDEX_HTML = INDEX_HTML.replace(
    '<option value="ssh">SSH</option><option value="vnc">VNC</option>',
    '<option value="ssh">SSH</option><option value="vnc">VNC</option><option value="smb">SMB</option>',
)
INDEX_HTML = INDEX_HTML.replace(
    "function resourceKind(r){if(r.resource_type==='vnc'||String(r.url||'').startsWith('vnc:'))return'vnc';",
    "function resourceKind(r){if(r.resource_type==='smb'||String(r.url||'').startsWith('smb:'))return'smb';if(r.resource_type==='vnc'||String(r.url||'').startsWith('vnc:'))return'vnc';",
)
INDEX_HTML = INDEX_HTML.replace(
    "function sessionUrl(resource){const kind=resourceKind(resource);return kind==='ssh'?api('ssh/'+resource.id+'/'):kind==='vnc'?api('vnc/'+resource.id+'/'):api('proxy/'+resource.id+'/');}",
    "function sessionUrl(resource){const kind=resourceKind(resource);return kind==='ssh'?api('ssh/'+resource.id+'/'):kind==='vnc'?api('vnc/'+resource.id+'/'):kind==='smb'?api('smb/'+resource.id+'/'):api('proxy/'+resource.id+'/');}",
)
INDEX_HTML = INDEX_HTML.replace(
    "    if(resourceKind(r)==='vnc')return String(r.vnc_host||'').replace(/^\\[|\\]$/g,'');",
    "    if(resourceKind(r)==='smb')return String(r.smb_host||'').replace(/^\\[|\\]$/g,'');\n    if(resourceKind(r)==='vnc')return String(r.vnc_host||'').replace(/^\\[|\\]$/g,'');",
)
INDEX_HTML = INDEX_HTML.replace(
    "    if(resourceKind(r)==='vnc')return Number(r.vnc_port||5900);",
    "    if(resourceKind(r)==='smb')return Number(r.smb_port||445);\n    if(resourceKind(r)==='vnc')return Number(r.vnc_port||5900);",
)
INDEX_HTML = INDEX_HTML.replace(
    "function connectionMeta(r){const kind=resourceKind(r);const port=resourcePort(r);if(kind==='vnc')",
    "function connectionMeta(r){const kind=resourceKind(r);const port=resourcePort(r);if(kind==='smb')return 'SMB'+(port?(' :'+port):'')+' · '+resourceHost(r);if(kind==='vnc')",
)
INDEX_HTML = INDEX_HTML.replace(
    "edit.onclick=()=>resourceKind(r)==='ssh'?showSSHResource(r):resourceKind(r)==='vnc'?showVNCResource(r):showEdit(r);",
    "edit.onclick=()=>resourceKind(r)==='ssh'?showSSHResource(r):resourceKind(r)==='vnc'?showVNCResource(r):resourceKind(r)==='smb'?showSMBResource(r):showEdit(r);",
)

SMB_DIALOGS = r'''
<dialog id="smb-dialog">
  <div class="dialog-body">
    <div class="dialog-head"><h2 id="smb-dialog-title">Add SMB connection</h2><div class="dialog-head-spacer"></div><button id="smb-close" class="icon-button" type="button">×</button></div>
    <form id="smb-form" class="edit-form">
      <input id="smb-edit-id" type="hidden">
      <div class="two-column">
        <label>Session Name<input id="smb-name" type="text" required placeholder="Santos Files"></label>
        <label>Group / Host<input id="smb-group-name" type="text" placeholder="Optional, e.g. Santos"></label>
      </div>
      <div class="ssh-host-row">
        <label>Host / IP<input id="smb-host" type="text" required placeholder="192.168.1.10"></label>
        <label>Port<input id="smb-port" type="number" min="1" max="65535" value="445" required></label>
      </div>
      <label>SMB credential<select id="smb-credential"><option value="">Guest / anonymous</option></select></label>
      <div id="smb-credential-summary" class="credential-summary"></div>
      <div class="ssh-security-note"><span>🗄️</span><div><strong>Server-side SMB browser</strong><br>Credentials stay in the App vault. The browser never receives the saved password.</div></div>
      <div class="dialog-actions ssh-dialog-actions"><button id="smb-cancel" class="tool-button" type="button">Cancel</button><button class="tool-button primary" type="submit">Save</button></div>
    </form>
  </div>
</dialog>

<dialog id="smb-credentials-dialog">
  <div class="dialog-body">
    <div class="dialog-head"><h2>SMB credentials</h2><div class="dialog-head-spacer"></div><button id="smb-credentials-close" class="icon-button" type="button">×</button></div>
    <div id="smb-credential-list" class="key-list"></div>
    <form id="smb-credential-form" class="edit-form">
      <h3>Add reusable credential</h3>
      <div class="two-column">
        <label>Name<input id="smb-cred-name" type="text" required placeholder="NAS account"></label>
        <label>Domain / Workgroup<input id="smb-cred-domain" type="text" placeholder="Optional"></label>
      </div>
      <div class="two-column">
        <label>Username<input id="smb-cred-user" type="text" required autocomplete="username"></label>
        <label>Password<input id="smb-cred-password" type="password" autocomplete="new-password"></label>
      </div>
      <div class="ssh-security-note"><span>🔐</span><div><strong>Reusable secret</strong><br>The password is written only to the App's protected <code>/data/smb</code> vault and is omitted from API responses.</div></div>
      <div class="dialog-actions"><button id="smb-credentials-cancel" class="tool-button" type="button">Close</button><button class="tool-button primary" type="submit">Add credential</button></div>
    </form>
  </div>
</dialog>
'''
INDEX_HTML = INDEX_HTML.replace('<dialog id="vnc-dialog">', SMB_DIALOGS + '\n<dialog id="vnc-dialog">')

SMB_JS = r'''
  let smbCredentials=[];
  async function loadSMBCredentials(){
    const r=await fetch(api('api/smb/credentials'));if(!r.ok)throw new Error(await r.text());smbCredentials=await r.json();populateSMBCredentialSelect();renderSMBCredentials();
  }
  function populateSMBCredentialSelect(){
    const sel=$('smb-credential');if(!sel)return;const current=sel.value;sel.innerHTML='<option value="">Guest / anonymous</option>';
    for(const c of smbCredentials){const o=document.createElement('option');o.value=c.id;o.textContent=c.name;sel.append(o);}sel.value=current;updateSMBCredentialSummary();
  }
  function updateSMBCredentialSummary(){const box=$('smb-credential-summary'),sel=$('smb-credential');if(!box||!sel)return;const c=smbCredentials.find(x=>x.id===sel.value);if(!c){box.classList.remove('visible');box.textContent='';return;}box.textContent=(c.domain?(c.domain+'\\'):'')+c.username;box.classList.add('visible');}
  function renderSMBCredentials(){const host=$('smb-credential-list');if(!host)return;host.innerHTML='';if(!smbCredentials.length){host.innerHTML='<div class="empty">No saved SMB credentials.</div>';return;}for(const c of smbCredentials){const row=document.createElement('div');row.className='key-row';const info=document.createElement('div');info.className='key-info';const n=document.createElement('strong');n.textContent=c.name;const m=document.createElement('span');m.textContent=(c.domain?(c.domain+'\\'):'')+c.username;info.append(n,m);const del=document.createElement('button');del.className='mini-button danger';del.type='button';del.textContent='Delete';del.onclick=async()=>{if(!confirm('Delete SMB credential '+c.name+'?'))return;const r=await fetch(api('api/smb/credentials/'+c.id),{method:'DELETE'});if(!r.ok){alert(await r.text());return;}await loadSMBCredentials();};row.append(info,del);host.append(row);}}
  async function showSMBResource(r){
    await loadSMBCredentials();$('smb-edit-id').value=r?r.id:'';$('smb-dialog-title').textContent=r?'Edit SMB connection':'Add SMB connection';$('smb-name').value=r?r.name:'';$('smb-group-name').value=r?(r.group_name||''):'';$('smb-host').value=r?(r.smb_host||''):'';$('smb-port').value=r?(r.smb_port||445):445;$('smb-credential').value=r?(r.smb_credential_id||''):'';updateSMBCredentialSummary();$('smb-dialog').showModal();
  }
  function closeSMB(){if($('smb-dialog').open)$('smb-dialog').close();}
  $('smb-form').addEventListener('submit',async e=>{e.preventDefault();const id=$('smb-edit-id').value;const payload={resource_type:'smb',name:$('smb-name').value,group_name:$('smb-group-name').value,smb_host:$('smb-host').value,smb_port:Number($('smb-port').value||445),smb_credential_id:$('smb-credential').value};const endpoint=id?api('api/resources/'+id):api('api/resources');const res=await fetch(endpoint,{method:id?'PUT':'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)});if(!res.ok){alert(await res.text());return;}const updated=await res.json();const s=id?sessions.get(id):null;if(s){s.resource=updated;s.label.textContent=updated.name;s.tab.title=updated.name;s.frame.title=updated.name;s.frame.src=sessionUrl(updated);}closeSMB();await Promise.all([loadResources(),loadResourceStatus()]);});
  $('add-smb').addEventListener('click',()=>showSMBResource(null));$('smb-close').addEventListener('click',closeSMB);$('smb-cancel').addEventListener('click',closeSMB);$('smb-credential').addEventListener('change',updateSMBCredentialSummary);
  $('smb-credentials').addEventListener('click',async()=>{await loadSMBCredentials();$('smb-credentials-dialog').showModal();});
  function closeSMBCredentials(){if($('smb-credentials-dialog').open)$('smb-credentials-dialog').close();}
  $('smb-credentials-close').addEventListener('click',closeSMBCredentials);$('smb-credentials-cancel').addEventListener('click',closeSMBCredentials);
  $('smb-credential-form').addEventListener('submit',async e=>{e.preventDefault();const payload={name:$('smb-cred-name').value,domain:$('smb-cred-domain').value,username:$('smb-cred-user').value,password:$('smb-cred-password').value};const r=await fetch(api('api/smb/credentials'),{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)});if(!r.ok){alert(await r.text());return;}$('smb-credential-form').reset();await loadSMBCredentials();});
'''
INDEX_HTML = INDEX_HTML.replace("  function showVNCResource(r){", SMB_JS + "\n  function showVNCResource(r){", 1)

for required in (
    'id="add-smb"',
    'id="smb-dialog"',
    'id="smb-credentials-dialog"',
    "resource_type:'smb'",
    "kind==='smb'?api('smb/'",
    "resourceKind(r)==='smb'",
):
    if required not in INDEX_HTML:
        raise RuntimeError(f"SMB UI composition failed: missing {required}")
