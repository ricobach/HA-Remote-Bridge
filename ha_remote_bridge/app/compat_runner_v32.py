"""HA Remote Bridge 0.5.8 runtime with per-Web virtual Host/SNI support."""

import asyncio

import compat_runner_v31 as previous
import main
import virtual_host_support
from ui_shell_v23 import INDEX_HTML

virtual_host_support.install()

base_runtime = previous.base_runtime
main.INDEX_HTML = INDEX_HTML
base_runtime.INDEX_HTML = INDEX_HTML
base_runtime.BRIDGE_UI_VERSION = "0.5.8"

if __name__ == "__main__":
    asyncio.run(base_runtime._run())
