"""HA Remote Bridge 0.3.1 runtime wrapper with SMB parent-directory navigation."""

import asyncio

import compat_runner_v6 as previous
import main
import smb_support_v5 as smb

# compat_runner_v6 -> v5 -> v4 -> v3. Swap both the preview-route module and
# the underlying runtime SMB implementation while preserving all existing routes.
previous.smb = smb
previous.previous.base.base.smb = smb
previous.previous.base.base.BRIDGE_UI_VERSION = "0.3.1"
main.INDEX_HTML = previous.previous.base.INDEX_HTML


if __name__ == "__main__":
    asyncio.run(previous.previous.base.base._run())
