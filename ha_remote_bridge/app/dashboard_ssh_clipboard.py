"""Mobile-friendly SSH clipboard paste controls."""

from dashboard_ssh_terminal import INDEX_HTML as BASE_INDEX_HTML

INDEX_HTML = BASE_INDEX_HTML

PASTE_CSS = r'''
    .ssh-paste-button[hidden] { display:none !important; }
    .ssh-paste-dialog { border:0; border-radius:10px; padding:0; width:min(92vw,520px); background:var(--surface); color:var(--text); box-shadow:0 12px 38px rgba(0,0,0,.32); }
    .ssh-paste-dialog::backdrop { background:rgba(0,0,0,.45); }
    .ssh-paste-wrap { display:grid; gap:10px; padding:14px; }
    .ssh-paste-wrap h3 { margin:0; font-size:15px; }
    .ssh-paste-wrap p { margin:0; color:var(--muted); font-size:12px; line-height:1.4; }
    .ssh-paste-wrap textarea { width:100%; min-height:130px; resize:vertical; border:1px solid var(--border); border-radius:7px; padding:9px; background:var(--surface); color:var(--text); font:13px ui-monospace,SFMono-Regular,Menlo,Consolas,monospace; }
    .ssh-paste-actions { display:flex; justify-content:flex-end; gap:8px; }
'''
INDEX_HTML = INDEX_HTML.replace("  </style>", PASTE_CSS + "\n  </style>", 1)

old_reload = '<button id="reload" class="icon-button" type="button" title="Reload" disabled>↻</button>'
new_reload = old_reload + '\n      <button id="ssh-paste" class="icon-button ssh-paste-button" type="button" title="Paste clipboard into SSH terminal" hidden>📋</button>'
if old_reload not in INDEX_HTML:
    raise RuntimeError("SSH clipboard composition failed: navigation toolbar changed")
INDEX_HTML = INDEX_HTML.replace(old_reload, new_reload, 1)

PASTE_JS = r'''
<script>
(function installSSHClipboardPaste(){
  const button=document.getElementById('ssh-paste');
  if(!button)return;

  const dialog=document.createElement('dialog');
  dialog.id='ssh-paste-dialog';
  dialog.className='ssh-paste-dialog';
  dialog.innerHTML=
    '<div class="ssh-paste-wrap">'+
      '<h3>Paste into SSH terminal</h3>'+
      '<p>Clipboard access is restricted by some iPhone/Home Assistant browser contexts. If direct paste is unavailable, tap and hold in the box, choose Paste, then tap Paste to terminal.</p>'+
      '<textarea id="ssh-paste-text" autocomplete="off" autocapitalize="off" spellcheck="false" placeholder="Tap and hold here, then choose Paste"></textarea>'+
      '<div class="ssh-paste-actions"><button id="ssh-paste-cancel" type="button">Cancel</button><button id="ssh-paste-send" type="button">Paste to terminal</button></div>'+
    '</div>';
  document.body.appendChild(dialog);

  const textarea=document.getElementById('ssh-paste-text');
  const cancel=document.getElementById('ssh-paste-cancel');
  const send=document.getElementById('ssh-paste-send');

  function activeSSH(){
    try{
      const session=typeof currentSession==='function'?currentSession():null;
      return session&&session.resource&&session.resource.resource_type==='ssh'?session:null;
    }catch(_){return null;}
  }

  async function sendText(text){
    const session=activeSSH();
    if(!session)throw new Error('No active SSH session');
    if(!text)return;
    const response=await fetch(api('api/ssh/sessions/'+encodeURIComponent(session.resource.id)+'/paste'),{
      method:'POST',
      headers:{'Content-Type':'application/json'},
      body:JSON.stringify({text})
    });
    if(!response.ok)throw new Error(await response.text()||'Paste failed');
    try{session.frame.contentWindow.focus();}catch(_){}
  }

  function openFallback(){
    textarea.value='';
    if(typeof dialog.showModal==='function')dialog.showModal();
    else dialog.setAttribute('open','');
    setTimeout(()=>textarea.focus(),60);
  }

  button.addEventListener('click',async()=>{
    button.disabled=true;
    try{
      if(navigator.clipboard&&typeof navigator.clipboard.readText==='function'&&window.isSecureContext){
        const text=await navigator.clipboard.readText();
        if(text){
          await sendText(text);
          return;
        }
      }
      openFallback();
    }catch(_){
      openFallback();
    }finally{
      button.disabled=false;
    }
  });

  cancel.addEventListener('click',()=>{
    if(typeof dialog.close==='function')dialog.close();
    else dialog.removeAttribute('open');
  });

  send.addEventListener('click',async()=>{
    send.disabled=true;
    try{
      await sendText(textarea.value);
      if(typeof dialog.close==='function')dialog.close();
      else dialog.removeAttribute('open');
      textarea.value='';
    }catch(err){
      alert('Unable to paste: '+(err&&err.message?err.message:String(err)));
    }finally{
      send.disabled=false;
    }
  });

  // Keep the control visible only while an SSH session is active. This also
  // follows restored tabs and mobile tab switching without changing old UI code.
  const sync=()=>{button.hidden=!activeSSH();};
  setInterval(sync,250);
  sync();
})();
</script>
'''
INDEX_HTML = INDEX_HTML.replace("</body>", PASTE_JS + "\n</body>", 1)

for required in (
    'id="ssh-paste"',
    "navigator.clipboard.readText",
    "/paste",
    "Paste to terminal",
    "Tap and hold here",
):
    if required not in INDEX_HTML:
        raise RuntimeError(f"SSH clipboard UI composition failed: missing {required}")
