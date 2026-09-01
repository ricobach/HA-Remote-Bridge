"""Improved SMB diagnostics and credential testing for HA Remote Bridge."""

from __future__ import annotations

import json

from aiohttp import web

import smb_support as base

# Keep the original client runner before installing the friendly-error wrapper.
_original_run_smbclient = base._run_smbclient


def _friendly_smb_error(message: str, resource: dict) -> str:
    """Translate common Samba NT status errors into actionable UI messages."""
    raw = (message or "").strip()
    upper = raw.upper()
    credential = base.VAULT.get(resource.get("smb_credential_id"))
    identity = (
        ((credential.get("domain") + "\\") if credential and credential.get("domain") else "")
        + (credential.get("username") if credential else "Guest / anonymous")
    )

    if "NT_STATUS_LOGON_FAILURE" in upper:
        if credential is None:
            return "SMB authentication failed: this server rejected Guest / anonymous access. Select an SMB credential and try again."
        return f"SMB authentication failed for {identity}. Check the username, password, and Domain / Workgroup."
    if "NT_STATUS_NO_SUCH_USER" in upper:
        return f"SMB user {identity} was not found on the server. Check the username and Domain / Workgroup."
    if "NT_STATUS_ACCOUNT_DISABLED" in upper:
        return f"SMB account {identity} is disabled on the server."
    if "NT_STATUS_ACCOUNT_LOCKED_OUT" in upper:
        return f"SMB account {identity} is locked out on the server."
    if "NT_STATUS_PASSWORD_EXPIRED" in upper or "NT_STATUS_PASSWORD_MUST_CHANGE" in upper:
        return f"The password for SMB account {identity} has expired or must be changed."
    if "NT_STATUS_ACCESS_DENIED" in upper:
        return f"SMB access was denied for {identity}. The credentials may be valid, but this account does not have permission for the requested operation."
    if "NT_STATUS_BAD_NETWORK_NAME" in upper:
        return "The SMB share does not exist or is not available to this account."
    if "NT_STATUS_IO_TIMEOUT" in upper:
        return "The SMB server stopped responding before the operation completed."
    return raw or "SMB request failed"


async def _translated_run_smbclient(resource: dict, extra: list[str], timeout: float = 8) -> str:
    try:
        return await _original_run_smbclient(resource, extra, timeout=timeout)
    except web.HTTPException as err:
        message = _friendly_smb_error(err.text or err.reason, resource)
        if err.status == 504:
            raise web.HTTPGatewayTimeout(text=message) from err
        if err.status >= 500:
            raise web.HTTPBadGateway(text=message) from err
        raise web.HTTPBadRequest(text=message) from err


# Existing base handlers resolve this global at request time, so installing the
# wrapper upgrades share listing, directory browsing, and downloads too.
base._run_smbclient = _translated_run_smbclient


async def test_connection(request: web.Request) -> web.Response:
    """Test a configured host/port and selected reusable SMB credential."""
    try:
        payload = await request.json()
    except (json.JSONDecodeError, ValueError):
        raise web.HTTPBadRequest(text="Invalid JSON")

    await base.VAULT.load()
    # Reuse the same resource validation as normal SMB resources.
    name, host, port, credential_id = base.validate_smb_payload(
        {
            "name": "SMB connection test",
            "smb_host": payload.get("smb_host", ""),
            "smb_port": payload.get("smb_port", 445),
            "smb_credential_id": payload.get("smb_credential_id", ""),
        }
    )
    del name
    resource = {
        "id": "test",
        "name": "SMB connection test",
        "resource_type": "smb",
        "smb_host": host,
        "smb_port": port,
        "smb_credential_id": credential_id,
    }

    try:
        raw = await _translated_run_smbclient(resource, ["-L", host], timeout=8)
    except web.HTTPException as err:
        return web.json_response({"ok": False, "error": err.text or err.reason}, status=err.status)

    share_count = 0
    for line in raw.splitlines():
        fields = line.split("|")
        if len(fields) >= 2 and fields[0].strip().lower() in {"disk", "disk share"}:
            name = fields[1].strip()
            if name and not name.endswith("$"):
                share_count += 1

    credential = base.VAULT.get(credential_id)
    identity = "Guest / anonymous"
    if credential:
        identity = ((credential.get("domain") + "\\") if credential.get("domain") else "") + credential.get("username", "")
    return web.json_response({"ok": True, "identity": identity, "shares": share_count})


# Public interface expected by the runtime.
VAULT = base.VAULT
validate_smb_payload = base.validate_smb_payload
smb_resource_url = base.smb_resource_url
list_credentials = base.list_credentials
add_credential = base.add_credential
delete_credential = base.delete_credential
list_shares = base.list_shares
list_directory = base.list_directory
download_file = base.download_file
probe_smb_resource = base.probe_smb_resource
smb_page = base.smb_page
