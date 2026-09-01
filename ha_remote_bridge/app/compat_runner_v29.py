"""HA Remote Bridge 0.5.5 runtime with Swagger Try-it-out request interception."""

import asyncio

import compat_runner_v28 as previous
import main
import swagger_request_compat
from ui_shell_v21 import INDEX_HTML

swagger_request_compat.install()

base_runtime = previous.base_runtime
main.INDEX_HTML = INDEX_HTML
base_runtime.INDEX_HTML = INDEX_HTML
base_runtime.BRIDGE_UI_VERSION = "0.5.5"

if __name__ == "__main__":
    asyncio.run(base_runtime._run())
