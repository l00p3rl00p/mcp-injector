# ENVIRONMENT.md — Workforce Nexus Suite (mcp-injector)

Host environment requirements, safety rules, and OS-specific paths for the **MCP Injector** repo (client discovery + safe config injection).

---

## 🔍 Core Dependency Rules

### Python
* **Minimum**: Python **3.9+**
* **Recommended**: Python **3.11+**
* **Isolation**: When installed as part of the suite, the injector runs from the **central** Nexus environment (no workspace venv required).

### Node / Docker
* Not required for injector operation.

---

## 🛠 Central Paths (Suite Home)

The suite uses predictable, user-owned paths:
* Nexus home: `~/.mcp-tools`
* Tools bin: `~/.mcp-tools/bin`
* Shared venv (optional): `~/.mcp-tools/.venv`
* Shared state + devlogs: `~/.mcp-tools/mcpinv/`
* Global injector config (created on install if missing): `~/.mcp-tools/config.json`

---

## ⚙️ Safety & Discovery Rules (No Disk Scans)

To reduce risk and surprise:
* The injector does **not** crawl your filesystem.
* It uses a bounded set of known app-specific locations and explicit user choices.
* It is **prompt-before-mutate**: discovery first, then confirm before writing config.

---

## 🧾 Devlogs (Shared Diagnostics)

Shared JSONL devlogs live under:
* `~/.mcp-tools/mcpinv/devlogs/nexus-YYYY-MM-DD.jsonl`

Behavior:
* Entries are appended as actions run.
* Old devlog files are pruned on use (90-day retention).
* `bootstrap.py --devlog` captures subprocess stdout/stderr for debugging injector flows.

---

## 🧩 Suite Install & Re-runs

If you only have this repo, you can still install the full suite (no scanning) via:
* `python3 bootstrap.py --install-suite --permanent`

This clones missing Nexus repos into `~/.mcp-tools` and then runs the Activator.

---

## 📝 Metadata
* **Status**: Hardened
* **Reference**: [ARCHITECTURE.md](./ARCHITECTURE.md) | [USER_OUTCOMES.md](./USER_OUTCOMES.md)

