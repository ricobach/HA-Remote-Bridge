# Archive

This directory contains historical project material that is no longer used by the current HA Remote Bridge App.

Archived material is for reference only and is not part of the active runtime.

## `legacy-docs/`

Early documentation from the HTTP/HTTPS-only phase of the project.

## `legacy-runtime/`

The historical release-numbered `compat_runner_vXX.py` startup chain was retired in 0.6.0. The exact source remains available in Git history; the archive manifest records the transition point and naming rationale.

The active App now starts `ha_remote_bridge/app/runtime.py` directly. New runtime features should be added as responsibility-based support/compatibility modules rather than new version-numbered runners.
