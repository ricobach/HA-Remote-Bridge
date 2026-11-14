"""SSH Tab and arrow controls for mobile terminals."""

from dashboard_ssh_clipboard import INDEX_HTML as BASE_INDEX_HTML

INDEX_HTML = BASE_INDEX_HTML

KEYS_CSS = r'''
    .ssh-key-strip {
      display:flex;
      align-items:center;
      gap:4px;
      margin-left:2px;
    }
    .ssh-key-strip[hidden] { display:none !important; }
    .ssh-key-button {
      min-width:32px;
      padding-left:7px !important;
      padding-right:7px !important;
      font-weight:600;
      touch-action:manipulation;
      -webkit-user-select:none;
      user-select:none;
    }
    .ssh-key-tab { min-width:42px; font-size:10px; }
    @media(max-width:700px) {
      .ssh-key-strip { gap:3px; }
      .ssh-key-button { min-width:30px; padding-left:5px !important; padding-right:5px !important; }
      .ssh-key-tab { min-width:38px; }
    }
'''
INDEX_HTML = INDEX_HTML.replace("  </style>", KEYS_CSS + "\n  </style>", 1)

old_paste = '<button id="ssh-paste" class="icon-button ssh-paste-button" type="button" title="Paste clipboard into SSH terminal" hidden>📋</button>'
new_paste = old_paste + '''
      <div id="ssh-key-strip" class="ssh-key-strip" hidden>
        <button class="icon-button ssh-key-button ssh-key-tab" type="button" data-ssh-key="tab" title="Tab">Tab</button>
        <button class="icon-button ssh-key-button" type="button" data-ssh-key="left" title="Left">←</button>
        <button class="icon-button ssh-key-button" type="button" data-ssh-key="up" title="Up">↑</button>
        <button class="icon-button ssh-key-button" type="button" data-ssh-key="down" title="Down">↓</button>
        <button class="icon-button ssh-key-button" type="button" data-ssh-key="right" title="Right">→</button>
      </div>'''
if old_paste not in INDEX_HTML:
    raise RuntimeError("SSH key controls composition failed: paste button changed")
INDEX_HTML = INDEX_HTML.replace(old_paste, new_paste, 1)

KEYS_JS = r'''
<script>
(function installSSHNavigationKeys(){
  const strip=document.getElementById('ssh-key-strip');
  if(!strip)return;

  function activeSSH(){
    try{
      const session=typeof currentSession==='function'?currentSession():null;
      return session&&session.resource&&session.resource.resource_type==='ssh'?session:null;
    }catch(_){return null;}
  }

  async function sendKey(key,button){
    const session=activeSSH();
    if(!session)return;
    button.disabled=true;
    try{
      const response=await fetch(
        api('api/ssh/sessions/'+encodeURIComponent(session.resource.id)+'/key'),
        {
          method:'POST',
          headers:{'Content-Type':'application/json'},
          body:JSON.stringify({key})
        }
      );
      if(!response.ok)throw new Error(await response.text()||'Key send failed');
      try{session.frame.contentWindow.focus();}catch(_){}
    }catch(err){
      alert('Unable to send key: '+(err&&err.message?err.message:String(err)));
    }finally{
      button.disabled=false;
    }
  }

  for(const button of strip.querySelectorAll('[data-ssh-key]')){
    button.addEventListener('click',()=>sendKey(button.dataset.sshKey,button));
  }

  const sync=()=>{strip.hidden=!activeSSH();};
  setInterval(sync,250);
  sync();
})();
</script>
'''
INDEX_HTML = INDEX_HTML.replace("</body>", KEYS_JS + "\n</body>", 1)

for required in (
    'id="ssh-key-strip"',
    'data-ssh-key="tab"',
    'data-ssh-key="left"',
    'data-ssh-key="up"',
    'data-ssh-key="down"',
    'data-ssh-key="right"',
    "/key",
):
    if required not in INDEX_HTML:
        raise RuntimeError(f"SSH key controls composition failed: missing {required}")
