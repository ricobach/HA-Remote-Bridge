"""Clickable SMB path breadcrumbs for HA Remote Bridge 0.4.5."""

from __future__ import annotations

from aiohttp import web

import smb_support_v7 as previous


BREADCRUMB_CSS = r'''
.crumbs{display:flex;align-items:center;gap:2px;min-width:0;white-space:nowrap;overflow-x:auto;scrollbar-width:none}
.crumbs::-webkit-scrollbar{display:none}
.crumb-link{border:0;background:transparent;color:var(--accent);padding:4px 2px;border-radius:4px;font:inherit;cursor:pointer;flex:0 0 auto}
.crumb-link:hover{text-decoration:underline}
.crumb-link:focus-visible{outline:2px solid var(--accent);outline-offset:1px}
.crumb-current{color:var(--muted);padding:4px 2px;flex:0 0 auto}
.crumb-sep{color:var(--muted);opacity:.75;flex:0 0 auto;user-select:none}
'''

OLD_CRUMBS = "function crumbs(){const bits=[];if(share)bits.push(share);if(path)bits.push(...path.split('/'));$('crumbs').textContent=bits.length?bits.join(' / '):'Shares';$('up').disabled=!share;}"
NEW_CRUMBS = r'''function crumbs(){
 const host=$('crumbs');host.innerHTML='';
 const addSep=()=>{const s=document.createElement('span');s.className='crumb-sep';s.textContent='/';host.append(s);};
 const addLink=(label,targetShare,targetPath)=>{const b=document.createElement('button');b.type='button';b.className='crumb-link';b.textContent=label;b.onclick=()=>{share=targetShare;path=targetPath;load();};host.append(b);};
 const addCurrent=label=>{const s=document.createElement('span');s.className='crumb-current';s.textContent=label;host.append(s);};
 if(!share){addCurrent('Shares');}
 else{
   const parts=path?path.split('/').filter(Boolean):[];
   if(parts.length){addLink(share,share,'');}else addCurrent(share);
   let built='';
   parts.forEach((part,index)=>{addSep();built=built?(built+'/'+part):part;if(index===parts.length-1)addCurrent(part);else addLink(part,share,built);});
 }
 const state=new URLSearchParams();if(share)state.set('share',share);if(path)state.set('path',path);
 const query=state.toString();history.replaceState(null,'',location.pathname+(query?('?'+query):''));
 $('up').disabled=!share;
 host.scrollLeft=host.scrollWidth;
}'''


async def smb_page(request: web.Request) -> web.Response:
    """Render the existing SMB browser with clickable path breadcrumbs."""
    response = await previous.smb_page(request)
    page = response.text
    if OLD_CRUMBS not in page:
        raise RuntimeError("SMB breadcrumb composition failed: breadcrumb renderer changed")
    if "</style>" not in page:
        raise RuntimeError("SMB breadcrumb composition failed: style footer missing")
    page = page.replace("</style>", BREADCRUMB_CSS + "\n</style>", 1)
    page = page.replace(OLD_CRUMBS, NEW_CRUMBS, 1)
    response.text = page
    return response


# Public interface expected by the current runtime layers.
VAULT = previous.VAULT
validate_smb_payload = previous.validate_smb_payload
smb_resource_url = previous.smb_resource_url
list_credentials = previous.list_credentials
add_credential = previous.add_credential
delete_credential = previous.delete_credential
list_shares = previous.list_shares
list_directory = previous.list_directory
download_file = previous.download_file
probe_smb_resource = previous.probe_smb_resource
test_connection = previous.test_connection
raw_file = previous.raw_file
text_preview = previous.text_preview
viewer_page = previous.viewer_page
zip_list = previous.zip_list
zip_raw = previous.zip_raw
zip_text = previous.zip_text
zip_entry_page = previous.zip_entry_page
