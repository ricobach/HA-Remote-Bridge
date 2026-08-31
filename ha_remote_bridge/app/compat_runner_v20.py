"""HA Remote Bridge 0.4.11 runtime with RutOS path/auth fixes."""

import asyncio

import compat_runner_v14 as previous
import compat_runner_v8 as zip_runtime
import rutos_compat

rutos_compat.install()

base_runtime = zip_runtime.previous.previous.previous.base.base
base_runtime.BRIDGE_UI_VERSION = "0.4.11"

if __name__ == "__main__":
    asyncio.run(base_runtime._run())
