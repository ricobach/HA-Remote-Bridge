"""HA Remote Bridge 0.5.3 runtime with same-origin Web API rebasing."""

import asyncio

import compat_runner_v26 as previous
import main
import same_origin_web_compat
from ui_shell_v21 import INDEX_HTML

same_origin_web_compat.install()

base_runtime = previous.base_runtime
main.INDEX_HTML = INDEX_HTML
base_runtime.INDEX_HTML = INDEX_HTML
base_runtime.BRIDGE_UI_VERSION = "0.5.3"

if __name__ == "__main__":
    asyncio.run(base_runtime._run())
