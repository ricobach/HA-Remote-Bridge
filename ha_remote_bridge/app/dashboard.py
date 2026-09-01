"""Canonical dashboard composition for HA Remote Bridge.

The historical ui_shell_vXX files were renamed by responsibility. Their proven
composition code is kept byte-for-byte unchanged; this loader supplies the old
module names as in-memory aliases while composing the final dashboard.
"""

from __future__ import annotations

import importlib
import sys

_UI_LAYERS = (
    ("ui_shell_v2", "dashboard_base"),
    ("ui_shell_v3", "dashboard_health"),
    ("ui_shell_v4", "dashboard_ssh"),
    ("ui_shell_v5", "dashboard_sessions"),
    ("ui_shell_v6", "dashboard_host_grouping"),
    ("ui_shell_v7", "dashboard_group_polish"),
    ("ui_shell_v8", "dashboard_ssh_editor"),
    ("ui_shell_v9", "dashboard_ssh_controls"),
    ("ui_shell_v10", "dashboard_vnc"),
    ("ui_shell_v11", "dashboard_smb"),
    ("ui_shell_v12", "dashboard_smb_diagnostics"),
    ("ui_shell_v13", "dashboard_compact"),
    ("ui_shell_v14", "dashboard_responsive"),
    ("ui_shell_v15", "dashboard_filters_sorting"),
    ("ui_shell_v16", "dashboard_service_collapse"),
    ("ui_shell_v17", "dashboard_reload"),
    ("ui_shell_v18", "dashboard_address_bar"),
    ("ui_shell_v19", "dashboard_ssh_passwords"),
    ("ui_shell_v20", "dashboard_host_discovery"),
    ("ui_shell_v21", "dashboard_canonical_grouping"),
    ("ui_shell_v22", "dashboard_rescan"),
    ("ui_shell_v23", "dashboard_virtual_host"),
    ("ui_shell_v24", "dashboard_virtual_host_persistence"),
)

_final = None
for legacy_name, functional_name in _UI_LAYERS:
    module = importlib.import_module(functional_name)
    sys.modules[legacy_name] = module
    _final = module

if _final is None or not hasattr(_final, "INDEX_HTML"):
    raise RuntimeError("Dashboard composition failed")

# New responsibility-based UI layers compose directly on the canonical result.
from dashboard_ssh_terminal import INDEX_HTML
