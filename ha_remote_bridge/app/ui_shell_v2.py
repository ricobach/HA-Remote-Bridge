"""Home Assistant / ESPHome-style dashboard shell for HA Remote Bridge."""

INDEX_HTML = r'''<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>HA Remote Bridge</title>
  <link rel="icon" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 64 64'%3E%3Crect width='64' height='64' rx='12' fill='%2303a9f4'/%3E%3Cpath d='M14 44h36M19 44V31l13-10 13 10v13M25 44V35h14v9M18 18c8-7 20-7 28 0M23 24c5-4 13-4 18 0' fill='none' stroke='white' stroke-width='4' stroke-linecap='round' stroke-linejoin='round'/%3E%3C/svg%3E">
  <style>
    :root {
      color-scheme: light dark;
      font-family: Roboto, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      --ha-blue: var(--primary-color, #03a9f4);
      --ha-header: var(--app-header-background-color, #0396c8);
      --bg: var(--primary-background-color, #f5f5f5);
      --surface: var(--card-background-color, #fff);
      --text: var(--primary-text-color, #212121);
      --muted: var(--secondary-text-color, #727272);
      --border: #e0e0e0;
      --success: #2eaf62;
      --danger: #ef5350;
      --warning: #f5a623;
    }
    * { box-sizing:border-box; }
    html,body { width:100%; height:100%; margin:0; }
    body { background:var(--bg); color:var(--text); overflow:hidden; }
    button,input,select { font:inherit; }
    button { cursor:pointer; }
    .shell { height:100vh; display:flex; flex-direction:column; min-height:0; }

    .app-header { height:52px; display:flex; align-items:center; gap:12px; padding:0 16px; background:var(--ha-header); color:#fff; box-shadow:0 2px 5px #0002; z-index:20; }
    .brand-mark { width:34px; height:34px; flex:0 0 auto; }
    .app-title { min-width:0; }
    .app-title strong { display:block; font-size:16px; line-height:1.15; }
    .app-title span { display:block; font-size:11px; opacity:.86; margin-top:2px; }
    .app-header-spacer { flex:1; }
    .header-status { display:flex; align-items:center; gap:7px; font-size:12px; opacity:.95; }
    .status-dot { width:9px; height:9px; border-radius:50%; background:#7df394; box-shadow:0 0 0 3px #ffffff21; }

    .browserbar { background:var(--surface); border-bottom:1px solid var(--border); z-index:15; }
    .tabs { display:flex; align-items:end; gap:3px; padding:6px 10px 0; overflow-x:auto; }
    .tab { display:inline-flex; align-items:center; gap:7px; min-width:105px; max-width:220px; height:34px; padding:0 10px; border:1px solid transparent; border-radius:7px 7px 0 0; background:#eceff1; color:#455a64; white-space:nowrap; user-select:none; }
    .tab.active { background:var(--bg); border-color:var(--border); border-bottom-color:var(--bg); color:var(--ha-blue); }
    .tab-label { overflow:hidden; text-overflow:ellipsis; flex:1; }
    .tab-close { width:21px; height:21px; border:0; border-radius:50%; background:transparent; color:inherit; padding:0; }
    .tab-close:hover { background:#0001; }
    .nav { min-height:42px; display:flex; align-items:center; gap:5px; padding:5px 10px; border-top:1px solid #eee; }
    .icon-button { width:34px; height:32px; display:grid; place-items:center; border:1px solid var(--border); border-radius:5px; background:var(--surface); color:#546e7a; padding:0; }
    .icon-button:disabled { opacity:.35; cursor:default; }
    .nav-title { min-width:0; flex:1; padding:7px 10px; border-radius:5px; background:#f5f5f5; color:var(--muted); font-size:12px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }

    .views { position:relative; flex:1; min-height:0; }
    .view { position:absolute; inset:0; display:none; }
    .view.active { display:block; }
    .home-view { overflow:auto; }
    .home { padding:18px; }

    .toolbar { display:flex; align-items:center; gap:8px; flex-wrap:wrap; margin-bottom:12px; }
    .search-wrap { position:relative; flex:0 1 330px; min-width:220px; }
    .search-wrap::before { content:'⌕'; position:absolute; left:10px; top:8px; color:#78909c; font-size:19px; }
    .search { width:100%; min-height:38px; padding:8px 10px 8px 34px; border:1px solid var(--border); border-radius:4px; background:var(--surface); color:var(--text); outline:none; }
    .search:focus { border-color:var(--ha-blue); box-shadow:0 0 0 1px var(--ha-blue); }
    .toolbar-spacer { flex:1; }
    .tool-button { min-height:36px; display:inline-flex; align-items:center; justify-content:center; gap:6px; border:1px solid var(--border); border-radius:4px; padding:0 11px; background:var(--surface); color:#455a64; }
    .tool-button.primary { background:var(--ha-blue); color:#fff; border-color:var(--ha-blue); }
    .tool-button.active { background:#e1f5fe; color:#0277bd; border-color:#81d4fa; }
    .view-toggle { display:inline-flex; border:1px solid var(--border); border-radius:4px; overflow:hidden; }
    .view-toggle button { width:36px; height:34px; border:0; border-right:1px solid var(--border); background:var(--surface); color:#607d8b; }
    .view-toggle button:last-child { border-right:0; }
    .view-toggle button.active { background:var(--ha-blue); color:#fff; }

    .filter-bar { display:none; gap:8px; align-items:center; flex-wrap:wrap; padding:10px; margin-bottom:12px; border:1px dashed #cfd8dc; border-radius:6px; background:var(--surface); }
    .filter-bar.open { display:flex; }
    .filter-bar label { display:flex; align-items:center; gap:6px; font-size:12px; color:var(--muted); }
    select { min-height:34px; padding:5px 8px; border:1px solid var(--border); border-radius:4px; background:var(--surface); color:var(--text); }

    .section { margin-bottom:18px; }
    .section-head { display:flex; align-items:center; gap:10px; min-height:38px; margin-bottom:8px; }
    .section-head h2 { margin:0; font-size:14px; font-weight:600; }
    .section-count { font-size:12px; color:var(--muted); }
    .section-head-spacer { flex:1; }
    .collapse-button { width:30px; height:30px; border:0; border-radius:4px; background:transparent; color:#607d8b; font-size:18px; }
    .section.collapsed .section-body { display:none; }
    .section.collapsed .collapse-button { transform:rotate(-90deg); }

    .device-grid { display:grid; grid-template-columns:repeat(auto-fill,minmax(265px,1fr)); gap:12px; }
    .device-grid.list { grid-template-columns:1fr; }
    .device-card { background:var(--surface); border:1px solid var(--border); border-radius:9px; min-width:0; overflow:hidden; box-shadow:0 1px 2px #0000000f; }
    .device-main { padding:12px 12px 10px; }
    .device-title-row { display:flex; align-items:flex-start; gap:8px; }
    .device-title { min-width:0; flex:1; }
    .device-name { font-size:14px; font-weight:600; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
    .device-subtitle { margin-top:5px; font-size:11px; color:var(--muted); overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
    .device-details { margin-top:7px; font-size:11px; color:var(--muted); overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
    .status-chip,.type-chip { display:inline-flex; align-items:center; gap:4px; border-radius:999px; padding:3px 7px; font-size:10px; font-weight:600; white-space:nowrap; }
    .status-chip.online { color:#218c4c; background:#e5f7eb; }
    .status-chip.discovered { color:#0b70b7; background:#e1f3ff; }
    .status-chip.unknown { color:#666; background:#eee; }
    .type-chip { margin-left:5px; color:#0277bd; background:#e1f5fe; }
    .device-actions { min-height:42px; display:flex; gap:6px; align-items:center; padding:7px 10px; border-top:1px solid var(--border); background:#fafafa; }
    .mini-button { min-height:29px; border:1px solid var(--border); border-radius:4px; padding:0 9px; background:var(--surface); color:#455a64; font-size:11px; }
    .mini-button.primary { background:var(--ha-blue); border-color:var(--ha-blue); color:#fff; }
    .mini-button.danger { color:#d32f2f; }
    .actions-spacer { flex:1; }

    .device-grid.list .device-card { display:grid; grid-template-columns:minmax(220px,1fr) auto; }
    .device-grid.list .device-actions { border-top:0; border-left:1px solid var(--border); background:var(--surface); }

    .empty { padding:24px 8px; text-align:center; color:var(--muted); font-size:13px; border:1px dashed var(--border); border-radius:7px; background:var(--surface); }

    .add-panel { display:none; margin-bottom:14px; background:var(--surface); border:1px solid var(--border); border-radius:7px; padding:12px; }
    .add-panel.open { display:block; }
    .resource-form { display:grid; grid-template-columns:1fr 2fr auto auto; gap:10px; align-items:end; }
    label { font-size:11px; color:var(--muted); display:grid; gap:4px; }
    input[type=text],input[type=url] { min-height:36px; padding:7px 9px; border:1px solid var(--border); border-radius:4px; background:var(--surface); color:var(--text); }
    .checkbox-row { display:flex; align-items:center; gap:6px; min-height:36px; }

    .session-frame { width:100%; height:100%; border:0; background:#fff; display:block; }
    dialog { width:min(540px,calc(100vw - 30px)); border:0; border-radius:8px; padding:0; background:var(--surface); color:var(--text); box-shadow:0 14px 50px #0005; }
    dialog::backdrop { background:#0007; }
    .dialog-body { padding:18px; }
    .dialog-head { display:flex; align-items:center; gap:10px; margin-bottom:16px; }
    .dialog-head h2 { margin:0; font-size:17px; }
    .dialog-head-spacer { flex:1; }
    .edit-form { display:grid; gap:12px; }
    .dialog-actions { display:flex; justify-content:flex-end; gap:7px; margin-top:5px; }

    @media (prefers-color-scheme:dark) {
      :root { --bg:#11191f; --surface:#1c252c; --text:#e8eef2; --muted:#9aabb5; --border:#34424b; }
      .tabs .tab { background:#26343d; color:#c1cbd1; }
      .tab.active { background:var(--bg); border-color:var(--border); border-bottom-color:var(--bg); color:#67c7f5; }
      .nav { border-color:var(--border); }
      .nav-title,.device-actions { background:#182126; }
      .tool-button.active { background:#16384a; color:#8bd7ff; border-color:#356881; }
      .status-chip.unknown { background:#334047; color:#ccd6db; }
    }
    @media (max-width:760px) {
      .app-title span,.header-status,.nav-title { display:none; }
      .home { padding:10px; }
      .search-wrap { flex:1 1 100%; min-width:0; }
      .toolbar-spacer { display:none; }
      .resource-form { grid-template-columns:1fr; }
      .device-grid { grid-template-columns:1fr; }
      .device-grid.list .device-card { display:block; }
      .device-grid.list .device-actions { border-left:0; border-top:1px solid var(--border); }
    }
  </style>
</head>
<body>
<div class="shell">
  <header class="app-header">
    <svg class="brand-mark" viewBox="0 0 64 64" aria-label="HA Remote Bridge" role="img">
      <rect width="64" height="64" rx="12" fill="#fff" opacity=".18"/>
      <path d="M14 44h36M19 44V31l13-10 13 10v13M25 44V35h14v9M18 18c8-7 20-7 28 0M23 24c5-4 13-4 18 0" fill="none" stroke="white" stroke-width="4" stroke-linecap="round" stroke-linejoin="round"/>
    </svg>
    <div class="app-title"><strong>HA Remote Bridge</strong><span>Discover and access local web devices through Home Assistant</span></div>
    <div class="app-header-spacer"></div>
    <div class="header-status"><span class="status-dot"></span>Discovery enabled</div>
  </header>

  <div class="browserbar">
    <div id="tabs" class="tabs"><button id="home-tab" class="tab active" type="button"><span class="tab-label">Home</span></button></div>
    <div class="nav">
      <button id="back" class="icon-button" type="button" title="Back" disabled>←</button>
      <button id="forward" class="icon-button" type="button" title="Forward" disabled>→</button>
      <button id="reload" class="icon-button" type="button" title="Reload" disabled>↻</button>
      <div id="nav-title" class="nav-title">HA Remote Bridge</div>
    </div>
  </div>

  <div id="views" class="views">
    <section id="home-view" class="view home-view active">
      <main class="home">
        <div class="toolbar">
          <div class="search-wrap"><input id="global-search" class="search" type="search" placeholder="Search devices..."></div>
          <div class="view-toggle" aria-label="View mode">
            <button id="grid-view" class="active" type="button" title="Grid view">▦</button>
            <button id="list-view" type="button" title="List view">☷</button>
          </div>
          <button id="toggle-filters" class="tool-button" type="button">☰ Filters</button>
          <div class="toolbar-spacer"></div>
          <button id="refresh-all" class="tool-button" type="button">↻ Refresh</button>
          <button id="toggle-add" class="tool-button primary" type="button">＋ Add resource</button>
        </div>

        <div id="filter-bar" class="filter-bar">
          <label>Configured type
            <select id="resource-filter"><option value="all">All</option><option value="esphome">ESPHome</option><option value="https">HTTPS</option><option value="http">HTTP</option></select>
          </label>
          <label>Discovered address
            <select id="discovery-address-filter"><option value="all">IPv4 + IPv6</option><option value="ipv4">IPv4</option><option value="ipv6">IPv6</option></select>
          </label>
          <button id="clear-filters" class="tool-button" type="button">Clear filters</button>
        </div>

        <section id="add-panel" class="add-panel">
          <form id="add-form" class="resource-form">
            <label>Name<input id="name" type="text" required placeholder="Kitchen ESPHome"></label>
            <label>Local URL<input id="url" type="url" required placeholder="http://192.168.1.50"></label>
            <label class="checkbox-row"><input id="verify" type="checkbox" checked> Verify SSL</label>
            <button class="tool-button primary" type="submit">Add</button>
          </form>
        </section>

        <section id="configured-section" class="section">
          <div class="section-head"><h2>Configured resources</h2><span id="resource-count" class="section-count">0 devices</span></div>
          <div class="section-body"><div id="resources" class="device-grid"></div></div>
        </section>

        <section id="discovery-section" class="section">
          <div class="section-head">
            <h2>Discovered ESPHome devices</h2><span id="discovered-count" class="section-count">0 devices</span>
            <div class="section-head-spacer"></div>
            <button id="collapse-discovery" class="collapse-button" type="button" title="Collapse discovered devices">⌄</button>
          </div>
          <div class="section-body"><div id="discovered-esphome" class="device-grid"><div class="empty">Searching for ESPHome devices…</div></div></div>
        </section>
      </main>
    </section>
  </div>
</div>

<dialog id="edit-dialog">
  <div class="dialog-body">
    <div class="dialog-head"><h2>Edit resource</h2><div class="dialog-head-spacer"></div><button id="edit-close" class="icon-button" type="button">×</button></div>
    <form id="edit-form" class="edit-form">
      <input id="edit-id" type="hidden">
      <label>Name<input id="edit-name" type="text" required></label>
      <label>Local URL<input id="edit-url" type="url" required></label>
      <label class="checkbox-row"><input id="edit-verify" type="checkbox"> Verify SSL certificate</label>
      <div class="dialog-actions"><button id="edit-cancel" class="tool-button" type="button">Cancel</button><button class="tool-button primary" type="submit">Save</button></div>
    </form>
  </div>
</dialog>

<script>
  const base = window.location.pathname.endsWith('/') ? window.location.pathname : window.location.pathname + '/';
  const api = path => base + path;
  const sessions = new Map();
  let activeSessionId = null;
  let resourceData = [];
  let discoveryData = [];
  let viewMode = 'grid';
  const $ = id => document.getElementById(id);

  const tabs=$('tabs'),views=$('views'),homeTab=$('home-tab'),homeView=$('home-view');
  const backButton=$('back'),forwardButton=$('forward'),reloadButton=$('reload'),navTitle=$('nav-title'),editDialog=$('edit-dialog');

  function currentSession(){ return activeSessionId ? sessions.get(activeSessionId) : null; }
  function updateNavigation(){ const s=currentSession(),on=Boolean(s); backButton.disabled=!on;forwardButton.disabled=!on;reloadButton.disabled=!on;navTitle.textContent=s?s.resource.url:'HA Remote Bridge'; }
  function setActive(id){ activeSessionId=id;homeTab.classList.toggle('active',id===null);homeView.classList.toggle('active',id===null);for(const [sid,s] of sessions){const a=sid===id;s.tab.classList.toggle('active',a);s.view.classList.toggle('active',a);}updateNavigation(); }

  function openSession(resource){
    const existing=sessions.get(resource.id); if(existing){setActive(resource.id);return;}
    const tab=document.createElement('div');tab.className='tab';tab.tabIndex=0;tab.setAttribute('role','tab');
    const label=document.createElement('span');label.className='tab-label';label.textContent=resource.name;
    const close=document.createElement('button');close.type='button';close.className='tab-close';close.textContent='×';close.title='Close '+resource.name;close.addEventListener('click',e=>{e.stopPropagation();closeSession(resource.id);});
    tab.append(label,close);tab.addEventListener('click',()=>setActive(resource.id));tab.addEventListener('keydown',e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();setActive(resource.id);}});tabs.append(tab);
    const view=document.createElement('section');view.className='view';const frame=document.createElement('iframe');frame.className='session-frame';frame.src=api('proxy/'+resource.id+'/');frame.title=resource.name;
    frame.addEventListener('load',()=>{try{const t=frame.contentDocument&&frame.contentDocument.title;if(t){label.textContent=t;tab.title=t;}}catch(_){}if(activeSessionId===resource.id)updateNavigation();});
    view.append(frame);views.append(view);sessions.set(resource.id,{resource,tab,label,view,frame});setActive(resource.id);
  }
  function closeSession(id){const s=sessions.get(id);if(!s)return;const active=activeSessionId===id;s.tab.remove();s.view.remove();sessions.delete(id);if(active){const ids=[...sessions.keys()];setActive(ids.length?ids[ids.length-1]:null);}}
  function navigate(kind){const s=currentSession();if(!s)return;try{if(kind==='back')s.frame.contentWindow.history.back();if(kind==='forward')s.frame.contentWindow.history.forward();if(kind==='reload')s.frame.contentWindow.location.reload();}catch(_){if(kind==='reload')s.frame.src=s.frame.src;}}

  function resourceKind(r){if(r.resource_type==='esphome'||r.profile==='esphome')return'esphome';try{return new URL(r.url).protocol==='https:'?'https':'http';}catch(_){return'http';}}
  function globalQuery(){return $('global-search').value.trim().toLowerCase();}
  function visibleResource(r){const q=globalQuery(),f=$('resource-filter').value,kind=resourceKind(r);const text=(r.name+' '+r.url+' '+kind).toLowerCase();return(!q||text.includes(q))&&(f==='all'||f===kind||(f==='http'&&kind==='esphome'&&r.url.startsWith('http:')));}
  function visibleDiscovery(d){const q=globalQuery(),f=$('discovery-address-filter').value,text=(d.name+' '+d.url+' '+(d.hostname||'')+' '+(d.version||'')).toLowerCase(),is6=(d.url||'').includes('[');return(!q||text.includes(q))&&(f==='all'||(f==='ipv6'&&is6)||(f==='ipv4'&&!is6));}

  function makeChip(text,cls){const x=document.createElement('span');x.className='status-chip '+cls;x.textContent=text;return x;}
  function setGridClass(){for(const id of ['resources','discovered-esphome']){const host=$(id);if(host)host.classList.toggle('list',viewMode==='list');}$('grid-view').classList.toggle('active',viewMode==='grid');$('list-view').classList.toggle('active',viewMode==='list');}

  function renderResources(){
    const host=$('resources');host.innerHTML='';const list=resourceData.filter(visibleResource);$('resource-count').textContent=list.length+' of '+resourceData.length+' devices';
    if(!list.length){host.innerHTML='<div class="empty">No configured resources match the current filters.</div>';setGridClass();return;}
    for(const r of list){
      const card=document.createElement('article');card.className='device-card';
      const main=document.createElement('div');main.className='device-main';
      const row=document.createElement('div');row.className='device-title-row';
      const title=document.createElement('div');title.className='device-title';const name=document.createElement('div');name.className='device-name';name.textContent=r.name;const sub=document.createElement('div');sub.className='device-subtitle';sub.textContent=r.url;const details=document.createElement('div');details.className='device-details';details.textContent='TLS verification: '+(r.verify_ssl===false?'off':'on');title.append(name,sub,details);
      const chips=document.createElement('div');chips.append(makeChip('Configured','online'));const type=document.createElement('span');type.className='type-chip';type.textContent=resourceKind(r)==='esphome'?'ESPHome':resourceKind(r).toUpperCase();chips.append(type);row.append(title,chips);main.append(row);
      const actions=document.createElement('div');actions.className='device-actions';
      const open=document.createElement('button');open.className='mini-button primary';open.type='button';open.textContent=sessions.has(r.id)?'Show':'Open';open.onclick=()=>openSession(r);
      const edit=document.createElement('button');edit.className='mini-button';edit.type='button';edit.textContent='Edit';edit.onclick=()=>showEdit(r);
      const spacer=document.createElement('div');spacer.className='actions-spacer';
      const remove=document.createElement('button');remove.className='mini-button danger';remove.type='button';remove.textContent='Delete';remove.onclick=async()=>{if(!confirm('Delete '+r.name+'?'))return;closeSession(r.id);await fetch(api('api/resources/'+r.id),{method:'DELETE'});await Promise.all([loadResources(),loadDiscoveredESPHome()]);};
      actions.append(open,edit,spacer,remove);card.append(main,actions);host.append(card);
    }
    setGridClass();
  }
  async function loadResources(){const res=await fetch(api('api/resources'),{cache:'no-store'});resourceData=await res.json();renderResources();}

  function renderDiscovery(){
    const host=$('discovered-esphome');host.innerHTML='';const list=discoveryData.filter(visibleDiscovery);$('discovered-count').textContent=list.length+' of '+discoveryData.length+' devices';
    if(!list.length){host.innerHTML='<div class="empty">No discovered ESPHome devices match the current filters.</div>';setGridClass();return;}
    for(const d of list){
      const card=document.createElement('article');card.className='device-card';
      const main=document.createElement('div');main.className='device-main';
      const row=document.createElement('div');row.className='device-title-row';
      const title=document.createElement('div');title.className='device-title';const name=document.createElement('div');name.className='device-name';name.textContent=d.name;const sub=document.createElement('div');sub.className='device-subtitle';sub.textContent=d.hostname||d.url;const details=document.createElement('div');details.className='device-details';details.textContent=[d.version?'ESPHome '+d.version:null,d.url,d.mac].filter(Boolean).join(' · ');title.append(name,sub,details);
      const chips=document.createElement('div');chips.append(makeChip('Discovered','discovered'));const type=document.createElement('span');type.className='type-chip';type.textContent='ESPHome';chips.append(type);row.append(title,chips);main.append(row);
      const actions=document.createElement('div');actions.className='device-actions';const add=document.createElement('button');add.className='mini-button primary';add.type='button';add.textContent='＋ Add';add.onclick=async()=>{add.disabled=true;const res=await fetch(api('api/resources'),{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({name:d.name,url:d.url,verify_ssl:false,resource_type:'esphome',discovery_key:d.key||d.hostname})});if(!res.ok){add.disabled=false;alert(await res.text());return;}await Promise.all([loadResources(),loadDiscoveredESPHome()]);};const spacer=document.createElement('div');spacer.className='actions-spacer';actions.append(add,spacer);card.append(main,actions);host.append(card);
    }
    setGridClass();
  }
  async function loadDiscoveredESPHome(){try{const res=await fetch(api('api/discovery/esphome'),{cache:'no-store'});if(!res.ok)throw new Error(await res.text());discoveryData=await res.json();renderDiscovery();}catch(e){$('discovered-esphome').innerHTML='<div class="empty">ESPHome discovery unavailable: '+String(e)+'</div>';}}

  function showEdit(r){$('edit-id').value=r.id;$('edit-name').value=r.name;$('edit-url').value=r.url;$('edit-verify').checked=r.verify_ssl!==false;editDialog.showModal();}
  function closeEdit(){if(editDialog.open)editDialog.close();}
  $('edit-form').addEventListener('submit',async e=>{e.preventDefault();const id=$('edit-id').value;const res=await fetch(api('api/resources/'+id),{method:'PUT',headers:{'Content-Type':'application/json'},body:JSON.stringify({name:$('edit-name').value,url:$('edit-url').value,verify_ssl:$('edit-verify').checked})});if(!res.ok){alert(await res.text());return;}const updated=await res.json();const s=sessions.get(id);if(s){s.resource=updated;s.label.textContent=updated.name;s.tab.title=updated.name;s.frame.title=updated.name;s.frame.src=api('proxy/'+id+'/');}closeEdit();updateNavigation();await loadResources();});

  homeTab.addEventListener('click',()=>setActive(null));backButton.addEventListener('click',()=>navigate('back'));forwardButton.addEventListener('click',()=>navigate('forward'));reloadButton.addEventListener('click',()=>navigate('reload'));
  $('edit-close').addEventListener('click',closeEdit);$('edit-cancel').addEventListener('click',closeEdit);
  $('toggle-add').addEventListener('click',()=>{$('add-panel').classList.toggle('open');if($('add-panel').classList.contains('open'))$('name').focus();});
  $('toggle-filters').addEventListener('click',()=>{$('filter-bar').classList.toggle('open');$('toggle-filters').classList.toggle('active',$('filter-bar').classList.contains('open'));});
  $('clear-filters').addEventListener('click',()=>{$('global-search').value='';$('resource-filter').value='all';$('discovery-address-filter').value='all';renderResources();renderDiscovery();});
  $('refresh-all').addEventListener('click',()=>Promise.all([loadResources(),loadDiscoveredESPHome()]));
  $('global-search').addEventListener('input',()=>{renderResources();renderDiscovery();});$('resource-filter').addEventListener('change',renderResources);$('discovery-address-filter').addEventListener('change',renderDiscovery);
  $('grid-view').addEventListener('click',()=>{viewMode='grid';setGridClass();});$('list-view').addEventListener('click',()=>{viewMode='list';setGridClass();});
  $('collapse-discovery').addEventListener('click',()=>{const s=$('discovery-section');s.classList.toggle('collapsed');$('collapse-discovery').title=s.classList.contains('collapsed')?'Expand discovered devices':'Collapse discovered devices';});
  $('add-form').addEventListener('submit',async e=>{e.preventDefault();const res=await fetch(api('api/resources'),{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({name:$('name').value,url:$('url').value,verify_ssl:$('verify').checked})});if(!res.ok){alert(await res.text());return;}e.target.reset();$('verify').checked=true;$('add-panel').classList.remove('open');await Promise.all([loadResources(),loadDiscoveredESPHome()]);});

  loadResources();loadDiscoveredESPHome();setGridClass();setInterval(loadDiscoveredESPHome,10000);
</script>
</body>
</html>'''
