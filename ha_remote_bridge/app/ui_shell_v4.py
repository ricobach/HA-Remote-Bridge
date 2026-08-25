"""SSH UI extensions for the HA/ESPHome-style dashboard."""

from ui_shell_v3 import INDEX_HTML as BASE_INDEX_HTML

INDEX_HTML = BASE_INDEX_HTML

# SSH-specific styling.
INDEX_HTML = INDEX_HTML.replace(
    "    .status-chip.discovered { color:#0b70b7; background:#e1f3ff; }",
    "    .status-chip.discovered { color:#0b70b7; background:#e1f3ff; }\n"
    "    .ssh-note { font-size:11px; color:var(--muted); line-height:1.45; }\n"
    "    textarea { width:100%; min-height:150px; resize:vertical; padding:8px 9px; border:1px solid var(--border); border-radius:4px; background:var(--surface); color:var(--text); font:12px ui-monospace,SFMono-Regular,Consolas,monospace; }\n"
    "    .key-list { display:grid; gap:8px; margin:12px 0; }\n"
    "    .key-row { display:grid; grid-template-columns:minmax(0,1fr) auto; gap:10px; align-items:center; padding:10px; border:1px solid var(--border); border-radius:6px; }\n"
    "    .key-name { font-weight:600; font-size:13px; }\n"
    "    .key-meta { font-size:10px; color:var(--muted); overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }\n"
    "    .key-actions { display:flex; gap:5px; flex-wrap:wrap; justify-content:flex-end; }\n"
    "    .two-column { display:grid; grid-template-columns:1fr 1fr; gap:10px; }",
)
INDEX_HTML = INDEX_HTML.replace(
    "      .resource-form { grid-template-columns:1fr; }",
    "      .resource-form,.two-column { grid-template-columns:1fr; }",
)

# Add SSH controls to the toolbar and SSH to resource filtering.
INDEX_HTML = INDEX_HTML.replace(
    '<button id="refresh-all" class="tool-button" type="button">↻ Refresh</button>\n          <button id="toggle-add" class="tool-button primary" type="button">＋ Add resource</button>',
    '<button id="refresh-all" class="tool-button" type="button">↻ Refresh</button>\n'
    '          <button id="ssh-keys" class="tool-button" type="button">🔑 SSH keys</button>\n'
    '          <button id="add-ssh" class="tool-button" type="button">⌨ Add SSH</button>\n'
    '          <button id="toggle-add" class="tool-button primary" type="button">＋ Add web</button>',
)
INDEX_HTML = INDEX_HTML.replace(
    '<option value="esphome">ESPHome</option><option value="https">HTTPS</option><option value="http">HTTP</option>',
    '<option value="esphome">ESPHome</option><option value="ssh">SSH</option><option value="https">HTTPS</option><option value="http">HTTP</option>',
)

# Add SSH resource and shared-key dialogs.
SSH_DIALOGS = r'''
<dialog id="ssh-dialog">
  <div class="dialog-body">
    <div class="dialog-head"><h2 id="ssh-dialog-title">Add SSH resource</h2><div class="dialog-head-spacer"></div><button id="ssh-close" class="icon-button" type="button">×</button></div>
    <form id="ssh-form" class="edit-form">
      <input id="ssh-edit-id" type="hidden">
      <label>Name<input id="ssh-name" type="text" required placeholder="Server"></label>
      <div class="two-column">
        <label>Host / IP<input id="ssh-host" type="text" required placeholder="192.168.1.20"></label>
        <label>Port<input id="ssh-port" type="number" min="1" max="65535" value="22" required></label>
      </div>
      <div class="two-column">
        <label>Username<input id="ssh-user" type="text" required placeholder="root"></label>
        <label>SSH credential<select id="ssh-credential"><option value="">None — prompt for password/key</option></select></label>
      </div>
      <div class="ssh-note">Saved keys are reusable across SSH resources. Encrypted private keys are supported; OpenSSH will ask for the key passphrase in the terminal when the session starts. Host keys use persistent <code>accept-new</code> verification.</div>
      <div class="dialog-actions"><button id="ssh-cancel" class="tool-button" type="button">Cancel</button><button class="tool-button primary" type="submit">Save</button></div>
    </form>
  </div>
</dialog>

<dialog id="ssh-keys-dialog">
  <div class="dialog-body">
    <div class="dialog-head"><h2>SSH credential vault</h2><div class="dialog-head-spacer"></div><button id="ssh-keys-close" class="icon-button" type="button">×</button></div>
    <div class="ssh-note">Private keys are stored only inside this App under <code>/data/ssh/keys</code> with restrictive permissions. They are not stored in resource definitions and are never returned by the API.</div>
    <div id="ssh-key-list" class="key-list"></div>
    <form id="generate-key-form" class="edit-form">
      <div class="two-column">
        <label>New generated key name<input id="generate-key-name" type="text" placeholder="Home servers"></label>
        <div style="display:flex;align-items:end"><button class="tool-button primary" type="submit">Generate ED25519 key</button></div>
      </div>
    </form>
    <hr style="border:0;border-top:1px solid var(--border);margin:16px 0">
    <form id="import-key-form" class="edit-form">
      <label>Imported key name<input id="import-key-name" type="text" placeholder="Existing admin key"></label>
      <label>Private key<textarea id="import-private-key" placeholder="-----BEGIN OPENSSH PRIVATE KEY-----"></textarea></label>
      <div class="dialog-actions"><button class="tool-button primary" type="submit">Save private key</button></div>
    </form>
  </div>
</dialog>
'''
INDEX_HTML = INDEX_HTML.replace('<dialog id="edit-dialog">', SSH_DIALOGS + '\n<dialog id="edit-dialog">')

# Data and URL helpers.
INDEX_HTML = INDEX_HTML.replace(
    "  let resourceStatus = {};\n  let viewMode = 'grid';",
    "  let resourceStatus = {};\n  let sshCredentials = [];\n  let viewMode = 'grid';",
)
INDEX_HTML = INDEX_HTML.replace(
    "  function openSession(resource){",
    "  function sessionUrl(resource){return resourceKind(resource)==='ssh'?api('ssh/'+resource.id+'/'):api('proxy/'+resource.id+'/');}\n"
    "  function openSession(resource){",
)
INDEX_HTML = INDEX_HTML.replace("frame.src=api('proxy/'+resource.id+'/');", "frame.src=sessionUrl(resource);")
INDEX_HTML = INDEX_HTML.replace(
    "function resourceKind(r){if(r.resource_type==='esphome'||r.profile==='esphome')return'esphome';try{return new URL(r.url).protocol==='https:'?'https':'http';}catch(_){return'http';}}",
    "function resourceKind(r){if(r.resource_type==='ssh'||String(r.url||'').startsWith('ssh:'))return'ssh';if(r.resource_type==='esphome'||r.profile==='esphome')return'esphome';try{return new URL(r.url).protocol==='https:'?'https':'http';}catch(_){return'http';}}\n"
    "  function credentialName(id){const c=sshCredentials.find(x=>x.id===id);return c?c.name:(id?'Unknown key':'Password / prompt');}",
)

# Render SSH metadata and route Edit to the SSH dialog.
INDEX_HTML = INDEX_HTML.replace(
    "const details=document.createElement('div');details.className='device-details';details.textContent='TLS verification: '+(r.verify_ssl===false?'off':'on');",
    "const details=document.createElement('div');details.className='device-details';details.textContent=resourceKind(r)==='ssh'?('Credential: '+credentialName(r.ssh_credential_id)):'TLS verification: '+(r.verify_ssl===false?'off':'on');",
)
INDEX_HTML = INDEX_HTML.replace(
    "edit.onclick=()=>showEdit(r);",
    "edit.onclick=()=>resourceKind(r)==='ssh'?showSSHResource(r):showEdit(r);",
)
INDEX_HTML = INDEX_HTML.replace(
    "s.frame.src=api('proxy/'+id+'/');",
    "s.frame.src=sessionUrl(updated);",
)

# SSH key vault and SSH resource JavaScript.
SSH_JS = r'''
  async function loadSSHCredentials(){
    try{
      const res=await fetch(api('api/ssh/credentials'),{cache:'no-store'});
      if(!res.ok)throw new Error(await res.text());
      sshCredentials=await res.json();
      populateSSHCredentialSelect();
      renderSSHKeyVault();
      renderResources();
    }catch(e){console.warn('Unable to load SSH credentials',e);}
  }
  function populateSSHCredentialSelect(){
    const sel=$('ssh-credential');if(!sel)return;const current=sel.value;sel.innerHTML='<option value="">None — prompt for password/key</option>';
    for(const c of sshCredentials){const o=document.createElement('option');o.value=c.id;o.textContent=c.name+(c.fingerprint?' · '+c.fingerprint:'');sel.append(o);}sel.value=current;
  }
  function showSSHResource(r){
    $('ssh-edit-id').value=r?r.id:'';$('ssh-dialog-title').textContent=r?'Edit SSH resource':'Add SSH resource';
    $('ssh-name').value=r?r.name:'';$('ssh-host').value=r?(r.ssh_host||''):'';$('ssh-port').value=r?(r.ssh_port||22):22;$('ssh-user').value=r?(r.ssh_user||''):'';
    populateSSHCredentialSelect();$('ssh-credential').value=r?(r.ssh_credential_id||''):'';$('ssh-dialog').showModal();
  }
  function closeSSH(){if($('ssh-dialog').open)$('ssh-dialog').close();}
  $('ssh-form').addEventListener('submit',async e=>{
    e.preventDefault();const id=$('ssh-edit-id').value;const payload={resource_type:'ssh',name:$('ssh-name').value,ssh_host:$('ssh-host').value,ssh_port:Number($('ssh-port').value||22),ssh_user:$('ssh-user').value,ssh_credential_id:$('ssh-credential').value};
    const endpoint=id?api('api/resources/'+id):api('api/resources');const res=await fetch(endpoint,{method:id?'PUT':'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)});if(!res.ok){alert(await res.text());return;}const updated=await res.json();
    const s=id?sessions.get(id):null;if(s){s.resource=updated;s.label.textContent=updated.name;s.tab.title=updated.name;s.frame.title=updated.name;s.frame.src=sessionUrl(updated);}closeSSH();await Promise.all([loadResources(),loadResourceStatus()]);
  });
  $('add-ssh').addEventListener('click',()=>showSSHResource(null));$('ssh-close').addEventListener('click',closeSSH);$('ssh-cancel').addEventListener('click',closeSSH);

  function renderSSHKeyVault(){
    const host=$('ssh-key-list');if(!host)return;host.innerHTML='';if(!sshCredentials.length){host.innerHTML='<div class="empty">No reusable SSH keys saved yet.</div>';return;}
    for(const c of sshCredentials){const row=document.createElement('div');row.className='key-row';const info=document.createElement('div');const n=document.createElement('div');n.className='key-name';n.textContent=c.name;const m=document.createElement('div');m.className='key-meta';m.textContent=[c.kind,c.fingerprint].filter(Boolean).join(' · ');info.append(n,m);const actions=document.createElement('div');actions.className='key-actions';
      if(c.public_key){const copy=document.createElement('button');copy.className='mini-button';copy.type='button';copy.textContent='Copy public key';copy.onclick=async()=>{await navigator.clipboard.writeText(c.public_key);copy.textContent='Copied';setTimeout(()=>copy.textContent='Copy public key',1200);};actions.append(copy);}
      const del=document.createElement('button');del.className='mini-button danger';del.type='button';del.textContent='Delete';del.onclick=async()=>{if(!confirm('Delete SSH key '+c.name+'?'))return;const res=await fetch(api('api/ssh/credentials/'+c.id),{method:'DELETE'});if(!res.ok){alert(await res.text());return;}await loadSSHCredentials();};actions.append(del);row.append(info,actions);host.append(row);}
  }
  $('ssh-keys').addEventListener('click',async()=>{await loadSSHCredentials();$('ssh-keys-dialog').showModal();});
  $('ssh-keys-close').addEventListener('click',()=>$('ssh-keys-dialog').close());
  $('generate-key-form').addEventListener('submit',async e=>{e.preventDefault();const name=$('generate-key-name').value.trim();if(!name)return;const res=await fetch(api('api/ssh/credentials/generate'),{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({name})});if(!res.ok){alert(await res.text());return;}$('generate-key-name').value='';await loadSSHCredentials();});
  $('import-key-form').addEventListener('submit',async e=>{e.preventDefault();const name=$('import-key-name').value.trim(),private_key=$('import-private-key').value;if(!name||!private_key)return;const res=await fetch(api('api/ssh/credentials'),{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({name,private_key})});if(!res.ok){alert(await res.text());return;}$('import-key-name').value='';$('import-private-key').value='';await loadSSHCredentials();});
'''
INDEX_HTML = INDEX_HTML.replace("  function showEdit(r){", SSH_JS + "\n  function showEdit(r){")

# Load key metadata with the dashboard; private key material never comes back to the browser.
INDEX_HTML = INDEX_HTML.replace(
    "  loadResources();loadDiscoveredESPHome();loadResourceStatus();setGridClass();",
    "  loadSSHCredentials();loadResources();loadDiscoveredESPHome();loadResourceStatus();setGridClass();",
)
