"""HA Remote Bridge 0.4.13 runtime with read-only endpoint address bar."""

import asyncio

import compat_runner_v21 as previous
import main
from ui_shell_v18 import INDEX_HTML

base_runtime = previous.base_runtime
main.INDEX_HTML = INDEX_HTML
base_runtime.INDEX_HTML = INDEX_HTML
base_runtime.BRIDGE_UI_VERSION = "0.4.13"

if __name__ == "__main__":
    asyncio.run(base_runtime._run())
