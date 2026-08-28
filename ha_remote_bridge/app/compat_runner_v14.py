"""HA Remote Bridge 0.4.5 runtime with clickable SMB breadcrumbs."""

import asyncio

import compat_runner_v13 as previous
import compat_runner_v8 as zip_runtime
import smb_support_v8 as smb

# Existing SMB and ZIP routes resolve their module-global `smb` references when
# requests arrive. Point the route stack at the breadcrumb-aware viewer layer.
zip_runtime.smb = smb
zip_runtime.previous.smb = smb
zip_runtime.previous.previous.smb = smb
zip_runtime.previous.previous.previous.base.base.smb = smb

base_runtime = zip_runtime.previous.previous.previous.base.base
base_runtime.BRIDGE_UI_VERSION = "0.4.5"

if __name__ == "__main__":
    asyncio.run(base_runtime._run())
