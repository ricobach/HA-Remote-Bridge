"""HA Remote Bridge 0.4.12 runtime with proxy-safe Web session reloads."""

import asyncio

import compat_runner_v20 as previous
import main
from ui_shell_v17 import INDEX_HTML

base_runtime = previous.base_runtime
main.INDEX_HTML = INDEX_HTML
base_runtime.INDEX_HTML = INDEX_HTML
base_runtime.BRIDGE_UI_VERSION = "0.4.12"

if __name__ == "__main__":
    asyncio.run(base_runtime._run())
