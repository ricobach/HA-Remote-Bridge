"""HA Remote Bridge 0.3.0 runtime wrapper with SMB file previews."""

import asyncio

import compat_runner_v5 as previous
import main
import smb_support_v4 as smb

# compat_runner_v5 -> compat_runner_v4 -> compat_runner_v3.
# Swap the active SMB implementation while preserving diagnostics/test routes.
previous.base.base.smb = smb
previous.base.smb = smb
previous.base.base.BRIDGE_UI_VERSION = "0.3.0"
main.INDEX_HTML = previous.base.INDEX_HTML

# compat_runner_v4 already wrapped launcher.create_app to add /api/smb/test.
# Add preview routes on top of that composition.
_original_create_app = previous.base.base.launcher.create_app


def _create_app():
    app = _original_create_app()
    app.router.add_get("/api/smb/{resource_id}/raw", smb.raw_file)
    app.router.add_get("/api/smb/{resource_id}/text", smb.text_preview)
    app.router.add_get("/smb/{resource_id}/view", smb.viewer_page)
    return app


previous.base.base.launcher.create_app = _create_app


if __name__ == "__main__":
    asyncio.run(previous.base.base._run())
