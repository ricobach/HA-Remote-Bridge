"""HA Remote Bridge 0.4.14 runtime with RutOS initial route correction."""

import asyncio

import compat_runner_v22 as previous
import main
import rutos_bootstrap
from ui_shell_v18 import INDEX_HTML

rutos_bootstrap.install()

base_runtime = previous.base_runtime
main.INDEX_HTML = INDEX_HTML
base_runtime.INDEX_HTML = INDEX_HTML
base_runtime.BRIDGE_UI_VERSION = "0.4.14"

if __name__ == "__main__":
    asyncio.run(base_runtime._run())
