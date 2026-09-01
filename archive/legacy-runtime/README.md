# Legacy runtime runners

HA Remote Bridge 0.6.0 retired the release-numbered runtime composition files:

```text
compat_runner_v2.py ... compat_runner_v33.py
```

They were replaced by the canonical active entry point:

```text
ha_remote_bridge/app/runtime.py
```

The old runner files were thin release-by-release composition wrappers. Their exact contents remain permanently available in Git history, including the repository state immediately before the 0.6.0 runtime consolidation.

This archive intentionally stores a manifest rather than duplicate Python source so historical runtime code is not copied into the Home Assistant App image.

Future runtime features should use responsibility-based modules such as `*_support.py`, `*_compat.py`, or dedicated feature modules and be composed explicitly by `runtime.py`.
