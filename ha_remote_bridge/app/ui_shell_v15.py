"""Sorting and ESPHome filtering for HA Remote Bridge 0.4.2."""

from ui_shell_v14 import INDEX_HTML as BASE_INDEX_HTML

INDEX_HTML = BASE_INDEX_HTML

SORT_FILTER_CSS = r'''
    /* 0.4.2: explicit ESPHome filtering and compact host sorting. */
    .compact-filter-row { align-items:center; }
    .hrb-sort-select {
      flex:0 0 auto;
      height:32px;
      min-height:32px;
      max-width:150px;
      padding:0 28px 0 10px;
      border:1px solid var(--border);
      border-radius:16px;
      background:var(--surface);
      color:var(--text);
      font-size:12px;
    }
    @media (max-width:760px) {
      .hrb-sort-select { max-width:128px; }
    }
'''
INDEX_HTML = INDEX_HTML.replace("  </style>", SORT_FILTER_CSS + "\n  </style>", 1)

SORT_FILTER_JS = r'''
<script>
(function installSortAndESPHomeFilter(){
  const SORT_KEY='ha_remote_bridge.host_sort.v1';
  let sorting=false;

  function resourceHostText(card){
    const node=card.querySelector('.group-host');
    return (node?node.textContent:'').trim();
  }
  function resourceNameText(card){
    const node=card.querySelector('.group-name');
    return (node?node.textContent:'').trim();
  }
  function statusRank(card){
    const text=(card.querySelector('.group-health')?.textContent||'').toLowerCase();
    if(text.includes('online'))return 0;
    if(text.includes('attention')||text.includes('offline'))return 1;
    return 2;
  }
  function connectionCount(card){return card.querySelectorAll('.connection-row').length;}
  function natural(a,b){return String(a).localeCompare(String(b),undefined,{numeric:true,sensitivity:'base'});}
  function currentSort(){
    const select=document.getElementById('hrb-sort');
    return select?select.value:(localStorage.getItem(SORT_KEY)||'name-asc');
  }
  function compareCards(a,b,mode){
    if(mode==='name-desc')return natural(resourceNameText(b),resourceNameText(a));
    if(mode==='host')return natural(resourceHostText(a),resourceHostText(b))||natural(resourceNameText(a),resourceNameText(b));
    if(mode==='status')return statusRank(a)-statusRank(b)||natural(resourceNameText(a),resourceNameText(b));
    if(mode==='connections')return connectionCount(b)-connectionCount(a)||natural(resourceNameText(a),resourceNameText(b));
    return natural(resourceNameText(a),resourceNameText(b));
  }
  function applySort(){
    if(sorting)return;
    const host=document.getElementById('resources');
    if(!host)return;
    const cards=[...host.children].filter(x=>x.classList&&x.classList.contains('connection-group-card'));
    if(cards.length<2)return;
    const wanted=[...cards].sort((a,b)=>compareCards(a,b,currentSort()));
    if(wanted.every((card,i)=>card===cards[i]))return;
    sorting=true;
    const fragment=document.createDocumentFragment();
    wanted.forEach(card=>fragment.appendChild(card));
    host.appendChild(fragment);
    sorting=false;
  }
  window.hrbApplyHostSort=applySort;

  function setCompactFilter(value,button){
    window.hrbCompactFilter=value;
    const legacy=document.getElementById('resource-filter');
    if(legacy && [...legacy.options].some(o=>o.value===value))legacy.value=value;
    document.querySelectorAll('.compact-filter-chip').forEach(x=>x.classList.remove('active'));
    if(button)button.classList.add('active');
    if(typeof renderResources==='function')renderResources();
    setTimeout(applySort,0);
  }

  function installControls(){
    const row=document.querySelector('.compact-filter-row');
    if(!row)return false;

    if(!document.getElementById('hrb-esphome-filter')){
      const chip=document.createElement('button');
      chip.id='hrb-esphome-filter';
      chip.className='compact-filter-chip';
      chip.type='button';
      chip.textContent='ESPHome';
      chip.addEventListener('click',()=>setCompactFilter('esphome',chip));
      row.appendChild(chip);
    }

    if(!document.getElementById('hrb-sort')){
      const select=document.createElement('select');
      select.id='hrb-sort';
      select.className='hrb-sort-select';
      select.title='Sort configured hosts';
      for(const [value,label] of [
        ['name-asc','Name A–Z'],
        ['name-desc','Name Z–A'],
        ['host','Host / IP'],
        ['status','Status'],
        ['connections','Connections']
      ]){
        const option=document.createElement('option');option.value=value;option.textContent='Sort: '+label;select.appendChild(option);
      }
      const saved=localStorage.getItem(SORT_KEY)||'name-asc';
      if([...select.options].some(o=>o.value===saved))select.value=saved;
      select.addEventListener('change',()=>{localStorage.setItem(SORT_KEY,select.value);applySort();});
      row.appendChild(select);
    }
    applySort();
    return true;
  }

  const resources=document.getElementById('resources');
  if(resources){
    const observer=new MutationObserver(()=>{if(!sorting)setTimeout(applySort,0);});
    observer.observe(resources,{childList:true});
  }

  if(!installControls()){
    const observer=new MutationObserver(()=>{if(installControls())observer.disconnect();});
    observer.observe(document.documentElement,{childList:true,subtree:true});
  }

  // Re-apply sorting after health refreshes because Status sorting can change.
  setInterval(()=>{if(currentSort()==='status')applySort();},5000);
})();
</script>
'''

INDEX_HTML = INDEX_HTML.replace("</body>", SORT_FILTER_JS + "\n</body>", 1)

for required in ("hrb-esphome-filter", "hrb-sort", "ha_remote_bridge.host_sort.v1", "setCompactFilter('esphome'"):
    if required not in INDEX_HTML:
        raise RuntimeError(f"Sort/filter UI composition failed: missing {required}")
