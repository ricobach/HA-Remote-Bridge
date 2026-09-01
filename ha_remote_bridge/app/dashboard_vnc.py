"""VNC UI extensions for HA Remote Bridge."""

from ui_shell_v9 import INDEX_HTML as BASE_INDEX_HTML

INDEX_HTML = BASE_INDEX_HTML

INDEX_HTML = INDEX_HTML.replace(
    '<button id="add-ssh" class="tool-button" type="button">⌨ Add SSH</button>',
    '<button id="add-ssh" class="tool-button" type="button">⌨ Add SSH</button>\n'
    '          <button id="add-vnc" class="tool-button" type="button">▣ Add VNC</button>',
)
INDEX_HTML = INDEX_HTML.replace(
    '<option value="ssh">SSH</option>',
    '<option value="ssh">SSH</option><option value="vnc">VNC</option>',
)

INDEX_HTML = INDEX_HTML.replace(
    "function resourceKind(r){if(r.resource_type==='ssh'||String(r.url||'').startsWith('ssh:'))return'ssh';if(r.resource_type==='esphome'||r.profile==='esphome')return'esphome';try{return new URL(r.url).protocol==='https:'?'https':'http';}catch(_){return'http';}}",
    "function resourceKind(r){if(r.resource_type==='vnc'||String(r.url||'').startsWith('vnc:'))return'vnc';if(r.resource_type==='ssh'||String(r.url||'').startsWith('ssh:'))return'ssh';if(r.resource_type==='esphome'||r.profile==='esphome')return'esphome';try{return new URL(r.url).protocol==='https:'?'https':'http';}catch(_){return'http';}}",
)
INDEX_HTML = INDEX_HTML.replace(
    "function sessionUrl(resource){return resourceKind(resource)==='ssh'?api('ssh/'+resource.id+'/'):api('proxy/'+resource.id+'/');}",
    "function sessionUrl(resource){const kind=resourceKind(resource);return kind==='ssh'?api('ssh/'+resource.id+'/'):kind==='vnc'?api('vnc/'+resource.id+'/'):api('proxy/'+resource.id+'/');}",
)

INDEX_HTML = INDEX_HTML.replace(
    "    if(resourceKind(r)==='ssh')return String(r.ssh_host||'').replace(/^\\[|\\]$/g,'');",
    "    if(resourceKind(r)==='vnc')return String(r.vnc_host||'').replace(/^\\[|\\]$/g,'');\n    if(resourceKind(r)==='ssh')return String(r.ssh_host||'').replace(/^\\[|\\]$/g,'');",
)
INDEX_HTML = INDEX_HTML.replace(
    "    if(resourceKind(r)==='ssh')return Number(r.ssh_port||22);",
    "    if(resourceKind(r)==='vnc')return Number(r.vnc_port||5900);\n    if(resourceKind(r)==='ssh')return Number(r.ssh_port||22);",
)
INDEX_HTML = INDEX_HTML.replace(
    "function connectionMeta(r){const kind=resourceKind(r);const port=resourcePort(r);if(kind==='ssh')return 'SSH'+(port?(' :'+port):'')+' · '+String(r.ssh_user||'')+'@'+resourceHost(r);try{const u=new URL(r.url);return kind.toUpperCase()+(port?(' :'+port):'')+(u.pathname&&u.pathname!=='/'?(' · '+u.pathname):'');}catch(_){return r.url;}}",
    "function connectionMeta(r){const kind=resourceKind(r);const port=resourcePort(r);if(kind==='vnc')return 'VNC'+(port?(' :'+port):'')+' · '+resourceHost(r)+(r.vnc_view_only?' · view only':'');if(kind==='ssh')return 'SSH'+(port?(' :'+port):'')+' · '+String(r.ssh_user||'')+'@'+resourceHost(r);try{const u=new URL(r.url);return kind.toUpperCase()+(port?(' :'+port):'')+(u.pathname&&u.pathname!=='/'?(' · '+u.pathname):'');}catch(_){return r.url;}}",
)
INDEX_HTML = INDEX_HTML.replace(
    "edit.onclick=()=>resourceKind(r)==='ssh'?showSSHResource(r):showEdit(r);",
    "edit.onclick=()=>resourceKind(r)==='ssh'?showSSHResource(r):resourceKind(r)==='vnc'?showVNCResource(r):showEdit(r);",
)

VNC_DIALOG = r'''
<dialog id="vnc-dialog">
  <div class="dialog-body">
    <div class="dialog-head"><h2 id="vnc-dialog-title">Add VNC connection</h2><div class="dialog-head-spacer"></div><button id="vnc-close" class="icon-button" type="button">×</button></div>
    <form id="vnc-form" class="edit-form">
      <input id="vnc-edit-id" type="hidden">
      <div class="two-column">
        <label>Session Name<input id="vnc-name" type="text" required placeholder="Santos Desktop"></label>
        <label>Group / Host<input id="vnc-group-name" type="text" placeholder="Optional, e.g. Santos"></label>
      </div>
      <div class="ssh-host-row">
        <label>Host / IP<input id="vnc-host" type="text" required placeholder="192.168.1.1"></label>
        <label>Port<input id="vnc-port" type="number" min="1" max="65535" value="5900" required></label>
      </div>
      <label class="checkbox-row"><input id="vnc-view-only" type="checkbox"> View only — disable keyboard and mouse input</label>
      <div class="ssh-security-note"><span>🖥️</span><div><strong>VNC authentication</strong><br>If the server requires a password, noVNC asks for it when the session opens. The password is not stored by HA Remote Bridge.</div></div>
      <div class="dialog-actions ssh-dialog-actions"><button id="vnc-cancel" class="tool-button" type="button">Cancel</button><button class="tool-button primary" type="submit">Save</button></div>
    </form>
  </div>
</dialog>
'''
INDEX_HTML = INDEX_HTML.replace('<dialog id="edit-dialog">', VNC_DIALOG + '\n<dialog id="edit-dialog">')

VNC_JS = r'''
  function showVNCResource(r){
    $('vnc-edit-id').value=r?r.id:'';
    $('vnc-dialog-title').textContent=r?'Edit VNC connection':'Add VNC connection';
    $('vnc-name').value=r?r.name:'';
    $('vnc-group-name').value=r?(r.group_name||''):'';
    $('vnc-host').value=r?(r.vnc_host||''):'';
    $('vnc-port').value=r?(r.vnc_port||5900):5900;
    $('vnc-view-only').checked=!!(r&&r.vnc_view_only);
    $('vnc-dialog').showModal();
  }
  function closeVNC(){if($('vnc-dialog').open)$('vnc-dialog').close();}
  $('vnc-form').addEventListener('submit',async e=>{
    e.preventDefault();
    const id=$('vnc-edit-id').value;
    const payload={resource_type:'vnc',name:$('vnc-name').value,group_name:$('vnc-group-name').value,vnc_host:$('vnc-host').value,vnc_port:Number($('vnc-port').value||5900),vnc_view_only:$('vnc-view-only').checked};
    const endpoint=id?api('api/resources/'+id):api('api/resources');
    const res=await fetch(endpoint,{method:id?'PUT':'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)});
    if(!res.ok){alert(await res.text());return;}
    const updated=await res.json();const s=id?sessions.get(id):null;
    if(s){s.resource=updated;s.label.textContent=updated.name;s.tab.title=updated.name;s.frame.title=updated.name;s.frame.src=sessionUrl(updated);}
    closeVNC();await Promise.all([loadResources(),loadResourceStatus()]);
  });
  $('add-vnc').addEventListener('click',()=>showVNCResource(null));
  $('vnc-close').addEventListener('click',closeVNC);
  $('vnc-cancel').addEventListener('click',closeVNC);
'''
INDEX_HTML = INDEX_HTML.replace("  function showEdit(r){", VNC_JS + "\n  function showEdit(r){", 1)

for required in (
    'id="add-vnc"',
    'id="vnc-dialog"',
    "resource_type:'vnc'",
    "kind==='vnc'?api('vnc/'",
    "resourceKind(r)==='vnc'",
):
    if required not in INDEX_HTML:
        raise RuntimeError(f"VNC UI composition failed: missing {required}")
