"""Canonical SMB service composition for HA Remote Bridge.

The historical smb_support_vXX modules were renamed by responsibility. This
loader supplies their former module names as in-memory aliases while composing
the current SMB implementation, then exposes the final public API.
"""

from __future__ import annotations

import importlib
import sys

_SMB_LAYERS = (
    ("smb_support", "smb_core"),
    ("smb_support_v2", "smb_diagnostics"),
    ("smb_support_v3", "smb_directory_parser"),
    ("smb_support_v4", "smb_file_viewer"),
    ("smb_support_v5", "smb_parent_navigation"),
    ("smb_support_v6", "smb_zip_browser"),
    ("smb_support_v7", "smb_file_navigation"),
    ("smb_support_v8", "smb_breadcrumbs"),
)

_final = None
for legacy_name, functional_name in _SMB_LAYERS:
    module = importlib.import_module(functional_name)
    sys.modules[legacy_name] = module
    _final = module

if _final is None:
    raise RuntimeError("SMB service composition failed")

# Re-export the final composed implementation. The individual functional layers
# keep references to their predecessors captured during import, so restoring
# smb_support to this canonical module is safe for any later imports.
for _name in dir(_final):
    if not _name.startswith("__"):
        globals()[_name] = getattr(_final, _name)

sys.modules["smb_support"] = sys.modules[__name__]
