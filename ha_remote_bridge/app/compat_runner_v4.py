"""HA Remote Bridge 0.2.8 runtime wrapper with SMB diagnostics."""

import asyncio

import compat_runner_v3 as base
import main
import smb_support_v2 as smb
from ui_shell_v12 import INDEX_HTML

# Swap the SMB implementation used by compat_runner_v3. Its functions resolve the
# module global at request time, so existing resource/status routes use v2 too.
base.smb = smb
base.INDEX_HTML = INDEX_HTML
base.BRIDGE_UI_VERSION = "0.2.8"
main.INDEX_HTML = INDEX_HTML

# Add the one new API route without duplicating the large runtime composition.
_original_create_app = base.launcher.create_app


def _create_app():
    app = _original_create_app()
    app.router.add_post("/api/smb/test", smb.test_connection)
    return app


base.launcher.create_app = _create_app


if __name__ == "__main__":
    asyncio.run(base._run())
