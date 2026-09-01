"""Per-connection SSH password authentication UI for HA Remote Bridge 0.5.0."""

from ui_shell_v18 import INDEX_HTML as BASE_INDEX_HTML

INDEX_HTML = BASE_INDEX_HTML

PASSWORD_AUTH_CSS = r'''
    /* 0.5.0: explicit per-connection SSH authentication selection. */
    .ssh-auth-detail {
      display:grid;
      gap:8px;
      padding:9px 10px;
      border:1px solid var(--border);
      border-radius:7px;
      background:color-mix(in srgb,var(--surface) 97%,var(--text) 3%);
    }
    .ssh-auth-detail[hidden] { display:none !important; }
    .ssh-password-state {
      min-height:16px;
      color:var(--muted);
      font-size:10px;
      line-height:1.4;
    }
    .ssh-password-state.saved { color:#218c4c; }
    #ssh-password { width:100%; }
'''
INDEX_HTML = INDEX_HTML.replace("  </style>", PASSWORD_AUTH_CSS + "\n  </style>", 1)

PASSWORD_AUTH_JS = r'''
<script>
(function installSSHPasswordAuthenticationUI(){
  const form=document.getElementById('ssh-form');
  const user=document.getElementById('ssh-user');
  const credential=document.getElementById('ssh-credential');
  const summary=document.getElementById('ssh-credential-summary');
  if(!form||!user||!credential)return;

  const authRow=user.closest('.ssh-auth-row')||user.closest('.two-column');
  const credentialLabel=credential.closest('label');
  if(!authRow||!credentialLabel)return;

  credentialLabel.remove();
  const authLabel=document.createElement('label');
  authLabel.textContent='Authentication';
  const auth=document.createElement('select');
  auth.id='ssh-auth-mode';
  for(const [value,label] of [
    ['prompt','Prompt in terminal'],
    ['key','SSH key'],
    ['password','Saved password']
  ]){
    const option=document.createElement('option');
    option.value=value;option.textContent=label;auth.appendChild(option);
  }
  authLabel.appendChild(auth);
  authRow.appendChild(authLabel);

  credentialLabel.firstChild.textContent='SSH key';
  const keyBlock=document.createElement('div');
  keyBlock.id='ssh-key-auth-block';
  keyBlock.className='ssh-auth-detail';
  keyBlock.appendChild(credentialLabel);
  if(summary)keyBlock.appendChild(summary);
  authRow.insertAdjacentElement('afterend',keyBlock);

  const passwordBlock=document.createElement('div');
  passwordBlock.id='ssh-password-auth-block';
  passwordBlock.className='ssh-auth-detail';
  const passwordLabel=document.createElement('label');
  passwordLabel.textContent='Password';
  const password=document.createElement('input');
  password.id='ssh-password';
  password.type='password';
  password.autocomplete='current-password';
  password.placeholder='Enter password';
  passwordLabel.appendChild(password);
  const passwordState=document.createElement('div');
  passwordState.id='ssh-password-state';
  passwordState.className='ssh-password-state';
  passwordBlock.append(passwordLabel,passwordState);
  keyBlock.insertAdjacentElement('afterend',passwordBlock);

  const securityNote=form.querySelector('.ssh-security-note');
  if(securityNote){
    securityNote.innerHTML='<span>🔐</span><div><strong>Secure authentication</strong><br>SSH keys remain in the reusable key vault. Saved passwords are stored only for this connection under the App protected <code>/data/ssh/passwords</code> area and are never returned by the API.</div>';
  }

  let editingResource=null;
  function inferredMode(resource){
    const explicit=String(resource?.ssh_auth_mode||'').toLowerCase();
    if(['prompt','key','password'].includes(explicit))return explicit;
    return resource?.ssh_credential_id?'key':'prompt';
  }
  function updateAuthUI(){
    const mode=auth.value;
    keyBlock.hidden=mode!=='key';
    passwordBlock.hidden=mode!=='password';
    if(mode==='password'){
      const saved=Boolean(editingResource&&editingResource.ssh_has_password);
      password.placeholder=saved?'Leave blank to keep saved password':'Enter password';
      passwordState.textContent=saved?'Saved password configured — leave blank to keep it, or enter a new password to replace it.':'The password will be saved only for this SSH connection.';
      passwordState.classList.toggle('saved',saved);
    }else{
      passwordState.textContent='';
      passwordState.classList.remove('saved');
    }
  }
  auth.addEventListener('change',updateAuthUI);

  const originalShow=window.showSSHResource;
  if(typeof originalShow==='function'){
    window.showSSHResource=function(resource){
      editingResource=resource||null;
      originalShow(resource);
      auth.value=inferredMode(resource);
      password.value='';
      updateAuthUI();
    };
  }

  // Capture submit before the older SSH handler. The password is sent only when
  // the user enters/replaces it; an empty field while editing preserves the
  // existing saved password on the server.
  form.addEventListener('submit',async event=>{
    event.preventDefault();
    event.stopImmediatePropagation();

    const id=document.getElementById('ssh-edit-id').value;
    const mode=auth.value;
    const payload={
      resource_type:'ssh',
      name:document.getElementById('ssh-name').value,
      group_name:document.getElementById('ssh-group-name').value,
      ssh_host:document.getElementById('ssh-host').value,
      ssh_port:Number(document.getElementById('ssh-port').value||22),
      ssh_user:user.value,
      ssh_auth_mode:mode,
      ssh_credential_id:mode==='key'?credential.value:'',
      ssh_password:mode==='password'?password.value:''
    };

    const endpoint=id?api('api/resources/'+id):api('api/resources');
    const response=await fetch(endpoint,{
      method:id?'PUT':'POST',
      headers:{'Content-Type':'application/json'},
      body:JSON.stringify(payload)
    });
    if(!response.ok){alert(await response.text());return;}
    const updated=await response.json();
    const session=id?sessions.get(id):null;
    if(session){
      session.resource=updated;
      session.label.textContent=updated.name;
      session.tab.title=updated.name;
      session.frame.title=updated.name;
      session.frame.src=sessionUrl(updated);
    }
    editingResource=updated;
    password.value='';
    if(typeof closeSSH==='function')closeSSH();
    await Promise.all([loadResources(),loadResourceStatus()]);
  },true);

  updateAuthUI();
})();
</script>
'''
INDEX_HTML = INDEX_HTML.replace("</body>", PASSWORD_AUTH_JS + "\n</body>", 1)

for required in (
    "ssh-auth-mode",
    "Saved password",
    "ssh_password:mode==='password'?password.value:''",
    "/data/ssh/passwords",
    "stopImmediatePropagation",
):
    if required not in INDEX_HTML:
        raise RuntimeError(f"SSH password UI composition failed: missing {required}")
