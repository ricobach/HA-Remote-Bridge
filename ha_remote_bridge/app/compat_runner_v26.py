"""HA Remote Bridge 0.5.2 runtime with canonical host grouping."""

import asyncio

import compat_runner_v25 as previous
import main
from ui_shell_v21 import INDEX_HTML

base_runtime = previous.base_runtime
main.INDEX_HTML = INDEX_HTML
base_runtime.INDEX_HTML = INDEX_HTML
base_runtime.BRIDGE_UI_VERSION = "0.5.2"

if __name__ == "__main__":
    asyncio.run(base_runtime._run())
