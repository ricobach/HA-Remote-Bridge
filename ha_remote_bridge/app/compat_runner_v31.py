"""HA Remote Bridge 0.5.7 runtime with host rescans and expanded 8xxx discovery."""

import asyncio

import compat_runner_v30 as previous
import host_discovery_expanded
import main
from ui_shell_v22 import INDEX_HTML

host_discovery_expanded.install()

base_runtime = previous.base_runtime
main.INDEX_HTML = INDEX_HTML
base_runtime.INDEX_HTML = INDEX_HTML
base_runtime.BRIDGE_UI_VERSION = "0.5.7"

if __name__ == "__main__":
    asyncio.run(base_runtime._run())
