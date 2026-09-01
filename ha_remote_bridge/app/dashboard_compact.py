"""Compact Home Assistant-style dashboard redesign for HA Remote Bridge."""

from ui_shell_v12 import INDEX_HTML as BASE_INDEX_HTML

INDEX_HTML = BASE_INDEX_HTML

COMPACT_CSS = r'''
    /* 0.4.0 compact dashboard: Home Assistant already provides the outer app header. */
    .app-header { display:none !important; }
    .browserbar { box-shadow:none; }
    .tabs { padding:4px 8px 0; gap:2px; scrollbar-width:none; }
    .tabs::-webkit-scrollbar { display:none; }
    .tab { min-width:78px; max-width:170px; height:32px; border-radius:6px 6px 0 0; padding:0 9px; font-size:12px; }
    .nav { display:none; min-height:38px; padding:4px 8px; }
    body.hrb-session-active .nav { display:flex; }
    .nav-title { display:none !important; }
    .icon-button { width:32px; height:30px; border-radius:7px; }

    .home { max-width:1040px; margin:0 auto; padding:14px 14px 28px; }
    .toolbar { gap:8px; flex-wrap:nowrap; margin-bottom:10px; position:relative; }
    .search-wrap { flex:1 1 auto; min-width:0; }
    .search { min-height:42px; border-radius:10px; padding-left:36px; }
    .toolbar > .view-toggle,
    .toolbar > #toggle-filters,
    .toolbar > .toolbar-spacer,
    .toolbar > #refresh-all,
    .toolbar > #toggle-add,
    .toolbar > #ssh-keys,
    .toolbar > #add-ssh,
    .toolbar > #add-vnc,
    .toolbar > #smb-credentials,
    .toolbar > #add-smb { display:none !important; }

    .compact-top-actions { display:flex; gap:7px; flex:0 0 auto; }
    .compact-icon-button,.compact-add-button {
      height:42px; border:1px solid var(--border); border-radius:10px; background:var(--surface);
      color:var(--text); display:inline-flex; align-items:center; justify-content:center; font-weight:500;
    }
    .compact-icon-button { width:42px; padding:0; font-size:20px; letter-spacing:1px; }
    .compact-add-button { padding:0 14px; background:var(--ha-blue); border-color:var(--ha-blue); color:white; gap:6px; }
    .compact-filter-row { display:flex; gap:6px; overflow-x:auto; padding:0 0 12px; scrollbar-width:none; }
    .compact-filter-row::-webkit-scrollbar { display:none; }
    .compact-filter-chip { flex:0 0 auto; height:32px; padding:0 12px; border:1px solid var(--border); border-radius:16px; background:var(--surface); color:var(--muted); font-size:12px; }
    .compact-filter-chip.active { background:color-mix(in srgb,var(--ha-blue) 12%,var(--surface)); border-color:color-mix(in srgb,var(--ha-blue) 45%,var(--border)); color:var(--ha-blue); font-weight:600; }

    .compact-menu { position:absolute; z-index:80; min-width:190px; padding:6px; border:1px solid var(--border); border-radius:10px; background:var(--surface); box-shadow:0 10px 30px #0003; display:none; }
    .compact-menu.open { display:grid; }
    .compact-menu button { min-height:38px; border:0; border-radius:7px; padding:0 10px; text-align:left; background:transparent; color:var(--text); }
    .compact-menu button:hover { background:color-mix(in srgb,var(--text) 6%,transparent); }
    .compact-menu .danger { color:#d32f2f; }
    .compact-menu .menu-separator { height:1px; background:var(--border); margin:5px 3px; }
    #compact-add-menu,#compact-more-menu { right:0; top:48px; }

    #filter-bar { margin-top:-4px; border-style:solid; border-radius:10px; }
    #add-panel { border-radius:10px; }
    .section { margin-bottom:16px; }
    .section-head { min-height:32px; margin-bottom:7px; }
    .section-head h2 { font-size:15px; }
    .section-count { font-size:11px; }

    .device-grid,.device-grid.list { display:grid; grid-template-columns:1fr; gap:10px; }
    .device-card.connection-group-card { display:block !important; border-radius:12px; box-shadow:none; overflow:visible; }
    .group-head { padding:13px 14px 11px; gap:8px; }
    .group-name { font-size:15px; }
    .group-host { font-size:11px; margin-top:3px; }
    .group-count { display:none; }
    .group-health { display:inline-flex; align-items:center; gap:6px; color:var(--muted); font-size:11px; white-space:nowrap; }
    .group-health-dot { width:8px; height:8px; border-radius:50%; background:#9e9e9e; }
    .group-health-dot.online { background:#36a65c; }
    .group-health-dot.offline { background:#d9534f; }

    .connection-row { position:relative; display:grid; grid-template-columns:34px minmax(0,1fr) auto; align-items:center; gap:10px; padding:11px 12px; }
    .protocol-mark { width:32px; height:32px; border-radius:8px; display:grid; place-items:center; background:color-mix(in srgb,var(--ha-blue) 10%,var(--surface)); color:var(--ha-blue); font-size:9px; font-weight:700; letter-spacing:.25px; }
    .connection-info { min-width:0; }
    .connection-name { font-size:13px; font-weight:600; }
    .connection-meta { margin-top:3px; font-size:11px; }
    .connection-chips { margin-top:5px; }
    .connection-chips .type-chip { display:none; }
    .status-chip { padding:2px 7px; font-size:9px; }
    .connection-actions { display:flex; flex-wrap:nowrap; gap:6px; }
    .connection-actions .mini-button { min-height:32px; border-radius:7px; font-size:11px; }
    .connection-actions .mini-button.primary { padding:0 12px; }
    .endpoint-more { width:32px; padding:0 !important; font-size:18px !important; line-height:1; }
    .endpoint-menu { right:10px; top:48px; min-width:130px; }

    .device-grid.list .connection-row { grid-template-columns:34px minmax(0,1fr) auto; }
    .device-grid.list .connection-actions { justify-content:flex-end; }

    @media (max-width:760px) {
      .home { padding:10px 10px 24px; }
      .toolbar { margin-bottom:8px; }
      .compact-add-button { width:42px; padding:0; font-size:0; }
      .compact-add-button::before { content:'+'; font-size:23px; font-weight:400; }
      .connection-row,.device-grid.list .connection-row { grid-template-columns:32px minmax(0,1fr) auto; gap:8px; padding:10px; }
      .protocol-mark { width:30px; height:30px; border-radius:7px; }
      .connection-actions .mini-button.primary { padding:0 10px; }
      .group-head { padding:12px 11px 10px; }
      .filter-bar label { flex:1 1 150px; }
    }
'''
INDEX_HTML = INDEX_HTML.replace("  </style>", COMPACT_CSS + "\n  </style>", 1)

# The compact protocol filter is independent of the legacy select, which remains
# available in the overflow menu for discovery-specific filters.
old_visible = "function visibleResource(r){const q=globalQuery(),f=$('resource-filter').value,kind=resourceKind(r);const text=(r.name+' '+(r.group_name||'')+' '+r.url+' '+kind).toLowerCase();return(!q||text.includes(q))&&(f==='all'||f===kind||(f==='http'&&kind==='esphome'&&r.url.startsWith('http:')));}"
new_visible = "function visibleResource(r){const q=globalQuery(),f=(window.hrbCompactFilter||$('resource-filter').value),kind=resourceKind(r);const text=(r.name+' '+(r.group_name||'')+' '+r.url+' '+kind).toLowerCase();const typeMatch=f==='all'||f===kind||(f==='web'&&(kind==='http'||kind==='https'||kind==='esphome'))||(f==='http'&&kind==='esphome'&&r.url.startsWith('http:'));return(!q||text.includes(q))&&typeMatch;}"
if old_visible not in INDEX_HTML:
    raise RuntimeError("Compact UI composition failed: visibleResource signature changed")
INDEX_HTML = INDEX_HTML.replace(old_visible, new_visible, 1)

start = INDEX_HTML.index("  function renderResources(){")
end = INDEX_HTML.index("  async function restoreSessionTabs()", start)
NEW_RENDER = r'''  function compactKindLabel(r){const k=resourceKind(r);if(k==='http'||k==='https'||k==='esphome')return 'WEB';return k.toUpperCase();}
  function compactConnectionMeta(r){
    const kind=resourceKind(r),port=resourcePort(r);
    if(kind==='ssh')return [r.ssh_user||'',port?(':'+port):''].filter(Boolean).join(' · ');
    if(kind==='vnc')return [port?(':'+port):'',r.vnc_view_only?'View only':''].filter(Boolean).join(' · ');
    if(kind==='smb')return port?(':'+port):'SMB';
    try{const u=new URL(r.url);return [kind.toUpperCase(),port?(':'+port):'',u.pathname&&u.pathname!=='/'?u.pathname:''].filter(Boolean).join(' · ');}catch(_){return r.url;}
  }
  function compactEditResource(r){const kind=resourceKind(r);if(kind==='ssh')return showSSHResource(r);if(kind==='vnc')return showVNCResource(r);if(kind==='smb')return showSMBResource(r);return showEdit(r);}
  function closeCompactMenus(){document.querySelectorAll('.compact-menu.open').forEach(x=>x.classList.remove('open'));}
  function toggleCompactMenu(menu,event){event&&event.stopPropagation();const was=menu.classList.contains('open');closeCompactMenus();if(!was)menu.classList.add('open');}
  function renderResources(){
    const host=$('resources');host.innerHTML='';const visible=resourceData.filter(visibleResource);$('resource-count').textContent=visible.length+' of '+resourceData.length+' connections';
    if(!visible.length){host.innerHTML='<div class="empty">No configured connections match the current filters.</div>';setGridClass();return;}
    const grouped=new Map();for(const r of visible){const key=groupKey(r);if(!grouped.has(key))grouped.set(key,[]);grouped.get(key).push(r);}
    for(const [,items] of grouped){
      items.sort((a,b)=>{const ka=resourceKind(a),kb=resourceKind(b);if(ka!==kb)return ka.localeCompare(kb);return(resourcePort(a)||0)-(resourcePort(b)||0);});
      const first=items[0],explicit=items.find(x=>String(x.group_name||'').trim()),titleText=explicit?explicit.group_name:first.name,commonHost=resourceHost(first);
      const card=document.createElement('article');card.className='device-card connection-group-card';
      const head=document.createElement('div');head.className='group-head';const title=document.createElement('div');title.className='group-title';const name=document.createElement('div');name.className='group-name';name.textContent=titleText;const sub=document.createElement('div');sub.className='group-host';sub.textContent=commonHost||first.url;title.append(name,sub);
      const aggregate=items.map(r=>resourceStatus[r.id]).filter(Boolean);const anyOffline=aggregate.some(x=>!x.online),anyOnline=aggregate.some(x=>x.online);const gh=document.createElement('div');gh.className='group-health';const dot=document.createElement('span');dot.className='group-health-dot '+(anyOffline?'offline':anyOnline?'online':'');const txt=document.createElement('span');txt.textContent=anyOffline?'Attention':anyOnline?'Online':'Checking';gh.append(dot,txt);head.append(title,gh);card.append(head);
      for(const r of items){
        const row=document.createElement('div');row.className='connection-row';const mark=document.createElement('div');mark.className='protocol-mark';mark.textContent=compactKindLabel(r);
        const info=document.createElement('div');info.className='connection-info';const n=document.createElement('div');n.className='connection-name';const kind=resourceKind(r);const friendly=(kind==='http'||kind==='https'||kind==='esphome')?'Web':kind==='ssh'?'SSH':kind==='vnc'?'VNC':kind==='smb'?'Files':r.name;n.textContent=(String(r.name||'').trim().toLowerCase()===String(titleText||'').trim().toLowerCase())?friendly:r.name;const meta=document.createElement('div');meta.className='connection-meta';meta.textContent=compactConnectionMeta(r);const chips=document.createElement('div');chips.className='connection-chips';const health=resourceStatus[r.id];chips.append(health?makeChip(health.online?'Online':'Offline',health.online?'online':'offline'):makeChip('Checking…','unknown'));info.append(n,meta,chips);
        const actions=document.createElement('div');actions.className='connection-actions';const open=document.createElement('button');open.className='mini-button primary';open.type='button';open.textContent='Open';open.onclick=()=>openSession(r);const more=document.createElement('button');more.className='mini-button endpoint-more';more.type='button';more.textContent='⋮';more.title='Connection actions';const menu=document.createElement('div');menu.className='compact-menu endpoint-menu';const edit=document.createElement('button');edit.type='button';edit.textContent='Edit';edit.onclick=e=>{e.stopPropagation();closeCompactMenus();compactEditResource(r);};const remove=document.createElement('button');remove.type='button';remove.className='danger';remove.textContent='Delete';remove.onclick=async e=>{e.stopPropagation();closeCompactMenus();if(!confirm('Delete '+r.name+'?'))return;closeSession(r.id);await fetch(api('api/resources/'+r.id),{method:'DELETE'});await Promise.all([loadResources(),loadDiscoveredESPHome(),loadResourceStatus()]);};menu.append(edit,remove);more.onclick=e=>toggleCompactMenu(menu,e);actions.append(open,more,menu);row.append(mark,info,actions);card.append(row);
      }
      host.append(card);
    }
    setGridClass();
  }
'''
INDEX_HTML = INDEX_HTML[:start] + NEW_RENDER + INDEX_HTML[end:]

COMPACT_JS = r'''
  // Build one compact command surface while keeping the existing controls as
  // implementation targets so their mature dialog/event handlers remain intact.
  (function installCompactDashboard(){
    const toolbar=document.querySelector('.toolbar');if(!toolbar)return;
    const actions=document.createElement('div');actions.className='compact-top-actions';
    const add=document.createElement('button');add.className='compact-add-button';add.type='button';add.textContent='+ Add';
    const more=document.createElement('button');more.className='compact-icon-button';more.type='button';more.textContent='⋮';more.title='More';
    const addMenu=document.createElement('div');addMenu.id='compact-add-menu';addMenu.className='compact-menu';
    const moreMenu=document.createElement('div');moreMenu.id='compact-more-menu';moreMenu.className='compact-menu';
    function menuButton(label,fn,cls){const b=document.createElement('button');b.type='button';b.textContent=label;if(cls)b.className=cls;b.onclick=e=>{e.stopPropagation();closeCompactMenus();fn();};return b;}
    addMenu.append(
      menuButton('Web connection',()=>document.getElementById('toggle-add').click()),
      menuButton('SSH connection',()=>document.getElementById('add-ssh').click()),
      menuButton('VNC connection',()=>document.getElementById('add-vnc').click()),
      menuButton('SMB connection',()=>document.getElementById('add-smb').click())
    );
    const sep=document.createElement('div');sep.className='menu-separator';
    moreMenu.append(
      menuButton('Refresh',()=>document.getElementById('refresh-all').click()),
      menuButton('SSH credentials',()=>document.getElementById('ssh-keys').click()),
      menuButton('SMB credentials',()=>document.getElementById('smb-credentials').click()),
      sep,
      menuButton('Grid view',()=>document.getElementById('grid-view').click()),
      menuButton('List view',()=>document.getElementById('list-view').click()),
      menuButton('More filters',()=>document.getElementById('toggle-filters').click())
    );
    actions.append(add,more,addMenu,moreMenu);toolbar.append(actions);
    add.onclick=e=>toggleCompactMenu(addMenu,e);more.onclick=e=>toggleCompactMenu(moreMenu,e);

    const filters=document.createElement('div');filters.className='compact-filter-row';
    const choices=[['all','All'],['web','Web'],['ssh','SSH'],['vnc','VNC'],['smb','SMB']];
    for(const [value,label] of choices){const b=document.createElement('button');b.type='button';b.className='compact-filter-chip'+(value==='all'?' active':'');b.textContent=label;b.dataset.filter=value;b.onclick=()=>{window.hrbCompactFilter=value;filters.querySelectorAll('.compact-filter-chip').forEach(x=>x.classList.toggle('active',x===b));renderResources();};filters.append(b);}
    toolbar.insertAdjacentElement('afterend',filters);

    function syncSessionChrome(){document.body.classList.toggle('hrb-session-active',!document.getElementById('home-view').classList.contains('active'));}
    const observer=new MutationObserver(syncSessionChrome);observer.observe(document.getElementById('home-view'),{attributes:true,attributeFilter:['class']});syncSessionChrome();
    document.addEventListener('click',closeCompactMenus);
  })();
'''

# Append after the existing event wiring so every legacy target button already works.
idx = INDEX_HTML.rfind("</script>")
if idx < 0:
    raise RuntimeError("Compact UI composition failed: closing script not found")
INDEX_HTML = INDEX_HTML[:idx] + COMPACT_JS + "\n" + INDEX_HTML[idx:]

for required in (
    "compact-filter-row",
    "compact-add-menu",
    "compactEditResource",
    "endpoint-more",
    "hrb-session-active",
):
    if required not in INDEX_HTML:
        raise RuntimeError(f"Compact UI composition failed: missing {required}")
