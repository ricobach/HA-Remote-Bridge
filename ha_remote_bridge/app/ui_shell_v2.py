"""Modern dashboard shell for HA Remote Bridge."""

INDEX_HTML = r'''<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>HA Remote Bridge</title>
  <link rel="icon" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 64 64'%3E%3Cdefs%3E%3ClinearGradient id='g' x1='0' y1='0' x2='1' y2='1'%3E%3Cstop stop-color='%2306b6d4'/%3E%3Cstop offset='1' stop-color='%232563eb'/%3E%3C/linearGradient%3E%3C/defs%3E%3Crect width='64' height='64' rx='15' fill='url(%23g)'/%3E%3Cpath d='M15 43h34M20 43V31l12-10 12 10v12M25 43V34h14v9M18 20c8-8 20-8 28 0M23 25c5-5 13-5 18 0' fill='none' stroke='white' stroke-width='4' stroke-linecap='round' stroke-linejoin='round'/%3E%3C/svg%3E">
  <style>
    :root { color-scheme: light dark; font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; }
    * { box-sizing: border-box; }
    html, body { width:100%; height:100%; margin:0; }
    body { background:#f3f7fb; color:#10233f; overflow:hidden; }
    button, input, select { font:inherit; }
    button { cursor:pointer; }
    .shell { height:100vh; display:flex; flex-direction:column; min-height:0; }
    .topbar { background:#fff; border-bottom:1px solid #d9e3ef; box-shadow:0 2px 10px #23415d12; z-index:10; }
    .tabs { display:flex; align-items:end; gap:5px; padding:8px 12px 0; overflow-x:auto; }
    .tab { display:inline-flex; align-items:center; gap:8px; min-width:105px; max-width:230px; height:38px; padding:0 11px; border:1px solid transparent; border-radius:10px 10px 0 0; background:#eef4fa; color:#35516f; user-select:none; white-space:nowrap; }
    .tab.active { background:#f3f7fb; border-color:#d9e3ef; border-bottom-color:#f3f7fb; color:#0d47a1; }
    .tab-label { overflow:hidden; text-overflow:ellipsis; flex:1; }
    .tab-close { display:grid; place-items:center; width:23px; height:23px; border:0; border-radius:50%; background:transparent; color:inherit; }
    .tab-close:hover { background:#dce8f4; }
    .nav { min-height:46px; padding:6px 12px; display:flex; gap:7px; align-items:center; border-top:1px solid #edf2f7; }
    .nav button { width:36px; height:34px; border:1px solid #d9e3ef; border-radius:9px; background:#f7fafc; color:#22466d; font-size:18px; }
    .nav button:disabled { opacity:.35; cursor:default; }
    .nav-title { min-width:0; flex:1; margin-left:4px; padding:8px 12px; border-radius:9px; background:#f4f7fa; color:#63768a; font-size:13px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
    .views { position:relative; flex:1; min-height:0; }
    .view { position:absolute; inset:0; display:none; }
    .view.active { display:block; }
    .home-view { overflow:auto; }
    .home { max-width:1180px; margin:0 auto; padding:22px; }
    .hero { display:flex; align-items:center; justify-content:space-between; gap:18px; padding:24px 26px; margin-bottom:18px; border-radius:20px; color:white; background:linear-gradient(120deg,#1467d8,#169fe8 55%,#19c0e8); box-shadow:0 12px 28px #1266c62b; }
    .brand { display:flex; align-items:center; gap:17px; min-width:0; }
    .brand-icon { flex:0 0 auto; width:72px; height:72px; border-radius:18px; background:#ffffff20; box-shadow:inset 0 0 0 1px #ffffff2b; padding:10px; }
    .hero h1 { margin:0 0 4px; font-size:29px; letter-spacing:-.02em; }
    .hero p { margin:0; opacity:.88; }
    .status-pill { display:flex; align-items:center; gap:9px; padding:11px 14px; border-radius:12px; background:#075fbf99; white-space:nowrap; font-size:13px; }
    .status-dot { width:10px; height:10px; border-radius:50%; background:#36db63; box-shadow:0 0 0 4px #36db6328; }
    .toolbar { display:flex; gap:10px; align-items:center; flex-wrap:wrap; margin-bottom:16px; }
    .grow { flex:1; }
    .action { border:0; border-radius:10px; padding:10px 14px; min-height:40px; background:#106ee8; color:white; font-weight:650; }
    .action:hover { filter:brightness(.97); }
    .secondary { background:#eff5fb; color:#1c5a95; border:1px solid #cfdeec; }
    .danger { background:#fff0f0; color:#c31d25; border:1px solid #f3c5c8; }
    .panel { background:#fff; border:1px solid #dce6ef; border-radius:16px; margin-bottom:18px; box-shadow:0 7px 20px #244b7210; overflow:hidden; }
    .panel-head { display:flex; align-items:center; justify-content:space-between; gap:14px; padding:17px 18px; background:#f7fbff; border-bottom:1px solid #e4edf5; }
    .panel-title { display:flex; align-items:center; gap:12px; min-width:0; }
    .section-icon { width:38px; height:38px; display:grid; place-items:center; border-radius:11px; background:#e6f3ff; color:#0d6bdc; font-size:20px; flex:0 0 auto; }
    .panel h2 { margin:0; font-size:18px; }
    .muted { color:#6a7f93; font-size:13px; margin-top:3px; }
    .count { display:inline-flex; align-items:center; min-height:25px; padding:3px 9px; border-radius:999px; background:#e7f1ff; color:#0e5fbd; font-size:12px; font-weight:700; }
    .panel-body { padding:16px; }
    .panel.collapsed .panel-body { display:none; }
    .panel.collapsed .panel-head { border-bottom:0; }
    .collapse-button { width:36px; height:36px; border:1px solid #d6e2ed; border-radius:9px; background:white; color:#37617f; font-size:18px; transition:transform .15s ease; }
    .panel.collapsed .collapse-button { transform:rotate(-90deg); }
    .filters { display:flex; flex-wrap:wrap; gap:9px; align-items:center; margin-bottom:14px; }
    .search, select { min-height:40px; border:1px solid #ccdae7; border-radius:10px; background:#fff; color:#183a5a; padding:8px 11px; }
    .search { flex:1 1 230px; min-width:160px; }
    select { flex:0 0 auto; }
    .resource-grid, .discovery-grid { display:grid; gap:12px; }
    .resource-grid { grid-template-columns:1fr; }
    .discovery-grid { grid-template-columns:repeat(auto-fit,minmax(255px,1fr)); }
    .device-card { border:1px solid #dce6ef; border-radius:14px; padding:15px; background:#fff; display:flex; flex-direction:column; gap:12px; min-width:0; }
    .device-top { display:flex; align-items:flex-start; gap:11px; }
    .device-badge { width:44px; height:44px; border-radius:12px; display:grid; place-items:center; background:#eaf5ff; color:#0a73e8; font-weight:800; }
    .resource-card { display:grid; grid-template-columns:minmax(190px,1.1fr) minmax(210px,1.5fr) auto; gap:16px; align-items:center; border:1px solid #e0e8f0; border-radius:13px; padding:14px 15px; }
    .resource-name { font-weight:750; font-size:16px; color:#102b4c; }
    .resource-url { color:#2c6db2; font-size:13px; overflow-wrap:anywhere; margin-top:3px; }
    .resource-meta { color:#75889b; font-size:12px; margin-top:4px; }
    .badge { display:inline-flex; align-items:center; padding:4px 8px; border-radius:999px; font-size:11px; font-weight:750; background:#e7f7eb; color:#218544; margin-left:7px; vertical-align:middle; }
    .actions { display:flex; gap:7px; flex-wrap:wrap; justify-content:flex-end; }
    .empty { color:#7a8da0; text-align:center; padding:24px 6px; }
    .form-card { padding:16px; }
    form.resource-form { display:grid; grid-template-columns:1fr 2fr auto auto; gap:10px; align-items:end; }
    form.edit-form { display:grid; gap:14px; }
    label { font-size:12px; color:#657a8f; display:grid; gap:5px; }
    input[type=text], input[type=url] { min-height:40px; padding:9px 11px; border:1px solid #ccdae7; border-radius:9px; background:#fff; color:#173957; }
    .checkbox-row { display:flex; align-items:center; gap:8px; font-size:14px; color:#53697f; }
    .session-frame { display:block; width:100%; height:100%; border:0; background:white; }
    dialog { width:min(560px,calc(100vw - 28px)); border:0; border-radius:16px; padding:0; background:#fff; color:#173957; box-shadow:0 20px 70px #071f3d52; }
    dialog::backdrop { background:#07182d99; }
    .dialog-body { padding:20px; }
    .dialog-head { display:flex; justify-content:space-between; align-items:center; margin-bottom:18px; }
    .dialog-head h2 { margin:0; }
    .dialog-close { width:36px; height:36px; border:0; border-radius:9px; background:#f1f5f9; color:#3f5f7e; font-size:22px; }
    .dialog-actions { display:flex; justify-content:flex-end; gap:8px; margin-top:8px; }
    @media (prefers-color-scheme: dark) {
      body { background:#101821; color:#e8f0f8; }
      .topbar,.panel,.device-card,dialog { background:#17222e; border-color:#2b3a49; }
      .tab { background:#1e2c39; color:#c9d8e7; }
      .tab.active { background:#101821; border-color:#2b3a49; border-bottom-color:#101821; color:#75b7ff; }
      .nav { border-color:#253442; }
      .nav button,.nav-title,.secondary,.collapse-button,.search,select,input[type=text],input[type=url] { background:#1b2936; border-color:#334658; color:#dbe7f1; }
      .panel-head { background:#14202b; border-color:#283847; }
      .resource-card,.device-card { border-color:#2b3d4d; }
      .resource-name { color:#edf5fb; }
      .resource-url { color:#75b7ff; }
      .muted,.resource-meta,label { color:#9fb1c2; }
      .section-icon { background:#193752; }
    }
    @media (max-width:760px) {
      .home { padding:13px; }
      .hero { padding:18px; align-items:flex-start; }
      .brand-icon { width:58px; height:58px; }
      .hero h1 { font-size:23px; }
      .status-pill { display:none; }
      form.resource-form { grid-template-columns:1fr; }
      .resource-card { grid-template-columns:1fr; }
      .actions { justify-content:flex-start; }
      .nav-title { display:none; }
    }
  </style>
</head>
<body>
<div class="shell">
  <header class="topbar">
    <div id="tabs" class="tabs">
      <button id="home-tab" class="tab active" type="button"><span class="tab-label">Home</span></button>
    </div>
    <div class="nav">
      <button id="back" type="button" title="Back" disabled>←</button>
      <button id="forward" type="button" title="Forward" disabled>→</button>
      <button id="reload" type="button" title="Reload" disabled>↻</button>
      <div id="nav-title" class="nav-title">HA Remote Bridge</div>
    </div>
  </header>

  <div id="views" class="views">
    <section id="home-view" class="view home-view active">
      <main class="home">
        <section class="hero">
          <div class="brand">
            <svg class="brand-icon" viewBox="0 0 64 64" aria-label="HA Remote Bridge logo" role="img">
              <path d="M14 46h36M19 46V32l13-11 13 11v14M25 46V36h14v10M17 19c8-8 22-8 30 0M23 25c5-5 13-5 18 0" fill="none" stroke="currentColor" stroke-width="4" stroke-linecap="round" stroke-linejoin="round"/>
            </svg>
            <div><h1>HA Remote Bridge</h1><p>Secure access to ESPHome and local web resources through Home Assistant.</p></div>
          </div>
          <div class="status-pill"><span class="status-dot"></span><span><strong>Running</strong><br>mDNS discovery active</span></div>
        </section>

        <div class="toolbar">
          <button id="toggle-add" class="action" type="button">＋ Add resource</button>
          <div class="grow"></div>
          <button id="refresh-all" class="action secondary" type="button">↻ Refresh</button>
        </div>

        <section id="add-panel" class="panel" hidden>
          <div class="form-card">
            <form id="add-form" class="resource-form">
              <label>Name<input id="name" type="text" required placeholder="Kitchen ESPHome"></label>
              <label>Local URL<input id="url" type="url" required placeholder="http://192.168.1.50"></label>
              <label class="checkbox-row"><input id="verify" type="checkbox" checked> Verify SSL</label>
              <button class="action" type="submit">Add resource</button>
            </form>
          </div>
        </section>

        <section id="discovery-panel" class="panel">
          <div class="panel-head">
            <div class="panel-title"><div class="section-icon">⌕</div><div><h2>Discovered ESPHome devices <span id="discovered-count" class="count">0</span></h2><div class="muted">ESPHome web servers found on your network via mDNS.</div></div></div>
            <button id="collapse-discovery" class="collapse-button" type="button" title="Collapse discovered devices">⌄</button>
          </div>
          <div class="panel-body">
            <div class="filters">
              <input id="discovery-search" class="search" type="search" placeholder="Filter discovered devices…">
              <select id="discovery-address-filter"><option value="all">All addresses</option><option value="ipv4">IPv4</option><option value="ipv6">IPv6</option></select>
            </div>
            <div id="discovered-esphome" class="discovery-grid"><div class="empty">Searching for ESPHome devices…</div></div>
          </div>
        </section>

        <section class="panel">
          <div class="panel-head"><div class="panel-title"><div class="section-icon">▱</div><div><h2>Configured resources <span id="resource-count" class="count">0</span></h2><div class="muted">Your active remote bridge targets.</div></div></div></div>
          <div class="panel-body">
            <div class="filters">
              <input id="resource-search" class="search" type="search" placeholder="Filter resources…">
              <select id="resource-filter"><option value="all">All resources</option><option value="esphome">ESPHome</option><option value="https">HTTPS</option><option value="http">HTTP</option></select>
            </div>
            <div id="resources" class="resource-grid"></div>
          </div>
        </section>
      </main>
    </section>
  </div>
</div>

<dialog id="edit-dialog"><div class="dialog-body"><div class="dialog-head"><h2>Edit resource</h2><button id="edit-close" class="dialog-close" type="button">×</button></div><form id="edit-form" class="edit-form"><input id="edit-id" type="hidden"><label>Name<input id="edit-name" type="text" required></label><label>Local URL<input id="edit-url" type="url" required></label><label class="checkbox-row"><input id="edit-verify" type="checkbox"> Verify SSL certificate</label><div class="dialog-actions"><button id="edit-cancel" class="action secondary" type="button">Cancel</button><button class="action" type="submit">Save changes</button></div></form></div></dialog>

<script>
  const base = window.location.pathname.endsWith('/') ? window.location.pathname : window.location.pathname + '/';
  const api = path => base + path;
  const sessions = new Map();
  let activeSessionId = null;
  let resourceData = [];
  let discoveryData = [];

  const $ = id => document.getElementById(id);
  const tabs = $('tabs'), views = $('views'), homeTab = $('home-tab'), homeView = $('home-view');
  const backButton = $('back'), forwardButton = $('forward'), reloadButton = $('reload'), navTitle = $('nav-title');
  const editDialog = $('edit-dialog');

  function currentSession(){ return activeSessionId ? sessions.get(activeSessionId) : null; }
  function updateNavigation(){ const s=currentSession(), on=Boolean(s); backButton.disabled=!on; forwardButton.disabled=!on; reloadButton.disabled=!on; navTitle.textContent=s?s.resource.url:'HA Remote Bridge'; }
  function setActive(id){ activeSessionId=id; homeTab.classList.toggle('active',id===null); homeView.classList.toggle('active',id===null); for(const [sid,s] of sessions){ const a=sid===id; s.tab.classList.toggle('active',a); s.view.classList.toggle('active',a); } updateNavigation(); }

  function openSession(resource){
    const existing=sessions.get(resource.id); if(existing){ setActive(resource.id); return; }
    const tab=document.createElement('div'); tab.className='tab'; tab.tabIndex=0; tab.setAttribute('role','tab');
    const label=document.createElement('span'); label.className='tab-label'; label.textContent=resource.name;
    const close=document.createElement('button'); close.type='button'; close.className='tab-close'; close.textContent='×'; close.title='Close '+resource.name; close.addEventListener('click',e=>{e.stopPropagation();closeSession(resource.id);});
    tab.append(label,close); tab.addEventListener('click',()=>setActive(resource.id)); tab.addEventListener('keydown',e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();setActive(resource.id);}}); tabs.append(tab);
    const view=document.createElement('section'); view.className='view'; const frame=document.createElement('iframe'); frame.className='session-frame'; frame.src=api('proxy/'+resource.id+'/'); frame.title=resource.name;
    frame.addEventListener('load',()=>{ try{ const t=frame.contentDocument&&frame.contentDocument.title; if(t){label.textContent=t;tab.title=t;} }catch(_){} if(activeSessionId===resource.id) updateNavigation(); });
    view.append(frame); views.append(view); sessions.set(resource.id,{resource,tab,label,view,frame}); setActive(resource.id);
  }
  function closeSession(id){ const s=sessions.get(id); if(!s)return; const active=activeSessionId===id; s.tab.remove();s.view.remove();sessions.delete(id); if(active){const ids=[...sessions.keys()];setActive(ids.length?ids[ids.length-1]:null);} }
  function navigate(kind){ const s=currentSession(); if(!s)return; try{ if(kind==='back')s.frame.contentWindow.history.back(); if(kind==='forward')s.frame.contentWindow.history.forward(); if(kind==='reload')s.frame.contentWindow.location.reload(); }catch(_){ if(kind==='reload')s.frame.src=s.frame.src; } }

  function resourceKind(r){ if(r.resource_type==='esphome'||r.profile==='esphome')return'esphome'; try{return new URL(r.url).protocol==='https:'?'https':'http';}catch(_){return'http';} }
  function visibleResource(r){ const q=$('resource-search').value.trim().toLowerCase(), f=$('resource-filter').value, kind=resourceKind(r); const matches=!q||(r.name+' '+r.url).toLowerCase().includes(q); return matches&&(f==='all'||f===kind||(f==='http'&&kind==='esphome'&&r.url.startsWith('http:'))); }
  function renderResources(){
    const host=$('resources'); host.innerHTML=''; $('resource-count').textContent=resourceData.length;
    const list=resourceData.filter(visibleResource); if(!list.length){host.innerHTML='<div class="empty">No resources match the current filter.</div>';return;}
    for(const r of list){
      const card=document.createElement('div'); card.className='resource-card';
      const info=document.createElement('div'); const name=document.createElement('div'); name.className='resource-name'; name.textContent=r.name; const badge=document.createElement('span'); badge.className='badge'; badge.textContent=resourceKind(r)==='esphome'?'ESPHome':'Web'; name.append(badge); const meta=document.createElement('div'); meta.className='resource-meta'; meta.textContent='TLS verification: '+(r.verify_ssl===false?'off':'on'); info.append(name,meta);
      const url=document.createElement('div'); url.className='resource-url'; url.textContent=r.url;
      const actions=document.createElement('div'); actions.className='actions';
      const open=document.createElement('button'); open.className='action'; open.type='button'; open.textContent=sessions.has(r.id)?'Show':'Open'; open.onclick=()=>openSession(r);
      const edit=document.createElement('button'); edit.className='action secondary'; edit.type='button'; edit.textContent='Edit'; edit.onclick=()=>showEdit(r);
      const remove=document.createElement('button'); remove.className='action danger'; remove.type='button'; remove.textContent='Delete'; remove.onclick=async()=>{if(!confirm('Delete '+r.name+'?'))return;closeSession(r.id);await fetch(api('api/resources/'+r.id),{method:'DELETE'});await loadResources();await loadDiscoveredESPHome();};
      actions.append(open,edit,remove); card.append(info,url,actions); host.append(card);
    }
  }
  async function loadResources(){ const res=await fetch(api('api/resources'),{cache:'no-store'}); resourceData=await res.json(); renderResources(); }

  function visibleDiscovery(d){ const q=$('discovery-search').value.trim().toLowerCase(), f=$('discovery-address-filter').value; const text=(d.name+' '+d.url+' '+(d.hostname||'')+' '+(d.version||'')).toLowerCase(); const is6=(d.url||'').includes('['); return (!q||text.includes(q))&&(f==='all'||(f==='ipv6'&&is6)||(f==='ipv4'&&!is6)); }
  function renderDiscovery(){
    const host=$('discovered-esphome'); host.innerHTML=''; $('discovered-count').textContent=discoveryData.length;
    const list=discoveryData.filter(visibleDiscovery); if(!list.length){host.innerHTML='<div class="empty">No discovered ESPHome devices match the current filter.</div>';return;}
    for(const d of list){
      const card=document.createElement('div'); card.className='device-card'; const top=document.createElement('div'); top.className='device-top'; const ico=document.createElement('div'); ico.className='device-badge'; ico.textContent='ESP';
      const info=document.createElement('div'); const name=document.createElement('div'); name.className='resource-name'; name.textContent=d.name; const url=document.createElement('div'); url.className='resource-url'; url.textContent=d.url; const meta=document.createElement('div'); meta.className='resource-meta'; meta.textContent=[d.version?'ESPHome '+d.version:null,d.mac,d.hostname].filter(Boolean).join(' · '); info.append(name,url,meta); top.append(ico,info);
      const actions=document.createElement('div'); actions.className='actions'; const add=document.createElement('button'); add.className='action'; add.type='button'; add.textContent='＋ Add'; add.onclick=async()=>{add.disabled=true; const res=await fetch(api('api/resources'),{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({name:d.name,url:d.url,verify_ssl:false,resource_type:'esphome',discovery_key:d.key||d.hostname})}); if(!res.ok){add.disabled=false;alert(await res.text());return;} await loadResources();await loadDiscoveredESPHome();}; actions.append(add); card.append(top,actions); host.append(card);
    }
  }
  async function loadDiscoveredESPHome(){ try{const res=await fetch(api('api/discovery/esphome'),{cache:'no-store'}); if(!res.ok)throw new Error(await res.text()); discoveryData=await res.json();renderDiscovery();}catch(e){$('discovered-esphome').innerHTML='<div class="empty">ESPHome discovery unavailable: '+String(e)+'</div>';}}

  function showEdit(r){$('edit-id').value=r.id;$('edit-name').value=r.name;$('edit-url').value=r.url;$('edit-verify').checked=r.verify_ssl!==false;editDialog.showModal();}
  function closeEdit(){if(editDialog.open)editDialog.close();}
  $('edit-form').addEventListener('submit',async e=>{e.preventDefault();const id=$('edit-id').value;const res=await fetch(api('api/resources/'+id),{method:'PUT',headers:{'Content-Type':'application/json'},body:JSON.stringify({name:$('edit-name').value,url:$('edit-url').value,verify_ssl:$('edit-verify').checked})});if(!res.ok){alert(await res.text());return;}const updated=await res.json();const s=sessions.get(id);if(s){s.resource=updated;s.label.textContent=updated.name;s.tab.title=updated.name;s.frame.title=updated.name;s.frame.src=api('proxy/'+id+'/');}closeEdit();updateNavigation();await loadResources();});

  homeTab.addEventListener('click',()=>setActive(null)); backButton.addEventListener('click',()=>navigate('back')); forwardButton.addEventListener('click',()=>navigate('forward')); reloadButton.addEventListener('click',()=>navigate('reload'));
  $('edit-close').addEventListener('click',closeEdit); $('edit-cancel').addEventListener('click',closeEdit);
  $('toggle-add').addEventListener('click',()=>{$('add-panel').hidden=!$('add-panel').hidden; if(!$('add-panel').hidden)$('name').focus();});
  $('refresh-all').addEventListener('click',async()=>{await Promise.all([loadResources(),loadDiscoveredESPHome()]);});
  $('resource-search').addEventListener('input',renderResources); $('resource-filter').addEventListener('change',renderResources); $('discovery-search').addEventListener('input',renderDiscovery); $('discovery-address-filter').addEventListener('change',renderDiscovery);
  $('collapse-discovery').addEventListener('click',()=>{const p=$('discovery-panel');p.classList.toggle('collapsed');$('collapse-discovery').title=p.classList.contains('collapsed')?'Expand discovered devices':'Collapse discovered devices';});
  $('add-form').addEventListener('submit',async e=>{e.preventDefault();const res=await fetch(api('api/resources'),{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({name:$('name').value,url:$('url').value,verify_ssl:$('verify').checked})});if(!res.ok){alert(await res.text());return;}e.target.reset();$('verify').checked=true;$('add-panel').hidden=true;await loadResources();await loadDiscoveredESPHome();});

  loadResources(); loadDiscoveredESPHome(); setInterval(loadDiscoveredESPHome,10000);
</script>
</body>
</html>'''
