"""Virtual Host/SNI editor and address-bar label for HA Remote Bridge 0.5.8."""

from __future__ import annotations

import re

from ui_shell_v22 import INDEX_HTML as BASE_INDEX_HTML

INDEX_HTML = BASE_INDEX_HTML


def _append_after_label(html: str, input_id: str, addition: str) -> str:
    pattern = rf'(<label>[^<]*<input id="{re.escape(input_id)}"[^>]*></label>)'
    updated, count = re.subn(pattern, rf'\1{addition}', html, count=1)
    if count != 1:
        raise RuntimeError(f"Virtual-host UI composition failed: input {input_id} not found")
    return updated


INDEX_HTML = _append_after_label(
    INDEX_HTML,
    "url",
    '<label>Virtual host / SNI <span style="font-weight:400">(optional)</span><input id="virtual-host" type="text" placeholder="www.example.com" autocomplete="off"></label>',
)
INDEX_HTML = _append_after_label(
    INDEX_HTML,
    "edit-url",
    '<label>Virtual host / SNI <span style="font-weight:400">(optional)</span><input id="edit-virtual-host" type="text" placeholder="www.example.com" autocomplete="off"></label>',
)

# Persist the virtual host in Web create/update requests. SSH/VNC/SMB editors
# remain untouched because this setting is specifically an HTTP/TLS concept.
old_add = "JSON.stringify({name:$('name').value,group_name:$('group-name').value,url:$('url').value,verify_ssl:$('verify').checked})"
new_add = "JSON.stringify({name:$('name').value,group_name:$('group-name').value,url:$('url').value,virtual_host:$('virtual-host').value,verify_ssl:$('verify').checked})"
if old_add not in INDEX_HTML:
    raise RuntimeError("Virtual-host UI composition failed: Web add payload signature changed")
INDEX_HTML = INDEX_HTML.replace(old_add, new_add, 1)

old_edit = "JSON.stringify({name:$('edit-name').value,group_name:$('edit-group-name').value,url:$('edit-url').value,verify_ssl:$('edit-verify').checked})"
new_edit = "JSON.stringify({name:$('edit-name').value,group_name:$('edit-group-name').value,url:$('edit-url').value,virtual_host:$('edit-virtual-host').value,verify_ssl:$('edit-verify').checked})"
if old_edit not in INDEX_HTML:
    raise RuntimeError("Virtual-host UI composition failed: Web edit payload signature changed")
INDEX_HTML = INDEX_HTML.replace(old_edit, new_edit, 1)

old_populate = "$('edit-name').value=r.name;$('edit-group-name').value=r.group_name||'';$('edit-url').value=r.url;"
new_populate = "$('edit-name').value=r.name;$('edit-group-name').value=r.group_name||'';$('edit-url').value=r.url;$('edit-virtual-host').value=r.virtual_host||'';"
if old_populate not in INDEX_HTML:
    raise RuntimeError("Virtual-host UI composition failed: Web edit population signature changed")
INDEX_HTML = INDEX_HTML.replace(old_populate, new_populate, 1)

VHOST_CSS = r'''
    /* 0.5.8: virtual-host identity is informational in the address bar. */
    .hrb-virtual-host-prefix { font-weight:600; }
'''
INDEX_HTML = INDEX_HTML.replace("  </style>", VHOST_CSS + "\n  </style>", 1)

# The read-only address bar was introduced in ui_shell_v18. Keep its endpoint
# URL exactly as before and prefix only the optional virtual hostname.
old_address = """    const value=locationFor(session);\n    if(value!==last){\n      last=value;\n      address.textContent=value;\n      address.title=value+' — read only';\n      address.classList.toggle('hrb-address-secure',value.startsWith('https://'));\n      address.classList.toggle('hrb-address-plain',!value.startsWith('https://'));\n    }"""
new_address = """    const endpointValue=locationFor(session);\n    const virtualHost=String((session.resource||{}).virtual_host||'').trim();\n    const value=virtualHost?'('+virtualHost+') '+endpointValue:endpointValue;\n    if(value!==last){\n      last=value;\n      address.textContent=value;\n      address.title=(virtualHost?'Virtual host / SNI: '+virtualHost+' · ':'')+endpointValue+' — read only';\n      address.classList.toggle('hrb-address-secure',endpointValue.startsWith('https://'));\n      address.classList.toggle('hrb-address-plain',!endpointValue.startsWith('https://'));\n    }"""
if old_address not in INDEX_HTML:
    raise RuntimeError("Virtual-host UI composition failed: read-only address signature changed")
INDEX_HTML = INDEX_HTML.replace(old_address, new_address, 1)

for required in (
    'id="virtual-host"',
    'id="edit-virtual-host"',
    "virtual_host:$('virtual-host').value",
    "r.virtual_host||''",
    "'('+virtualHost+') '+endpointValue",
):
    if required not in INDEX_HTML:
        raise RuntimeError(f"Virtual-host UI composition failed: missing {required}")
