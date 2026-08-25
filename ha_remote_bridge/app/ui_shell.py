"""Tabbed browser-style UI for HA Remote Bridge."""

INDEX_HTML = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>HA Remote Bridge</title>
  <style>
    :root { color-scheme: light dark; font-family: system-ui, sans-serif; }
    * { box-sizing: border-box; }
    html, body { width: 100%; height: 100%; margin: 0; }
    body { background: var(--primary-background-color, #fafafa); color: var(--primary-text-color, #222); overflow: hidden; }
    .shell { height: 100vh; display: flex; flex-direction: column; min-height: 0; }
    .topbar { background: var(--card-background-color, #fff); border-bottom: 1px solid #8883; box-shadow: 0 1px 5px #0002; z-index: 10; }
    .tabs { display: flex; align-items: end; gap: 4px; padding: 8px 10px 0; overflow-x: auto; scrollbar-width: thin; }
    .tab { display: inline-flex; align-items: center; gap: 8px; min-width: 110px; max-width: 230px; height: 38px; padding: 0 10px; border: 1px solid transparent; border-radius: 9px 9px 0 0; background: #8881; color: inherit; cursor: pointer; user-select: none; white-space: nowrap; font: inherit; }
    .tab:hover { background: #8882; }
    .tab.active { background: var(--primary-background-color, #fafafa); border-color: #8883; border-bottom-color: var(--primary-background-color, #fafafa); }
    .tab-label { overflow: hidden; text-overflow: ellipsis; flex: 1; }
    .tab-close { display: inline-grid; place-items: center; width: 22px; height: 22px; border-radius: 50%; border: 0; padding: 0; background: transparent; color: inherit; font: inherit; line-height: 1; cursor: pointer; }
    .tab-close:hover { background: #8883; }
    .nav { display: flex; align-items: center; gap: 6px; min-height: 46px; padding: 6px 10px; border-top: 1px solid #8882; }
    .nav button { width: 36px; height: 34px; padding: 0; border: 0; border-radius: 8px; cursor: pointer; font-size: 18px; background: #8882; color: inherit; }
    .nav button:hover:not(:disabled) { background: #8883; }
    .nav button:disabled { opacity: .35; cursor: default; }
    .nav-title { min-width: 0; flex: 1; margin-left: 5px; padding: 7px 10px; border-radius: 8px; background: #8881; font-size: 13px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; opacity: .82; }
    .views { position: relative; flex: 1; min-height: 0; }
    .view { position: absolute; inset: 0; display: none; }
    .view.active { display: block; }
    .home-view { overflow: auto; }
    .home { max-width: 900px; margin: 0 auto; padding: 24px; }
    h1 { margin: 0 0 4px; font-size: 28px; }
    h2 { margin: 0; font-size: 20px; }
    .subtitle { opacity: .7; margin: 0 0 24px; }
    .card { background: var(--card-background-color, #fff); border-radius: 12px; padding: 18px; margin-bottom: 16px; box-shadow: 0 2px 8px #0002; }
    .row { display: flex; gap: 12px; align-items: center; justify-content: space-between; }
    .resource-name { font-weight: 650; font-size: 17px; }
    .resource-url { opacity: .7; font-size: 13px; overflow-wrap: anywhere; margin-top: 3px; }
    .resource-meta { opacity: .6; font-size: 12px; margin-top: 4px; }
    .actions { display: flex; gap: 8px; flex-wrap: wrap; }
    button.action { border: 0; border-radius: 8px; padding: 10px 14px; cursor: pointer; text-decoration: none; font: inherit; background: var(--primary-color, #03a9f4); color: white; }
    button.secondary { background: #607d8b; }
    button.danger { background: #c62828; }
    form.resource-form { display: grid; grid-template-columns: 1fr 2fr auto auto; gap: 10px; align-items: end; }
    form.edit-form { display: grid; gap: 14px; }
    label { font-size: 12px; opacity: .8; display: grid; gap: 5px; }
    input[type=text], input[type=url] { padding: 10px; border: 1px solid #8887; border-radius: 8px; background: transparent; color: inherit; font: inherit; }
    .empty { opacity: .65; text-align: center; padding: 28px 4px; }
    .note { font-size: 13px; opacity: .7; }
    .session-frame { display: block; width: 100%; height: 100%; border: 0; background: white; }
    dialog { width: min(560px, calc(100vw - 28px)); border: 0; border-radius: 14px; padding: 0; background: var(--card-background-color, #fff); color: inherit; box-shadow: 0 16px 60px #0007; }
    dialog::backdrop { background: #0008; }
    .dialog-body { padding: 20px; }
    .dialog-head { display: flex; justify-content: space-between; align-items: center; gap: 12px; margin-bottom: 18px; }
    .dialog-close { border: 0; background: transparent; color: inherit; cursor: pointer; font-size: 24px; line-height: 1; padding: 4px 8px; border-radius: 8px; }
    .dialog-close:hover { background: #8882; }
    .dialog-actions { display: flex; justify-content: flex-end; gap: 8px; margin-top: 6px; }
    .checkbox-row { display: flex; align-items: center; gap: 8px; font-size: 14px; opacity: .9; }
    @media (max-width: 700px) {
      .home { padding: 14px; }
      form.resource-form { grid-template-columns: 1fr; }
      .row { align-items: flex-start; flex-direction: column; }
      .tab { min-width: 95px; max-width: 170px; }
      .nav-title { display: none; }
    }
  </style>
</head>
<body>
<div class="shell">
  <header class="topbar">
    <div id="tabs" class="tabs">
      <button id="home-tab" class="tab active" type="button" title="Home">
        <span class="tab-label">Home</span>
      </button>
    </div>
    <div class="nav">
      <button id="back" type="button" title="Back" disabled>&larr;</button>
      <button id="forward" type="button" title="Forward" disabled>&rarr;</button>
      <button id="reload" type="button" title="Reload" disabled>&#8635;</button>
      <div id="nav-title" class="nav-title">HA Remote Bridge</div>
    </div>
  </header>

  <div id="views" class="views">
    <section id="home-view" class="view home-view active">
      <main class="home">
        <h1>HA Remote Bridge</h1>
        <p class="subtitle">Secure access to local resources through Home Assistant Ingress.</p>

        <section class="card">
          <form id="add-form" class="resource-form">
            <label>Name<input id="name" type="text" required placeholder="Kitchen ESPHome"></label>
            <label>Local URL<input id="url" type="url" required placeholder="http://192.168.1.50"></label>
            <label><span>Verify SSL</span><input id="verify" type="checkbox" checked></label>
            <button class="action" type="submit">Add resource</button>
          </form>
          <p class="note">HTTP/HTTPS, target login cookies, WebSockets and Server-Sent Events are supported. Credentials embedded in URLs are rejected.</p>
        </section>

        <section id="resources"></section>
      </main>
    </section>
  </div>
</div>

<dialog id="edit-dialog">
  <div class="dialog-body">
    <div class="dialog-head">
      <h2>Edit resource</h2>
      <button id="edit-close" class="dialog-close" type="button" aria-label="Close">×</button>
    </div>
    <form id="edit-form" class="edit-form">
      <input id="edit-id" type="hidden">
      <label>Name<input id="edit-name" type="text" required></label>
      <label>Local URL<input id="edit-url" type="url" required></label>
      <label class="checkbox-row"><input id="edit-verify" type="checkbox"> Verify SSL certificate</label>
      <div class="dialog-actions">
        <button id="edit-cancel" class="action secondary" type="button">Cancel</button>
        <button class="action" type="submit">Save changes</button>
      </div>
    </form>
  </div>
</dialog>

<script>
  const base = window.location.pathname.endsWith('/') ? window.location.pathname : window.location.pathname + '/';
  const api = (path) => base + path;
  const sessions = new Map();
  let activeSessionId = null;

  const tabs = document.getElementById('tabs');
  const views = document.getElementById('views');
  const homeTab = document.getElementById('home-tab');
  const homeView = document.getElementById('home-view');
  const backButton = document.getElementById('back');
  const forwardButton = document.getElementById('forward');
  const reloadButton = document.getElementById('reload');
  const navTitle = document.getElementById('nav-title');
  const editDialog = document.getElementById('edit-dialog');
  const editForm = document.getElementById('edit-form');

  function currentSession() {
    return activeSessionId ? sessions.get(activeSessionId) : null;
  }

  function updateNavigation() {
    const session = currentSession();
    const enabled = Boolean(session);
    backButton.disabled = !enabled;
    forwardButton.disabled = !enabled;
    reloadButton.disabled = !enabled;
    navTitle.textContent = session ? session.resource.url : 'HA Remote Bridge';
  }

  function setActive(id) {
    activeSessionId = id;
    homeTab.classList.toggle('active', id === null);
    homeView.classList.toggle('active', id === null);

    for (const [sessionId, session] of sessions) {
      const active = sessionId === id;
      session.tab.classList.toggle('active', active);
      session.view.classList.toggle('active', active);
    }
    updateNavigation();
  }

  function openSession(resource) {
    const existing = sessions.get(resource.id);
    if (existing) {
      setActive(resource.id);
      return;
    }

    const tab = document.createElement('div');
    tab.className = 'tab';
    tab.title = resource.name;
    tab.tabIndex = 0;
    tab.setAttribute('role', 'tab');
    tab.setAttribute('aria-label', resource.name);

    const label = document.createElement('span');
    label.className = 'tab-label';
    label.textContent = resource.name;

    const close = document.createElement('button');
    close.type = 'button';
    close.className = 'tab-close';
    close.title = 'Close ' + resource.name;
    close.setAttribute('aria-label', 'Close ' + resource.name);
    close.textContent = '×';
    close.addEventListener('click', (event) => {
      event.stopPropagation();
      closeSession(resource.id);
    });

    tab.append(label, close);
    tab.addEventListener('click', () => setActive(resource.id));
    tab.addEventListener('keydown', (event) => {
      if (event.key === 'Enter' || event.key === ' ') {
        event.preventDefault();
        setActive(resource.id);
      }
    });
    tabs.append(tab);

    const view = document.createElement('section');
    view.className = 'view';
    view.dataset.sessionId = resource.id;

    const frame = document.createElement('iframe');
    frame.className = 'session-frame';
    frame.src = api('proxy/' + resource.id + '/');
    frame.title = resource.name;
    frame.addEventListener('load', () => {
      try {
        const title = frame.contentDocument && frame.contentDocument.title;
        if (title) {
          label.textContent = title;
          tab.title = title;
        }
      } catch (_) {}
      if (activeSessionId === resource.id) updateNavigation();
    });

    view.append(frame);
    views.append(view);
    sessions.set(resource.id, {resource, tab, label, view, frame});
    setActive(resource.id);
  }

  function closeSession(id) {
    const session = sessions.get(id);
    if (!session) return;

    const wasActive = activeSessionId === id;
    session.tab.remove();
    session.view.remove();
    sessions.delete(id);

    if (wasActive) {
      const remaining = Array.from(sessions.keys());
      setActive(remaining.length ? remaining[remaining.length - 1] : null);
    }
  }

  function navigate(kind) {
    const session = currentSession();
    if (!session) return;
    try {
      if (kind === 'back') session.frame.contentWindow.history.back();
      if (kind === 'forward') session.frame.contentWindow.history.forward();
      if (kind === 'reload') session.frame.contentWindow.location.reload();
    } catch (_) {
      if (kind === 'reload') session.frame.src = session.frame.src;
    }
  }

  function showEdit(resource) {
    document.getElementById('edit-id').value = resource.id;
    document.getElementById('edit-name').value = resource.name;
    document.getElementById('edit-url').value = resource.url;
    document.getElementById('edit-verify').checked = resource.verify_ssl !== false;
    editDialog.showModal();
  }

  function closeEdit() {
    if (editDialog.open) editDialog.close();
  }

  homeTab.addEventListener('click', () => setActive(null));
  backButton.addEventListener('click', () => navigate('back'));
  forwardButton.addEventListener('click', () => navigate('forward'));
  reloadButton.addEventListener('click', () => navigate('reload'));
  document.getElementById('edit-close').addEventListener('click', closeEdit);
  document.getElementById('edit-cancel').addEventListener('click', closeEdit);

  editForm.addEventListener('submit', async (event) => {
    event.preventDefault();
    const resourceId = document.getElementById('edit-id').value;
    const response = await fetch(api('api/resources/' + resourceId), {
      method: 'PUT',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({
        name: document.getElementById('edit-name').value,
        url: document.getElementById('edit-url').value,
        verify_ssl: document.getElementById('edit-verify').checked,
      }),
    });
    if (!response.ok) {
      alert(await response.text());
      return;
    }

    const updated = await response.json();
    const session = sessions.get(resourceId);
    if (session) {
      session.resource = updated;
      session.label.textContent = updated.name;
      session.tab.title = updated.name;
      session.frame.title = updated.name;
      session.frame.src = api('proxy/' + resourceId + '/');
    }
    closeEdit();
    updateNavigation();
    load();
  });

  async function load() {
    const response = await fetch(api('api/resources'));
    const resources = await response.json();
    const host = document.getElementById('resources');
    host.innerHTML = '';
    if (!resources.length) {
      host.innerHTML = '<div class="card empty">No resources configured yet.</div>';
      return;
    }

    for (const resource of resources) {
      const card = document.createElement('div');
      card.className = 'card row';
      const info = document.createElement('div');
      const name = document.createElement('div');
      name.className = 'resource-name';
      name.textContent = resource.name;
      const url = document.createElement('div');
      url.className = 'resource-url';
      url.textContent = resource.url;
      const meta = document.createElement('div');
      meta.className = 'resource-meta';
      meta.textContent = 'TLS verification: ' + (resource.verify_ssl === false ? 'off' : 'on');
      info.append(name, url, meta);

      const actions = document.createElement('div');
      actions.className = 'actions';
      const open = document.createElement('button');
      open.type = 'button';
      open.className = 'action';
      open.textContent = sessions.has(resource.id) ? 'Show' : 'Open';
      open.onclick = () => openSession(resource);

      const edit = document.createElement('button');
      edit.type = 'button';
      edit.className = 'action secondary';
      edit.textContent = 'Edit';
      edit.onclick = () => showEdit(resource);

      const remove = document.createElement('button');
      remove.type = 'button';
      remove.className = 'action danger';
      remove.textContent = 'Delete';
      remove.onclick = async () => {
        if (!confirm('Delete ' + resource.name + '?')) return;
        closeSession(resource.id);
        await fetch(api('api/resources/' + resource.id), {method: 'DELETE'});
        load();
      };
      actions.append(open, edit, remove);
      card.append(info, actions);
      host.append(card);
    }
  }

  document.getElementById('add-form').addEventListener('submit', async (event) => {
    event.preventDefault();
    const response = await fetch(api('api/resources'), {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({
        name: document.getElementById('name').value,
        url: document.getElementById('url').value,
        verify_ssl: document.getElementById('verify').checked,
      }),
    });
    if (!response.ok) {
      alert(await response.text());
      return;
    }
    event.target.reset();
    document.getElementById('verify').checked = true;
    load();
  });

  load();
</script>
</body>
</html>
"""
