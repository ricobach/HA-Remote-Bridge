"""HA Remote Bridge 0.4.4 runtime with previous/next SMB file navigation."""

import asyncio

import compat_runner_v12 as previous
import compat_runner_v8 as zip_runtime
import smb_support_v7 as smb

# The SMB and ZIP routes were composed in the older runtime layers and resolve
# their module-global `smb` references when requests arrive. Point every layer
# at the new viewer module so normal files and nested ZIP entries both gain
# Previous/Next navigation without rebuilding the route stack.
zip_runtime.smb = smb
zip_runtime.previous.smb = smb
zip_runtime.previous.previous.smb = smb
zip_runtime.previous.previous.previous.base.base.smb = smb

# Importing the current dashboard runtime above has already installed the 0.4.3
# UI shell. Reuse the stable base runner directly and only advance its banner.
base_runtime = zip_runtime.previous.previous.previous.base.base
base_runtime.BRIDGE_UI_VERSION = "0.4.4"

if __name__ == "__main__":
    asyncio.run(base_runtime._run())
