"""SMB viewer parent-directory navigation for HA Remote Bridge 0.3.1."""

from __future__ import annotations

import html
from urllib.parse import quote

from aiohttp import web

import smb_support_v4 as previous

base = previous.base

# Make the SMB browser restorable to a particular share/folder. This lets the
# file viewer return to the exact parent directory instead of the share list.
SMB_PAGE = previous.SMB_PAGE
_old_state = "const resourceId='__RESOURCE_ID__';let share='';let path='';const $=id=>document.getElementById(id);const enc=v=>encodeURIComponent(v);"
_new_state = "const resourceId='__RESOURCE_ID__';const initial=new URLSearchParams(location.search);let share=initial.get('share')||'';let path=initial.get('path')||'';const $=id=>document.getElementById(id);const enc=v=>encodeURIComponent(v);"
if _old_state not in SMB_PAGE:
    raise RuntimeError("SMB parent-navigation composition failed: browser state initializer changed")
SMB_PAGE = SMB_PAGE.replace(_old_state, _new_state, 1)


async def smb_page(request: web.Request) -> web.Response:
    resource = base._resource(request)
    page = SMB_PAGE.replace("__RESOURCE_ID__", resource["id"])
    return web.Response(text=page, content_type="text/html", headers={"Cache-Control": "no-store"})


async def viewer_page(request: web.Request) -> web.Response:
    resource = base._resource(request)
    share = base._safe_share(request.query.get("share", ""))
    full_path = base._safe_path(request.query.get("path", ""))
    if not full_path:
        raise web.HTTPBadRequest(text="A file path is required")

    parent, _, filename = full_path.rpartition("/")
    kind, mime = previous._preview_kind(filename)
    q_share = quote(share, safe="")
    q_path = quote(full_path, safe="")
    q_parent = quote(parent, safe="")
    rid = resource["id"]

    raw_url = f"../../api/smb/{rid}/raw?share={q_share}&path={q_path}"
    text_url = f"../../api/smb/{rid}/text?share={q_share}&path={q_path}"
    download_url = f"../../api/smb/{rid}/download?share={q_share}&path={q_path}"
    # `./` is /smb/<resource>/ from the viewer route. Query state tells the
    # browser which share and exact directory to restore.
    browser_url = f"./?share={q_share}&path={q_parent}"

    if kind == "image":
        viewer = f'<img src="{html.escape(raw_url, quote=True)}" alt="">'
    elif kind == "pdf":
        viewer = f'<iframe src="{html.escape(raw_url, quote=True)}" title="PDF preview"></iframe>'
    elif kind == "audio":
        viewer = f'<audio controls autoplay src="{html.escape(raw_url, quote=True)}"></audio>'
    elif kind == "video":
        viewer = f'<video controls playsinline src="{html.escape(raw_url, quote=True)}"></video>'
    elif kind == "text":
        viewer = ""
    else:
        viewer = '<div class="unknown"><h2>No inline preview</h2><p>This file type is not supported by the built-in viewer.</p><p>Use Download to open it with another app.</p></div>'

    page = previous.VIEW_PAGE
    # Always return to the encoded parent directory. Do not use history.back(),
    # because Home Assistant/iOS WebViews can have unrelated navigation history.
    page = page.replace(
        "const back=document.getElementById('back');back.onclick=()=>history.length>1?history.back():location.replace('__BROWSER__');",
        "const back=document.getElementById('back');back.onclick=()=>location.replace('__BROWSER__');",
        1,
    )
    replacements = {
        "__NAME__": html.escape(filename),
        "__MIME__": html.escape(mime),
        "__VIEWER__": viewer,
        "__KIND__": kind,
        "__TEXT_API__": text_url,
        "__DOWNLOAD__": download_url,
        "__BROWSER__": browser_url,
    }
    for key, value in replacements.items():
        page = page.replace(key, value)
    return web.Response(text=page, content_type="text/html", headers={"Cache-Control": "no-store"})


# Public interface expected by the runtime.
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
