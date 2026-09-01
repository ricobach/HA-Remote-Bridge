"""HA Remote Bridge 0.5.9 runtime with persistent virtual-host address prefix."""

import asyncio

import compat_runner_v32 as previous
import main
from ui_shell_v24 import INDEX_HTML

base_runtime = previous.base_runtime
main.INDEX_HTML = INDEX_HTML
base_runtime.INDEX_HTML = INDEX_HTML
base_runtime.BRIDGE_UI_VERSION = "0.5.9"

if __name__ == "__main__":
    asyncio.run(base_runtime._run())
