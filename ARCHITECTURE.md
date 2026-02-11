# Architecture - The Surgeon (mcp-injector)

**The technical blueprint for precision configuration management in the Workforce Nexus.**

This document provides a low-density, comprehensive deep dive into the internal logic, state machines, and modular subsystems that power the `mcp-injector`. It is intended for developers and architects who need to understand exactly how the system achieves industrial-level reliability when modifying IDE configuration files.

---

## 🔍 Nexus Suite Context
The **Surgeon** is the configuration management engine of the **Workforce Nexus**. It ensures that tools managed by the Activator and discovered by the Observer are correctly registered in your IDEs. For the full architectural roadmap, see the [Master Nexus Guide](../repo-mcp-packager/NEXUS_GUIDE.md).

## 🏗 Core Philosophy: Surgical Precision

The Surgeon follows the **Verify -> Backup -> Change -> Validate** loop. It treats user configuration files as mission-critical artifacts that must never be corrupted.

1.  **Non-Destructive Parsing**: Uses the standard `json` library to parse and manipulate data as a Python dictionary, preserving as much structure as possible.
2.  **Atomic Integrity**: Changes are never written directly to the target file. A temporary file is used to verify success before an atomic rename.
3.  **Schema Drift Protection**: Detects if the internal structure of an IDE config has changed (e.g., from a list to an object) before attempting a write.

---

## 🏗 Subsystem Breakdown

### 1. The Injection Engine (`MCPInjector` class)
The core logic for safe JSON manipulation.

*   **`load_config()`**: Reads the target file. If missing, initializes a standard structure (e.g., `{"mcpServers": {}}`) to ensure the first injection succeeds.
*   **`add_server()`**: Handles the delicate logic of inserting a new tool. It ensures that the `command`, `args`, and optional `env` blocks are correctly formatted.
*   **`remove_server()`**: Safely extracts an entry by key, ensuring no trailing commas or broken brackets are left behind.

### 2. Validation & Auditing
The Surgeon protects the user from "Bracket Hell" through two layers of defense.

*   **Structural Audit (`_structural_audit`)**:
    *   **Goal**: Detect type-level differences between the old and new config.
    *   **Logic**: Recursively compares types of keys. If it finds that a known key has changed type (e.g., `mcpServers` was an object but is now a string), it aborts to prevent corruption.
*   **Industrial Schema Validation (`_validate_with_schema`)**:
    *   **Goal**: Ensure 100% compliance with IDE expectations.
    *   **Logic**: If `jsonschema` is available in the environment (provided by the Industrial Nexus tier), it validates the final output against local schema definitions before writing.

### 3. Safety & Backup Layer
*   **Automatic Backups**: Every write operation triggers an immediate `.json.backup` copy of the original file.
*   **Atomic Write**: The system writes to `config.json.tmp`, validates that the file is readable JSON, and then uses `os.replace` to commit the change. This prevents "partial writes" if the system crashes midway.

---

## ⚡ Integrated Nexus Logic

The Surgeon is suite-aware. Every time a client configuration is modified, it updates the global Workforce Nexus registry.

*   **Global Sync**: Calls `update_global_config()` to store the location of the modified IDE config in `~/.mcp-tools/config.json`. This allows the Observer (manager) to find and monitor the servers later without a full system scan.
*   **Auto-Chmod**: When injected, any shell scripts or python commands are passed through the Nexus permission-hardening filter to ensure they are executable (`chmod +x`).

---

## 📂 Data Structures

### IDE Configuration Mapping
The Surgeon maintains a dictionary of known client paths across different platforms.

| Client | Path Pattern |
| :--- | :--- |
| **Claude** | `~/Library/Application Support/Claude/claude_desktop_config.json` |
| **Cursor** | `~/.cursor/mcp.json` |
| **VS Code** | `~/.vscode/mcp_settings.json` |

---

## 🛡 Security & Permissions
*   **Local Execution**: The Surgeon never makes network requests. It operates entirely on local filesystem state.
*   **User Consent**: In interactive mode, every injection requires a final `[Y/n]` confirmation from the user after viewing a summary of the change.

---

## 📝 Metadata
*   **Status**: Hardened (Phase 9)
*   **Developer**: l00p3rl00p
*   **Reference**: [ENVIRONMENT.md](./ENVIRONMENT.md) | [USER_OUTCOMES.md](./USER_OUTCOMES.md)
