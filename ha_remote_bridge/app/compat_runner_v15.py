"""HA Remote Bridge 0.4.6 runtime with RutOS/Teltonika compatibility."""

import asyncio

import compat_runner_v14 as previous
import compat_runner_v8 as zip_runtime
import rutos_compat

# Importing the current runtime stack installs all existing Web/SSH/VNC/SMB,
# viewer, ZIP and dashboard compatibility layers. Apply RutOS last so it wraps
# the final request-header and browser-shim implementations.
rutos_compat.install()

base_runtime = zip_runtime.previous.previous.previous.base.base
base_runtime.BRIDGE_UI_VERSION = "0.4.6"

if __name__ == "__main__":
    asyncio.run(base_runtime._run())
