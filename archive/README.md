# Archive

This directory contains historical project material that is no longer used by the current HA Remote Bridge App.

Archived material is for reference only and is not part of the active runtime.

## `legacy-docs/`

Early documentation from the HTTP/HTTPS-only phase of the project.

## `legacy-runtime/`

The historical release-numbered `compat_runner_vXX.py` startup chain was retired in 0.6.0. The exact source remains available in Git history; the archive manifest records the transition point and naming rationale.

## UI and SMB source naming

Version 0.7.0 retired the physical `ui_shell_vXX.py` and `smb_support_vXX.py` filenames from the active App tree.

The UI layers are now named by responsibility, for example:

```text
dashboard_base.py
dashboard_health.py
dashboard_host_grouping.py
dashboard_address_bar.py
dashboard_host_discovery.py
dashboard_virtual_host.py
```

The SMB layers are similarly named:

```text
smb_core.py
smb_diagnostics.py
smb_directory_parser.py
smb_file_viewer.py
smb_parent_navigation.py
smb_zip_browser.py
smb_file_navigation.py
smb_breadcrumbs.py
```

`dashboard.py` and `smb_service.py` are the canonical composition entry modules. They provide in-memory aliases for the historical module names only while loading the unchanged, proven layer implementations. The old physical filenames are not copied into the App image.

The former generic `compat_runner.py` Web/ESPHome compatibility module is now `web_proxy_compat.py`.

Exact historical source and original filenames remain available in Git history.
