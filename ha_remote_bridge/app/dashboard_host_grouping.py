"""Grouped host/connection UI for HA Remote Bridge."""

from __future__ import annotations

import re

from ui_shell_v5 import INDEX_HTML as BASE_INDEX_HTML

INDEX_HTML = BASE_INDEX_HTML

# Grouped host card styling. Individual endpoints keep their own status/actions.
INDEX_HTML = INDEX_HTML.replace(
    "    .device-actions { min-height:42px; display:flex; gap:6px; align-items:center; padding:7px 10px; border-top:1px solid var(--border); background:#fafafa; }",
    "    .device-actions { min-height:42px; display:flex; gap:6px; align-items:center; padding:7px 10px; border-top:1px solid var(--border); background:#fafafa; }\n"
    "    .connection-group-card { overflow:visible; }\n"
    "    .group-head { display:flex; align-items:center; gap:10px; padding:12px; border-bottom:1px solid var(--border); }\n"
    "    .group-title { min-width:0; flex:1; }\n"
    "    .group-name { font-size:14px; font-weight:600; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }\n"
    "    .group-host { margin-top:3px; color:var(--muted); font-size:10px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }\n"
    "    .group-count { color:var(--muted); font-size:10px; white-space:nowrap; }\n"
    "    .connection-row { display:grid; grid-template-columns:minmax(0,1fr) auto; align-items:center; gap:10px; padding:9px 10px; border-bottom:1px solid var(--border); }\n"
    "    .connection-row:last-child { border-bottom:0; }\n"
    "    .connection-info { min-width:0; }\n"
    "    .connection-name { font-size:12px; font-weight:600; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }\n"
    "    .connection-meta { margin-top:3px; color:var(--muted); font-size:10px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }\n"
    "    .connection-chips { display:flex; align-items:center; flex-wrap:wrap; gap:4px; margin-top:5px; }\n"
    "    .connection-actions { display:flex; gap:5px; align-items:center; flex-wrap:wrap; justify-content:flex-end; }",
)
INDEX_HTML = INDEX_HTML.replace(
    "      .device-grid.list .device-actions { border-left:0; border-top:1px solid var(--border); }",
    "      .device-grid.list .device-actions { border-left:0; border-top:1px solid var(--border); }\n"
    "      .connection-row { grid-template-columns:1fr; }\n"
    "      .connection-actions { justify-content:flex-start; }",
)

# Add a friendly group/host field to Web add/edit and SSH add/edit forms.
def _append_after_label(html: str, input_id: str, addition: str) -> str:
    pattern = rf'(<label>[^<]*<input id="{re.escape(input_id)}"[^>]*></label>)'
    return re.sub(pattern, rf'\1{addition}', html, count=1)

INDEX_HTML = _append_after_label(
    INDEX_HTML,
    "name",
    '<label>Group / Host<input id="group-name" type="text" placeholder="Optional, e.g. Santos"></label>',
)
INDEX_HTML = _append_after_label(
    INDEX_HTML,
    "edit-name",
    '<label>Group / Host<input id="edit-group-name" type="text" placeholder="Optional, e.g. Santos"></label>',
)
INDEX_HTML = _append_after_label(
    INDEX_HTML,
    "ssh-name",
    '<label>Group / Host<input id="ssh-group-name" type="text" placeholder="Optional, e.g. Santos"></label>',
)

# Persist group_name from all create/update flows.
INDEX_HTML = INDEX_HTML.replace(
    "JSON.stringify({name:$('name').value,url:$('url').value,verify_ssl:$('verify').checked})",
    "JSON.stringify({name:$('name').value,group_name:$('group-name').value,url:$('url').value,verify_ssl:$('verify').checked})",
)
INDEX_HTML = INDEX_HTML.replace(
    "JSON.stringify({name:$('edit-name').value,url:$('edit-url').value,verify_ssl:$('edit-verify').checked})",
    "JSON.stringify({name:$('edit-name').value,group_name:$('edit-group-name').value,url:$('edit-url').value,verify_ssl:$('edit-verify').checked})",
)
INDEX_HTML = INDEX_HTML.replace(
    "const payload={resource_type:'ssh',name:$('ssh-name').value,ssh_host:$('ssh-host').value",
    "const payload={resource_type:'ssh',name:$('ssh-name').value,group_name:$('ssh-group-name').value,ssh_host:$('ssh-host').value",
)
INDEX_HTML = INDEX_HTML.replace(
    "{name:d.name,url:d.url,verify_ssl:false,resource_type:'esphome',discovery_key:d.key||d.hostname}",
    "{name:d.name,group_name:d.name,url:d.url,verify_ssl:false,resource_type:'esphome',discovery_key:d.key||d.hostname}",
)

# Populate the group field when editing.
INDEX_HTML = INDEX_HTML.replace(
    "$('edit-name').value=r.name;$('edit-url').value=r.url;",
    "$('edit-name').value=r.name;$('edit-group-name').value=r.group_name||'';$('edit-url').value=r.url;",
)
INDEX_HTML = INDEX_HTML.replace(
    "$('ssh-name').value=r?r.name:'';$('ssh-host').value=r?(r.ssh_host||''):'';",
    "$('ssh-name').value=r?r.name:'';$('ssh-group-name').value=r?(r.group_name||''):'';$('ssh-host').value=r?(r.ssh_host||''):'';",
)

# Group helpers. Explicit group names win. Otherwise identical hostnames/IPs are
# grouped automatically, while a friendly resource name is used as the heading.
GROUP_HELPERS = r'''
  function resourceHost(r){
    if(resourceKind(r)==='ssh')return String(r.ssh_host||'').replace(/^\[|\]$/g,'');
    try{return new URL(r.url).hostname.replace(/^\[|\]$/g,'');}catch(_){return '';}
  }
  function resourcePort(r){
    if(resourceKind(r)==='ssh')return Number(r.ssh_port||22);
    try{const u=new URL(r.url);return Number(u.port||(u.protocol==='https:'?443:80));}catch(_){return null;}
  }
  function groupKey(r){const explicit=String(r.group_name||'').trim();if(explicit)return 'name:'+explicit.toLowerCase();const host=resourceHost(r);return host?'host:'+host.toLowerCase():'resource:'+r.id;}
  function connectionMeta(r){const kind=resourceKind(r);const port=resourcePort(r);if(kind==='ssh')return 'SSH'+(port?(' :'+port):'')+' · '+String(r.ssh_user||'')+'@'+resourceHost(r);try{const u=new URL(r.url);return kind.toUpperCase()+(port?(' :'+port):'')+(u.pathname&&u.pathname!=='/'?(' · '+u.pathname):'');}catch(_){return r.url;}}
'''
INDEX_HTML = INDEX_HTML.replace("  function renderResources(){", GROUP_HELPERS + "\n  function renderResources(){", 1)

# Replace configured-resource card rendering with host/group cards containing one or
# more independently actionable endpoints.
start = INDEX_HTML.index("  function renderResources(){")
end = INDEX_HTML.index("  async function restoreSessionTabs()", start)
NEW_RENDER = r'''  function renderResources(){
    const host=$('resources');host.innerHTML='';const visible=resourceData.filter(visibleResource);$('resource-count').textContent=visible.length+' of '+resourceData.length+' connections';
    if(!visible.length){host.innerHTML='<div class="empty">No configured connections match the current filters.</div>';setGridClass();return;}

    const grouped=new Map();
    for(const r of visible){const key=groupKey(r);if(!grouped.has(key))grouped.set(key,[]);grouped.get(key).push(r);}

    for(const [,items] of grouped){
      items.sort((a,b)=>{const ka=resourceKind(a),kb=resourceKind(b);if(ka!==kb)return ka.localeCompare(kb);return (resourcePort(a)||0)-(resourcePort(b)||0);});
      const first=items[0];const explicit=items.find(x=>String(x.group_name||'').trim());const titleText=explicit?explicit.group_name:first.name;const commonHost=resourceHost(first);
      const card=document.createElement('article');card.className='device-card connection-group-card';
      const head=document.createElement('div');head.className='group-head';const title=document.createElement('div');title.className='group-title';const name=document.createElement('div');name.className='group-name';name.textContent=titleText;const sub=document.createElement('div');sub.className='group-host';sub.textContent=commonHost||first.url;title.append(name,sub);const count=document.createElement('div');count.className='group-count';count.textContent=items.length+' connection'+(items.length===1?'':'s');head.append(title,count);card.append(head);

      for(const r of items){
        const row=document.createElement('div');row.className='connection-row';const info=document.createElement('div');info.className='connection-info';const n=document.createElement('div');n.className='connection-name';n.textContent=r.name;const meta=document.createElement('div');meta.className='connection-meta';meta.textContent=connectionMeta(r);const chips=document.createElement('div');chips.className='connection-chips';const health=resourceStatus[r.id];chips.append(health?makeChip(health.online?'Online':'Offline',health.online?'online':'offline'):makeChip('Checking…','unknown'));const type=document.createElement('span');type.className='type-chip';type.textContent=resourceKind(r)==='esphome'?'ESPHome':resourceKind(r).toUpperCase();chips.append(type);info.append(n,meta,chips);

        const actions=document.createElement('div');actions.className='connection-actions';const open=document.createElement('button');open.className='mini-button primary';open.type='button';open.textContent=sessions.has(r.id)?'Show':'Open';open.onclick=()=>openSession(r);const edit=document.createElement('button');edit.className='mini-button';edit.type='button';edit.textContent='Edit';edit.onclick=()=>resourceKind(r)==='ssh'?showSSHResource(r):showEdit(r);const remove=document.createElement('button');remove.className='mini-button danger';remove.type='button';remove.textContent='Delete';remove.onclick=async()=>{if(!confirm('Delete '+r.name+'?'))return;closeSession(r.id);await fetch(api('api/resources/'+r.id),{method:'DELETE'});await Promise.all([loadResources(),loadDiscoveredESPHome(),loadResourceStatus()]);};actions.append(open,edit,remove);row.append(info,actions);card.append(row);
      }
      host.append(card);
    }
    setGridClass();
  }
'''
INDEX_HTML = INDEX_HTML[:start] + NEW_RENDER + INDEX_HTML[end:]
