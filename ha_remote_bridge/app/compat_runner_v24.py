"""HA Remote Bridge 0.5.0 runtime with per-connection SSH passwords."""

import asyncio

import compat_runner_v23 as previous
import main
import ssh_password_auth
from ui_shell_v19 import INDEX_HTML

base_runtime = previous.base_runtime
ssh_password_auth.install_runtime_handlers(base_runtime)
main.INDEX_HTML = INDEX_HTML
base_runtime.INDEX_HTML = INDEX_HTML
base_runtime.BRIDGE_UI_VERSION = "0.5.0"

if __name__ == "__main__":
    asyncio.run(base_runtime._run())
