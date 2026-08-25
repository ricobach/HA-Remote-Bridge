"""HA Remote Bridge 0.2.3 runtime wrapper."""

import asyncio

import compat_runner_v2 as base
import main
from ui_shell_v9 import INDEX_HTML

base.INDEX_HTML = INDEX_HTML
base.BRIDGE_UI_VERSION = "0.2.3"
main.INDEX_HTML = INDEX_HTML


if __name__ == "__main__":
    asyncio.run(base._run())
