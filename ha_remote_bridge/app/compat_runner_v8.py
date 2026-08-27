"""HA Remote Bridge 0.3.2 runtime wrapper with inline SMB ZIP browsing."""

import asyncio

import compat_runner_v7 as previous
import main
import smb_support_v6 as smb

# v7 -> v6 -> v5 -> v4 -> v3. The existing file-preview routes in v6 resolve
# its module-global `smb` at request time, so point that at the ZIP-aware layer.
previous.smb = smb
previous.previous.smb = smb
previous.previous.previous.base.base.smb = smb
previous.previous.previous.base.base.BRIDGE_UI_VERSION = "0.3.2"
main.INDEX_HTML = previous.previous.previous.base.INDEX_HTML

# Add ZIP-specific APIs and the nested-entry viewer on top of the existing
# preview/test route composition.
_original_create_app = previous.previous.previous.base.base.launcher.create_app


def _create_app():
    app = _original_create_app()
    app.router.add_get("/api/smb/{resource_id}/zip/list", smb.zip_list)
    app.router.add_get("/api/smb/{resource_id}/zip/raw", smb.zip_raw)
    app.router.add_get("/api/smb/{resource_id}/zip/text", smb.zip_text)
    app.router.add_get("/smb/{resource_id}/zip-entry", smb.zip_entry_page)
    return app


previous.previous.previous.base.base.launcher.create_app = _create_app


if __name__ == "__main__":
    asyncio.run(previous.previous.previous.base.base._run())
