"""HA Remote Bridge 0.4.7 runtime with RutOS subscription compatibility."""

import asyncio

import compat_runner_v14 as previous
import compat_runner_v8 as zip_runtime
import rutos_compat

# Apply the latest RutOS compatibility layer after the existing Web/SSH/VNC/SMB
# and UI stacks have been installed.
rutos_compat.install()

base_runtime = zip_runtime.previous.previous.previous.base.base
base_runtime.BRIDGE_UI_VERSION = "0.4.7"

if __name__ == "__main__":
    asyncio.run(base_runtime._run())
