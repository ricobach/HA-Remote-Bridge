"""HA Remote Bridge 0.5.4 runtime with OpenAPI/Swagger proxy server rewriting."""

import asyncio

import compat_runner_v27 as previous
import main
import openapi_proxy_compat
from ui_shell_v21 import INDEX_HTML

openapi_proxy_compat.install()

base_runtime = previous.base_runtime
main.INDEX_HTML = INDEX_HTML
base_runtime.INDEX_HTML = INDEX_HTML
base_runtime.BRIDGE_UI_VERSION = "0.5.4"

if __name__ == "__main__":
    asyncio.run(base_runtime._run())
