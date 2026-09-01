"""SSH editor polish for HA Remote Bridge."""

from ui_shell_v7 import INDEX_HTML as BASE_INDEX_HTML

INDEX_HTML = BASE_INDEX_HTML

INDEX_HTML = INDEX_HTML.replace(
    "    dialog { width:min(540px,calc(100vw - 30px)); border:0; border-radius:8px; padding:0; background:var(--surface); color:var(--text); box-shadow:0 14px 50px #0005; }",
    "    dialog { width:min(540px,calc(100vw - 24px)); max-height:calc(100vh - 24px); border:0; border-radius:10px; padding:0; background:var(--surface); color:var(--text); box-shadow:0 14px 50px #0005; overflow:hidden; }\n"
    "    #ssh-dialog { width:min(640px,calc(100vw - 24px)); }\n"
    "    #ssh-dialog .dialog-body { max-height:calc(100vh - 24px); overflow-y:auto; overflow-x:hidden; }\n"
    "    #ssh-dialog .edit-form, #ssh-dialog label, #ssh-dialog input, #ssh-dialog select { min-width:0; }\n"
    "    #ssh-dialog input, #ssh-dialog select { width:100%; max-width:100%; }\n"
    "    .ssh-host-row { display:grid; grid-template-columns:minmax(0,1fr) 110px; gap:10px; }\n"
    "    .ssh-auth-row { display:grid; grid-template-columns:minmax(140px,.75fr) minmax(0,1.35fr); gap:10px; }\n"
    "    .credential-summary { display:none; padding:9px 10px; border:1px solid var(--border); border-radius:6px; background:var(--bg); font-size:10px; color:var(--muted); line-height:1.45; overflow-wrap:anywhere; }\n"
    "    .credential-summary.visible { display:block; }\n"
    "    .ssh-security-note { display:flex; gap:8px; align-items:flex-start; padding:9px 10px; border:1px solid var(--border); border-radius:6px; background:var(--bg); color:var(--muted); font-size:10px; line-height:1.45; }\n"
    "    .ssh-security-note strong { color:var(--text); font-weight:600; }\n"
    "    .ssh-dialog-actions { position:sticky; bottom:0; margin:8px -18px -18px; padding:12px 18px; border-top:1px solid var(--border); background:var(--surface); }",
)
INDEX_HTML = INDEX_HTML.replace(
    "      .resource-form,.two-column { grid-template-columns:1fr; }",
    "      .resource-form,.two-column,.ssh-host-row,.ssh-auth-row { grid-template-columns:1fr; }",
)

old_form = '''      <input id="ssh-edit-id" type="hidden">
      <label>Session Name<input id="ssh-name" type="text" required placeholder="Server"></label><label>Group / Host<input id="ssh-group-name" type="text" placeholder="Optional, e.g. Santos"></label>
      <div class="two-column">
        <label>Host / IP<input id="ssh-host" type="text" required placeholder="192.168.1.20"></label>
        <label>Port<input id="ssh-port" type="number" min="1" max="65535" value="22" required></label>
      </div>
      <div class="two-column">
        <label>Username<input id="ssh-user" type="text" required placeholder="root"></label>
        <label>SSH credential<select id="ssh-credential"><option value="">None — prompt for password/key</option></select></label>
      </div>
      <div class="ssh-note">Saved keys are reusable across SSH resources. Encrypted private keys are supported; OpenSSH will ask for the key passphrase in the terminal when the session starts. Host keys use persistent <code>accept-new</code> verification.</div>
      <div class="dialog-actions"><button id="ssh-cancel" class="tool-button" type="button">Cancel</button><button class="tool-button primary" type="submit">Save</button></div>'''

new_form = '''      <input id="ssh-edit-id" type="hidden">
      <div class="two-column">
        <label>Session Name<input id="ssh-name" type="text" required placeholder="Santos SSH"></label>
        <label>Group / Host<input id="ssh-group-name" type="text" placeholder="Optional, e.g. Santos"></label>
      </div>
      <div class="ssh-host-row">
        <label>Host / IP<input id="ssh-host" type="text" required placeholder="192.168.1.1"></label>
        <label>Port<input id="ssh-port" type="number" min="1" max="65535" value="22" required></label>
      </div>
      <div class="ssh-auth-row">
        <label>Username<input id="ssh-user" type="text" required placeholder="root"></label>
        <label>SSH credential<select id="ssh-credential"><option value="">Password / interactive prompt</option></select></label>
      </div>
      <div id="ssh-credential-summary" class="credential-summary"></div>
      <div class="ssh-security-note"><span>🔐</span><div><strong>Secure connection</strong><br>Reusable private keys stay in the App credential vault. Host keys are remembered with <code>accept-new</code> verification.</div></div>
      <div class="dialog-actions ssh-dialog-actions"><button id="ssh-cancel" class="tool-button" type="button">Cancel</button><button class="tool-button primary" type="submit">Save</button></div>'''

INDEX_HTML = INDEX_HTML.replace(old_form, new_form)

INDEX_HTML = INDEX_HTML.replace(
    "  function populateSSHCredentialSelect(){\n    const sel=$('ssh-credential');if(!sel)return;const current=sel.value;sel.innerHTML='<option value=\"\">None — prompt for password/key</option>';\n    for(const c of sshCredentials){const o=document.createElement('option');o.value=c.id;o.textContent=c.name+(c.fingerprint?' · '+c.fingerprint:'');sel.append(o);}sel.value=current;\n  }",
    "  function updateSSHCredentialSummary(){const box=$('ssh-credential-summary'),sel=$('ssh-credential');if(!box||!sel)return;const c=sshCredentials.find(x=>x.id===sel.value);if(!c){box.classList.remove('visible');box.textContent='';return;}box.textContent=[c.kind||'SSH key',c.fingerprint||'',c.public_key?'Public key available':''].filter(Boolean).join(' · ');box.classList.add('visible');}\n"
    "  function populateSSHCredentialSelect(){\n    const sel=$('ssh-credential');if(!sel)return;const current=sel.value;sel.innerHTML='<option value=\"\">Password / interactive prompt</option>';\n    for(const c of sshCredentials){const o=document.createElement('option');o.value=c.id;o.textContent=c.name;sel.append(o);}sel.value=current;updateSSHCredentialSummary();\n  }",
)
INDEX_HTML = INDEX_HTML.replace(
    "    populateSSHCredentialSelect();$('ssh-credential').value=r?(r.ssh_credential_id||''):'';$('ssh-dialog').showModal();",
    "    populateSSHCredentialSelect();$('ssh-credential').value=r?(r.ssh_credential_id||''):'';updateSSHCredentialSummary();$('ssh-dialog').showModal();",
)
INDEX_HTML = INDEX_HTML.replace(
    "  $('add-ssh').addEventListener('click',()=>showSSHResource(null));$('ssh-close').addEventListener('click',closeSSH);$('ssh-cancel').addEventListener('click',closeSSH);",
    "  $('ssh-credential').addEventListener('change',updateSSHCredentialSummary);\n  $('add-ssh').addEventListener('click',()=>showSSHResource(null));$('ssh-close').addEventListener('click',closeSSH);$('ssh-cancel').addEventListener('click',closeSSH);",
)
