# Archive

This directory contains historical project files that are no longer used by the current HA Remote Bridge App.

Archived material is kept for reference only and is not copied into the App image or imported by the runtime.

## `legacy-docs/`

Early documentation from the HTTP/HTTPS-only phase of the project. These documents became inaccurate after SSH, VNC, SMB, discovery and the App-only architecture were added.

## Why the numbered Python files are not archived

The current runtime is still layered. `ha_remote_bridge/run.sh` starts the latest compatibility runner, which imports preceding runtime layers; the UI and several support modules follow a similar composition model.

As a result, many files with older version numbers are still active dependencies. They should only be archived after the runtime/UI stack is consolidated into canonical modules and the import graph no longer references them.
