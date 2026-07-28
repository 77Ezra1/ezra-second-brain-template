# System Changelog

## 2026-07-28

- Added platform-specific installation paths for macOS and Windows.
- Added `scripts/install-macos.sh` and `scripts/install-windows.ps1` wrappers around the cross-platform Python installer.
- Added `--platform auto|macos|windows|linux` to `scripts/install.py` and platform-aware `config/brain.yaml` generation.
- Added macOS and Windows installation guides under `docs/`.
- Updated README, Chinese README, commands docs, and architecture docs with Mac/Win setup instructions.
- Added installer tests covering platform config generation and Windows next-step output.

## Initial

- Initialized second-brain structure.
