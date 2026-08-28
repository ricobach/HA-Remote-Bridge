"""HA Remote Bridge 0.4.1 runtime with responsive desktop cards."""

import asyncio

import compat_runner_v9 as previous
import main
from ui_shell_v14 import INDEX_HTML

main.INDEX_HTML = INDEX_HTML
previous.previous.previous.previous.previous.base.base.INDEX_HTML = INDEX_HTML
previous.previous.previous.previous.previous.base.base.BRIDGE_UI_VERSION = "0.4.1"

if __name__ == "__main__":
    asyncio.run(previous.previous.previous.previous.previous.base.base._run())
