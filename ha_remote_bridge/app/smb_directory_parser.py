"""Robust SMB directory listing parser for HA Remote Bridge."""

from __future__ import annotations

import re

import main
import smb_support_v2 as previous

# smbclient -g is documented as a parse-friendly mode for -L share listings, but
# normal `ls` output is not guaranteed to use that same pipe-delimited format.
# Support both pipe-style rows seen in some Samba builds and the normal human
# listing format: filename, DOS attributes, size, modified timestamp.
base = previous.base

_HUMAN_LISTING_RE = re.compile(
    r"^\s*(?P<name>.*?)\s+(?P<attrs>[A-Z]+)\s+(?P<size>\d+)\s+(?P<modified>.+?)\s*$"
)


def _parse_directory(raw: str) -> list[dict]:
    items: list[dict] = []
    candidate_lines = 0

    for line in raw.splitlines():
        stripped = line.strip()
        if not stripped:
            continue

        attrs = ""
        name = ""
        size: int | None = None

        # Some Samba versions/builds produce rows such as:
        #   D|0|Thu Aug 27 09:44:00 2026|Folder
        # Keep this deliberately flexible and use the final field as the name.
        fields = line.split("|")
        if len(fields) >= 3:
            maybe_attrs = fields[0].strip()
            maybe_size = fields[1].strip()
            maybe_name = fields[-1].strip()
            if maybe_attrs and maybe_size.isdigit() and maybe_name:
                attrs = maybe_attrs
                size = int(maybe_size)
                name = maybe_name
                candidate_lines += 1
        else:
            # Normal smbclient `ls` output is column based, for example:
            #   Documents                          D        0  Thu Aug 27 09:44:00 2026
            # Filename may contain spaces, so parse from the attributes/size tail.
            match = _HUMAN_LISTING_RE.match(line)
            if match:
                attrs = match.group("attrs")
                size = int(match.group("size"))
                name = match.group("name").rstrip()
                candidate_lines += 1

        if not name or name in {".", ".."}:
            continue

        is_dir = "D" in attrs.upper()
        items.append(
            {
                "name": name,
                "directory": is_dir,
                "size": None if is_dir else size,
            }
        )

    items.sort(key=lambda item: (not item["directory"], item["name"].lower()))
    main.LOGGER.info(
        "SMB directory parser received %d line(s), recognized %d candidate row(s), parsed %d item(s)",
        len(raw.splitlines()),
        candidate_lines,
        len(items),
    )
    return items


# Existing base.list_directory resolves base._parse_directory at request time.
base._parse_directory = _parse_directory

# Re-export the public SMB interface expected by the runtime.
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
smb_page = previous.smb_page
test_connection = previous.test_connection
