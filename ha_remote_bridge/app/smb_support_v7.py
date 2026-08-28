"""Previous/next file navigation for SMB and ZIP viewers in HA Remote Bridge 0.4.4."""

from __future__ import annotations

import json
from urllib.parse import quote

from aiohttp import web

import smb_support_v6 as previous

base = previous.base


def _inject_navigation(page: str, *, script: str) -> str:
    """Add Previous/Next controls to the existing viewer without replacing it."""
    marker = '<button id="back" type="button">← Back</button>'
    if marker not in page:
        raise RuntimeError("File navigation composition failed: viewer Back button changed")
    controls = (
        marker
        + '<button id="file-prev" type="button" disabled title="Previous file">‹ Previous</button>'
        + '<button id="file-next" type="button" disabled title="Next file">Next ›</button>'
    )
    page = page.replace(marker, controls, 1)
    if "</script></body>" not in page:
        raise RuntimeError("File navigation composition failed: viewer script footer changed")
    return page.replace("</script></body>", script + "\n</script></body>", 1)


async def viewer_page(request: web.Request) -> web.Response:
    """Normal SMB viewer with sibling-file Previous/Next navigation."""
    response = await previous.viewer_page(request)
    # ZIP files return the ZIP browser rather than the generic viewer, so leave
    # that page alone. Nested ZIP entries are handled by zip_entry_page below.
    full_path = base._safe_path(request.query.get("path", ""))
    if full_path.lower().endswith(".zip"):
        return response

    resource = base._resource(request)
    share = base._safe_share(request.query.get("share", ""))
    parent, _, filename = full_path.rpartition("/")
    rid = resource["id"]
    q_share = quote(share, safe="")
    q_parent = quote(parent, safe="")

    script = f"""
const filePrev=document.getElementById('file-prev'),fileNext=document.getElementById('file-next');
const siblingApi='../../api/smb/{rid}/list?share={q_share}&path={q_parent}';
const currentFile={json.dumps(filename)};
const parentPath={json.dumps(parent)};
const viewerShare={json.dumps(share)};
let siblingFiles=[];
function siblingPath(name){{return [parentPath,name].filter(Boolean).join('/');}}
function openSibling(index){{
  if(index<0||index>=siblingFiles.length)return;
  location.href='view?share='+encodeURIComponent(viewerShare)+'&path='+encodeURIComponent(siblingPath(siblingFiles[index].name));
}}
async function loadSiblingNavigation(){{
  try{{
    const r=await fetch(siblingApi,{{cache:'no-store'}});const d=await r.json();
    if(!r.ok)throw new Error(d.error||'Unable to list folder');
    siblingFiles=(d.items||[]).filter(item=>!item.directory);
    const index=siblingFiles.findIndex(item=>item.name===currentFile);
    filePrev.disabled=index<=0;fileNext.disabled=index<0||index>=siblingFiles.length-1;
    filePrev.onclick=()=>openSibling(index-1);fileNext.onclick=()=>openSibling(index+1);
  }}catch(e){{console.warn('Unable to load sibling-file navigation',e);filePrev.disabled=true;fileNext.disabled=true;}}
}}
loadSiblingNavigation();
document.addEventListener('keydown',e=>{{
  if(e.altKey||e.ctrlKey||e.metaKey||e.shiftKey)return;
  const tag=(e.target&&e.target.tagName||'').toLowerCase();if(tag==='input'||tag==='textarea'||tag==='select')return;
  if(e.key==='ArrowLeft'&&!filePrev.disabled){{e.preventDefault();filePrev.click();}}
  if(e.key==='ArrowRight'&&!fileNext.disabled){{e.preventDefault();fileNext.click();}}
}});
"""
    page = _inject_navigation(response.text, script=script)
    response.text = page
    return response


async def zip_entry_page(request: web.Request) -> web.Response:
    """Nested ZIP-entry viewer with Previous/Next within the current ZIP folder."""
    response = await previous.zip_entry_page(request)
    resource = base._resource(request)
    share = base._safe_share(request.query.get("share", ""))
    full_path = base._safe_path(request.query.get("path", ""))
    entry = previous._safe_entry_name(request.query.get("entry", ""))
    folder = request.query.get("folder", "").replace("\\", "/").strip("/")
    if folder:
        folder = previous._safe_entry_name(folder)

    rid = resource["id"]
    q_share = quote(share, safe="")
    q_path = quote(full_path, safe="")
    q_folder = quote(folder, safe="")

    script = f"""
const filePrev=document.getElementById('file-prev'),fileNext=document.getElementById('file-next');
const zipSiblingApi='../../api/smb/{rid}/zip/list?share={q_share}&path={q_path}&folder={q_folder}';
const currentEntry={json.dumps(entry)};
const zipShare={json.dumps(share)},zipPath={json.dumps(full_path)},zipFolder={json.dumps(folder)};
let zipSiblingFiles=[];
function openZipSibling(index){{
  if(index<0||index>=zipSiblingFiles.length)return;
  const item=zipSiblingFiles[index];
  location.href='zip-entry?share='+encodeURIComponent(zipShare)+'&path='+encodeURIComponent(zipPath)+'&entry='+encodeURIComponent(item.entry)+(zipFolder?'&folder='+encodeURIComponent(zipFolder):'');
}}
async function loadZipSiblingNavigation(){{
  try{{
    const r=await fetch(zipSiblingApi,{{cache:'no-store'}});const d=await r.json();
    if(!r.ok)throw new Error(d.error||'Unable to list ZIP folder');
    zipSiblingFiles=(d.items||[]).filter(item=>!item.directory);
    const index=zipSiblingFiles.findIndex(item=>item.entry===currentEntry);
    filePrev.disabled=index<=0;fileNext.disabled=index<0||index>=zipSiblingFiles.length-1;
    filePrev.onclick=()=>openZipSibling(index-1);fileNext.onclick=()=>openZipSibling(index+1);
  }}catch(e){{console.warn('Unable to load ZIP sibling navigation',e);filePrev.disabled=true;fileNext.disabled=true;}}
}}
loadZipSiblingNavigation();
document.addEventListener('keydown',e=>{{
  if(e.altKey||e.ctrlKey||e.metaKey||e.shiftKey)return;
  const tag=(e.target&&e.target.tagName||'').toLowerCase();if(tag==='input'||tag==='textarea'||tag==='select')return;
  if(e.key==='ArrowLeft'&&!filePrev.disabled){{e.preventDefault();filePrev.click();}}
  if(e.key==='ArrowRight'&&!fileNext.disabled){{e.preventDefault();fileNext.click();}}
}});
"""
    page = _inject_navigation(response.text, script=script)
    response.text = page
    return response


# Public interface expected by the existing runtime layers.
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
smb_page = previous.smb_page
zip_list = previous.zip_list
zip_raw = previous.zip_raw
zip_text = previous.zip_text
