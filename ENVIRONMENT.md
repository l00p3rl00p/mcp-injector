# Environment Specification - The Surgeon (mcp-injector)

**Unified Environment Requirements & Client Mapping.**

This document provides a low-density technical manual for the host environment requirements, dependency resolution logic, and IDE-specific configuration paths used by the `mcp-injector`.

---

## 📂 Nexus Suite Impact
When running as part of the **Workforce Nexus**, the Surgeon uses the shared central configuration:
* **Nexus Home**: `~/.mcp-tools/`
* **Central Registry**: `~/.mcp-tools/mcp-injector/config.json`

## 🔍 Core Dependency Rules

### 1. Python Runtimes
*   **Standalone Mode**: Optimized for **Python 3.6+**. The Surgeon uses standard library modules only (`json`, `pathlib`, `os`, `shutil`) to ensure it can be dropped into any environment without a virtual environment.
*   **Industrial Nexus Tier**: When integrated with the Workforce Nexus, it uses **Python 3.11+** and leverages `jsonschema` for high-confidence validation.

### 2. File Access & Permissions
*   **Write Access**: The Surgeon requires read/write access to the IDE configuration directories (listed below).
*   **Backup Storage**: The Surgeon creates a `.json.backup` file in the same directory as the target config. Sufficient disk space for multiple config versions is required.

---

## 🛠 Client Configuration Matrix

The Surgeon maintains a mapping of known MCP client configuration files. These paths are expanded automatically based on the host OS.

| Client | Platform | Path Pattern |
| :--- | :--- | :--- |
| **Claude** | macOS | `~/Library/Application Support/Claude/claude_desktop_config.json` |
| **Cursor** | macOS | `~/.cursor/mcp.json` |
| **VS Code** | macOS | `~/.vscode/mcp_settings.json` |
| **Xcode** | macOS | `~/Library/Developer/Xcode/UserData/MCPServers/config.json` |
| **AI Studio**| Linux/macOS| `~/.config/aistudio/mcp_servers.json` |

### Platform-Specific Expansion
*   **macOS**: Uses `Path.home()` and `Library/Application Support`.
*   **Windows**: Uses `%APPDATA%` and `%USERPROFILE%` environment variables.
*   **Linux**: Follows the XDG Base Directory Specification (e.g., `~/.config`).

---

## 🛡 Security & Hardening

### Atomic Operations
To prevent data loss, the Surgeon performs all file writes in three distinct steps:
1.  **Backup**: Copies `config.json` -> `config.json.backup`.
2.  **Verify**: Writes the new structure to `config.json.tmp` and confirms it is valid JSON.
3.  **Swap**: Atomically replaces the original file with the verified temporary file.

### Industrial Hardening (Nexus Tier)
In **Permanent (Industrial)** mode, the environment triggers:
*   **Schema Validation**: Loads IDE-specific JSON schemas from the Nexus home to verify field types and required properties.
*   **Permissions Lockdown**: Automatically applies `chmod +x` to any scripts or python binaries injected into the configuration.

---

## 📝 Metadata
*   **Status**: Hardened (Phase 9)
*   **Developer**: l00p3rl00p
*   **Reference**: [ARCHITECTURE.md](./ARCHITECTURE.md) | [USER_OUTCOMES.md](./USER_OUTCOMES.md)
