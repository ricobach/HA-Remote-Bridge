"""HA Remote Bridge 0.4.3 runtime with collapsible multi-service cards."""

import asyncio

import compat_runner_v11 as previous
import main
from ui_shell_v16 import INDEX_HTML

main.INDEX_HTML = INDEX_HTML
previous.previous.previous.previous.previous.previous.previous.base.base.INDEX_HTML = INDEX_HTML
previous.previous.previous.previous.previous.previous.previous.base.base.BRIDGE_UI_VERSION = "0.4.3"

if __name__ == "__main__":
    asyncio.run(previous.previous.previous.previous.previous.previous.previous.base.base._run())
