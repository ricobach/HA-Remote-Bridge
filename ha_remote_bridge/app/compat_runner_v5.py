"""HA Remote Bridge 0.2.9 runtime wrapper with robust SMB folder parsing."""

import asyncio

import compat_runner_v4 as base
import main
import smb_support_v3 as smb

# Upgrade the SMB implementation while keeping the 0.2.8 UI and diagnostics.
base.base.smb = smb
base.smb = smb
base.base.BRIDGE_UI_VERSION = "0.2.9"
main.INDEX_HTML = base.INDEX_HTML

# compat_runner_v4 patched launcher.create_app to add /api/smb/test; keep that
# composition and run the underlying modern runtime.
if __name__ == "__main__":
    asyncio.run(base.base._run())
