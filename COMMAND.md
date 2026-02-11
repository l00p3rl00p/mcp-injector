# Workforce Nexus: Commands (Quick Start)

This file is the **human-first** quick command sheet.

For the exhaustive, verifiable command matrix, see `COMMANDS.md`.

---

## Run Standalone (Surgeon)

```bash
python3 mcp_injector.py --help
```

List supported IDE clients:

```bash
python3 mcp_injector.py --list-clients
```

Guided injection (recommended):

```bash
python3 mcp_injector.py --startup-detect
```

---

## Install / Repair the Full Suite

This repo’s `bootstrap.py` is a **safe forwarder** (no disk scanning). It will:
- use `../repo-mcp-packager/bootstrap.py` if present, or
- use `~/.mcp-tools/repo-mcp-packager/bootstrap.py` if installed, or
- (TTY-only) offer to fetch Activator into `~/.mcp-tools`.

```bash
python3 bootstrap.py --permanent
```

---

## Uninstall (Central-Only, Safe by Default)

This uninstaller **only touches approved central locations** (e.g. `~/.mcp-tools`, `~/.mcpinv`, and the Nexus PATH block).
It does **not** scan your disk or delete anything in your git workspace.

Full wipe:

```bash
python3 uninstall.py --purge-data --kill-venv
```

Diagnostics:

```bash
python3 uninstall.py --purge-data --kill-venv --verbose --devlog
```

