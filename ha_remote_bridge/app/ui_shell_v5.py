"""Persistent session-tab UI extensions for HA Remote Bridge."""

from ui_shell_v4 import INDEX_HTML as BASE_INDEX_HTML

INDEX_HTML = BASE_INDEX_HTML

# Make the SSH naming semantics explicit in the form.
INDEX_HTML = INDEX_HTML.replace(
    '<label>Name<input id="ssh-name" type="text" required placeholder="Server"></label>',
    '<label>Session Name<input id="ssh-name" type="text" required placeholder="Server"></label>',
)

# Keep tab labels tied to the configured session/resource name. Remote page
# titles are useful inside the iframe, but must not rename the bridge tab.
INDEX_HTML = INDEX_HTML.replace(
    "frame.addEventListener('load',()=>{try{const t=frame.contentDocument&&frame.contentDocument.title;if(t){label.textContent=t;tab.title=t;}}catch(_){}if(activeSessionId===resource.id)updateNavigation();});",
    "frame.addEventListener('load',()=>{if(activeSessionId===resource.id)updateNavigation();});",
)

# Persist only non-sensitive UI state: open resource IDs and the selected tab.
INDEX_HTML = INDEX_HTML.replace(
    "  const sessions = new Map();\n  let activeSessionId = null;",
    "  const sessions = new Map();\n"
    "  const SESSION_STATE_KEY = 'ha_remote_bridge.session_tabs.v1';\n"
    "  let sessionsRestored = false;\n"
    "  let activeSessionId = null;",
)

INDEX_HTML = INDEX_HTML.replace(
    "  function currentSession(){ return activeSessionId ? sessions.get(activeSessionId) : null; }\n"
    "  function updateNavigation(){ const s=currentSession(),on=Boolean(s); backButton.disabled=!on;forwardButton.disabled=!on;reloadButton.disabled=!on;navTitle.textContent=s?s.resource.url:'HA Remote Bridge'; }\n"
    "  function setActive(id){ activeSessionId=id;homeTab.classList.toggle('active',id===null);homeView.classList.toggle('active',id===null);for(const [sid,s] of sessions){const a=sid===id;s.tab.classList.toggle('active',a);s.view.classList.toggle('active',a);}updateNavigation(); }",
    "  function currentSession(){ return activeSessionId ? sessions.get(activeSessionId) : null; }\n"
    "  function saveSessionState(){try{localStorage.setItem(SESSION_STATE_KEY,JSON.stringify({open:[...sessions.keys()],active:activeSessionId}));}catch(_){}}\n"
    "  function updateNavigation(){ const s=currentSession(),on=Boolean(s); backButton.disabled=!on;forwardButton.disabled=!on;reloadButton.disabled=!on;navTitle.textContent=s?s.resource.url:'HA Remote Bridge'; }\n"
    "  function setActive(id){ activeSessionId=id;homeTab.classList.toggle('active',id===null);homeView.classList.toggle('active',id===null);for(const [sid,s] of sessions){const a=sid===id;s.tab.classList.toggle('active',a);s.view.classList.toggle('active',a);}updateNavigation();saveSessionState(); }",
)

INDEX_HTML = INDEX_HTML.replace(
    "  function closeSession(id){const s=sessions.get(id);if(!s)return;const active=activeSessionId===id;s.tab.remove();s.view.remove();sessions.delete(id);if(active){const ids=[...sessions.keys()];setActive(ids.length?ids[ids.length-1]:null);}}",
    "  function closeSession(id){const s=sessions.get(id);if(!s)return;const active=activeSessionId===id;if(resourceKind(s.resource)==='ssh'){fetch(api('api/ssh/sessions/'+id),{method:'DELETE'}).catch(()=>{});}s.tab.remove();s.view.remove();sessions.delete(id);if(active){const ids=[...sessions.keys()];setActive(ids.length?ids[ids.length-1]:null);}else{saveSessionState();}}",
)

# Restore sessions after configured resources are known. Invalid/deleted resource
# IDs are discarded automatically. Recreated iframes reconnect to their resource;
# SSH iframes reattach to the persistent tmux-backed terminal.
INDEX_HTML = INDEX_HTML.replace(
    "  async function loadResources(){const res=await fetch(api('api/resources'),{cache:'no-store'});resourceData=await res.json();renderResources();}",
    "  async function restoreSessionTabs(){if(sessionsRestored)return;sessionsRestored=true;let state=null;try{state=JSON.parse(localStorage.getItem(SESSION_STATE_KEY)||'null');}catch(_){}if(!state||!Array.isArray(state.open)){saveSessionState();return;}const byId=new Map(resourceData.map(r=>[r.id,r]));for(const id of state.open){const r=byId.get(id);if(r)openSession(r);}if(state.active===null){setActive(null);}else if(state.active&&sessions.has(state.active)){setActive(state.active);}else if(sessions.size){setActive([...sessions.keys()][sessions.size-1]);}else{setActive(null);}saveSessionState();}\n"
    "  async function loadResources(){const res=await fetch(api('api/resources'),{cache:'no-store'});resourceData=await res.json();renderResources();await restoreSessionTabs();}",
)
