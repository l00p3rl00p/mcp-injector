# The Surgeon: Features & Commands

## Overview
**The Surgeon (`mcp-injector`)** is the configuration manager for the Workforce Nexus. It handles the delicate task of modifying complex JSON configuration files for various IDEs without breaking them.

## Features

### 1. 💉 Surgical Injection
*   **Precision Parsing**: Reads existing JSON configs, adds/removes MCP server entries, and writes them back atomically.
*   **Backup & Safety**: Automatically creates backups before modification. Validates JSON integrity before writing.
*   **Atomic Writes**: Uses temp files and atomic renames to prevent partial writes.

### 2. 🤝 Universal Compatibility
*   **Known Clients**: Pre-configured paths for:
    *   Claude Desktop
    *   Cursor
    *   Xcode
    *   VS Code
    *   Google AI Studio
    *   Google NotebookLM (CLI)
*   **Custom Paths**: Can target any JSON config file via `--config`.

### 3. 🔄 Global Sync
*   **Nexus Integration**: Updates the global `~/.mcp-tools/config.json` whenever it modifies a known client, keeping the entire suite aware of your tools.

## Command Reference

### Interactive Mode
```bash
# Add a server with a guided wizard
python mcp_injector.py --client claude --add
```

### Scripting / Headless
```bash
# Add a specific server (great for installers)
python mcp_injector.py --client cursor --add \
  --name "my-server" \
  --command "python" \
  --args "/path/to/server.py"

# Remove a server
python mcp_injector.py --client claude --remove "my-server"
```

### Discovery
```bash
# See where The Surgeon looks for configs
python mcp_injector.py --list-clients

# See what servers are currently installed in Claude
python mcp_injector.py --client claude --list
```

---
**Part of the Workforce Nexus**
*   **The Surgeon**: `mcp-injector` (Configuration)
*   **The Observer**: `mcp-server-manager` (Dashboard)
*   **The Activator**: `repo-mcp-packager` (Automation)
*   **The Librarian**: `mcp-link-library` (Knowledge)
