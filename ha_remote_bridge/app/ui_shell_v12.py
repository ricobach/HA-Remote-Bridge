"""SMB credential diagnostics UI for HA Remote Bridge."""

from ui_shell_v11 import INDEX_HTML as BASE_INDEX_HTML

INDEX_HTML = BASE_INDEX_HTML

# Add a visible test result and a Test connection action to the SMB editor.
INDEX_HTML = INDEX_HTML.replace(
    '<div class="ssh-security-note"><span>🗄️</span><div><strong>Server-side SMB browser</strong><br>Credentials stay in the App vault. The browser never receives the saved password.</div></div>\n      <div class="dialog-actions ssh-dialog-actions"><button id="smb-cancel" class="tool-button" type="button">Cancel</button><button class="tool-button primary" type="submit">Save</button></div>',
    '<div class="ssh-security-note"><span>🗄️</span><div><strong>Server-side SMB browser</strong><br>Credentials stay in the App vault. The browser never receives the saved password.</div></div>\n'
    '      <div id="smb-test-result" class="credential-summary"></div>\n'
    '      <div class="dialog-actions ssh-dialog-actions"><button id="smb-test" class="tool-button" type="button">Test connection</button><div style="flex:1"></div><button id="smb-cancel" class="tool-button" type="button">Cancel</button><button class="tool-button primary" type="submit">Save</button></div>',
)

SMB_TEST_JS = r'''
  function clearSMBTestResult(){const box=$('smb-test-result');if(!box)return;box.classList.remove('visible');box.textContent='';}
  function showSMBTestResult(message,ok){const box=$('smb-test-result');if(!box)return;box.textContent=message;box.classList.add('visible');box.style.color=ok?'#218c4c':'#c62828';}
  async function testSMBConnection(){
    const button=$('smb-test');button.disabled=true;showSMBTestResult('Testing SMB connection…',true);
    try{
      const payload={smb_host:$('smb-host').value,smb_port:Number($('smb-port').value||445),smb_credential_id:$('smb-credential').value};
      const r=await fetch(api('api/smb/test'),{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload),cache:'no-store'});
      const type=(r.headers.get('content-type')||'').toLowerCase();
      let data=null;
      if(type.includes('application/json'))data=await r.json();
      else{const text=await r.text();throw new Error(text.slice(0,300)||('Connection test failed ('+r.status+')'));}
      if(!r.ok||!data.ok)throw new Error(data.error||('Connection test failed ('+r.status+')'));
      showSMBTestResult('Connected as '+data.identity+' · '+data.shares+' visible share'+(data.shares===1?'':'s'),true);
    }catch(e){showSMBTestResult(e.message||String(e),false);}
    finally{button.disabled=false;}
  }
  $('smb-test').addEventListener('click',testSMBConnection);
  $('smb-host').addEventListener('input',clearSMBTestResult);
  $('smb-port').addEventListener('input',clearSMBTestResult);
  $('smb-credential').addEventListener('change',clearSMBTestResult);
'''
INDEX_HTML = INDEX_HTML.replace(
    "  $('add-smb').addEventListener('click',()=>showSMBResource(null));",
    SMB_TEST_JS + "\n  $('add-smb').addEventListener('click',()=>showSMBResource(null));",
    1,
)

# Clear stale test output every time the editor opens.
INDEX_HTML = INDEX_HTML.replace(
    "updateSMBCredentialSummary();$('smb-dialog').showModal();",
    "updateSMBCredentialSummary();clearSMBTestResult();$('smb-dialog').showModal();",
    1,
)

for required in ('id="smb-test"', 'id="smb-test-result"', "api('api/smb/test')"):
    if required not in INDEX_HTML:
        raise RuntimeError(f"SMB test UI composition failed: missing {required}")
