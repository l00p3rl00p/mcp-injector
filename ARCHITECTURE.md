# Architecture - MCP Surgeon (mcp-injector)

**The technical blueprint for the Configuration Injection Engine.**

The **Surgeon** is the suite's interface to the host's IDE ecosystem. It specializes in high-fidelity, atomic modifications of JSON configuration files, ensuring MCP servers are registered correctly across Claude Desktop, Cursor, and other clients.

---

## 🔍 Core Philosophy: Surgical Precision

The Surgeon operates on the principle of **Atomic JSON Transitions**. It avoids brute-force file overwriting and instead uses structured manipulation to insert or remove specific server entries without disturbing existing user configurations.

---

## 🏗 Subsystem Breakdown

### 1. The Injection Engine (`mcp_injector.py`)
The heart of the tool. It performs the actual JSON "surgery."
* **Bracket Hell Prevention**: A custom logic layer that ensures valid comma placement in the `mcpServers` list.
* **Atomic Writes**: Uses `tempfile` and `os.replace` to ensure that a crash mid-save never results in a corrupted config file.
* **Automatic Backups**: Always creates a `.bak` timestamped copy before any write operation.

### 2. Client Discovery Module
Detects the presence and location of IDE configuration files.
* **Claude Desktop**: Maps to `~/Library/Application Support/Claude/claude_desktop_config.json`.
* **Cursor**: Maps to standard workspace config locations.
* **AI Studio / Antigravity**: Detects specialized AI development environments.

### 3. Interactive Installation (`mcp_injector_install.sh`)
Provides the high-level onboarding experience.
* **Guided Setup**: Detects which IDEs are installed and prompts the user to choose which ones to configure.
* **Suite Synchronization**: When run within the Workforce Nexus, it automatically proposes the injection of the **Librarian** and other MCP-stdio components.

### 4. Cleanup & Rollback
Supports non-destructive removal of Nexus entries.
* **Tag-Based Removal**: Uses the `id` of the entry to surgically excise the correct block while leaving other servers intact.

---

## 🔐 Safety & Hardening

### 1. Validation Before Commit
The Surgeon parses the target JSON *before* modification. If the file is already corrupted or invalid, it aborts the operation to prevent further damage.

### 2. Noclobber Compliance
Adheres to the Global Security Mandate by ensuring that it does not overwrite files unless explicitly requested via the recovery/repair workflow.

---

## 📝 Metadata
* **Status**: Production Ready (v3.2.1)
* **Author**: l00p3rl00p
* **Part of**: The Workforce Nexus Suite
