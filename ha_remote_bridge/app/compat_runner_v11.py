"""HA Remote Bridge 0.4.2 runtime with sorting and ESPHome filtering."""

import asyncio

import compat_runner_v10 as previous
import main
from ui_shell_v15 import INDEX_HTML

main.INDEX_HTML = INDEX_HTML
previous.previous.previous.previous.previous.previous.base.base.INDEX_HTML = INDEX_HTML
previous.previous.previous.previous.previous.previous.base.base.BRIDGE_UI_VERSION = "0.4.2"

if __name__ == "__main__":
    asyncio.run(previous.previous.previous.previous.previous.previous.base.base._run())
