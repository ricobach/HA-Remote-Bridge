"""HA Remote Bridge 0.4.0 runtime with compact dashboard redesign."""

import asyncio

import compat_runner_v8 as previous
import main
from ui_shell_v13 import INDEX_HTML

# Keep all 0.3.3 Web/SSH/VNC/SMB/ZIP routes and only replace the dashboard shell.
main.INDEX_HTML = INDEX_HTML
previous.previous.previous.previous.base.base.INDEX_HTML = INDEX_HTML
previous.previous.previous.previous.base.base.BRIDGE_UI_VERSION = "0.4.0"


if __name__ == "__main__":
    asyncio.run(previous.previous.previous.previous.base.base._run())
