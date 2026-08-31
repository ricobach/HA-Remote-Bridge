"""HA Remote Bridge 0.5.1 runtime with targeted host service discovery."""

import asyncio

import compat_runner_v24 as previous
import host_discovery
import main
from ui_shell_v20 import INDEX_HTML

host_discovery.install()

base_runtime = previous.base_runtime
main.INDEX_HTML = INDEX_HTML
base_runtime.INDEX_HTML = INDEX_HTML
base_runtime.BRIDGE_UI_VERSION = "0.5.1"

if __name__ == "__main__":
    asyncio.run(base_runtime._run())
