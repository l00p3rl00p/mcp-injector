# MCP JSON Injector

**A standalone tool to safely add/remove MCP servers config from config files.**

No more broken JSON. No more bracket hell. This tool ensures your MCP configurations are always valid, backed up, and correctly formatted for all supported IDEs.

---

## ⚡ Quick Start

Get the GIT REPOSITORY and MCP PACKAGER from the [repo-mcp-packager](https://github.com/l00p3rl00p/repo-mcp-packager/) repository and drop it in the root of your project. That's it—no additional setup required.

**Or use the Universal Bootstrapper:**
```bash
python mcp_injector.py --bootstrap
```
This will check for and optionally fetch the other workspace components (`mcp-server-manager`, `repo-mcp-packager`).

### 2. Add an MCP Server
The easiest way to add a server is using interactive prompts:
```bash
python mcp_injector.py --client claude --add
```

---

## 📋 Table of Contents

1. [Overview](#-overview)
2. [Features](#-features)
3. [Installation](#-installation)
4. [Usage Examples](#-usage-examples)
5. [Advanced Usage](#-advanced-usage)
6. [Safety Features](#-safety-features)
7. [Troubleshooting](#-troubleshooting)
8. [Git-Packager Workspace](#-git-packager-workspace)
9. [Contributing](#-contributing)
10. [License](#-license)

---

## 🔍 Overview

The MCP JSON Injector is a zero-dependency Python tool designed to manage MCP server configurations in IDE JSON files. It handles the "bracket hell" of manual JSON editing, ensuring that commas and brackets are correctly placed every time.

Whether you're adding a new server, removing an old one, or listing what's currently configured, the injector provides a safe and idempotent way to manage your environment.

---

## 🌟 Features

* **Interactive Mode**: Simple prompts to guide you through adding/removing servers.
* **JSON Validation**: Prevents saving if the resulting JSON would be invalid.
* **Automatic Backups**: Always creates a `.backup` file before any modification.
* **Standalone**: Single file with zero dependencies, works on Python 3.6+.
* **Idempotent**: Safe to run multiple times with the same input.
* **IDE Support**: Pre-configured paths for Claude, Xcode, Codex, Cursor, and more.

---

## 🛠 Installation

### As a Standalone Tool
Copy `mcp_injector.py` to your local `bin` directory for easy access:
```bash
cp mcp_injector.py ~/bin/mcp-inject
chmod +x ~/bin/mcp-inject
```

### via Git-Packager Workspace
The injector is part of a larger suite. You can bootstrap the entire workspace:
```bash
# The easiest way - interactive prompts
python mcp_injector.py --client claude --add
```

**What it does:**
- Shows you preset options (Agent Browser, AI Studio, etc.)
- Asks for custom values if needed
- Validates your JSON
- Creates a backup before modifying
- Shows you a summary of all servers

---

## 💻 Usage Examples

### List All Known Clients
See which IDEs the tool has detected on your system:
```bash
python mcp_injector.py --list-clients
```
**Output:**
```
📂 Known MCP Client Locations:

✅ XCODE
   ~/Library/Developer/Xcode/UserData/MCPServers/config.json

❌ CODEX
   ~/Library/Application Support/Codex/mcp_servers.json

✅ CLAUDE
   ~/Library/Application Support/Claude/claude_desktop_config.json
```

### Add a Server to Claude
```bash
python mcp_injector.py --client claude --add
```
**Interactive prompts:**
```
🔧 Add MCP Server (Interactive Mode)

Quick Presets:
  1. Agent Browser (Vercel)
  2. AI Studio (Google)
  3. NotebookLM
  4. Custom (manual entry)

Select preset [1-4]: 1

📦 Using preset: agent-browser
   Command: npx -y @vercel/agent-browser mcp

Add environment variables? [y/N]: n

📝 Summary:
   Name: agent-browser
   Command: npx
   Args: ['-y', '@vercel/agent-browser', 'mcp']

Proceed? [Y/n]: y

📦 Backup created: ~/Library/Application Support/Claude/claude_desktop_config.json.backup
✅ Config updated: ~/Library/Application Support/Claude/claude_desktop_config.json
🎉 Added server 'agent-browser'

📊 Current servers: agent-browser
```

### List Servers in a Config
```bash
python mcp_injector.py --client claude --list
```
**Output:**
```
📋 Configured MCP Servers (2):

🔧 agent-browser
   Command: npx -y @vercel/agent-browser mcp

   shesha
   Command: /Users/you/shesha/.venv/bin/librarian mcp run
```
*(🔧 indicates Shesha-managed)*

### Remove a Server
Safely remove a server by its name:
```bash
python mcp_injector.py --client claude --remove agent-browser
```

### Custom Config Path
Use the injector with any JSON file:
```bash
python mcp_injector.py --config ~/custom/path/config.json --add
```

---

## 🛡️ Safety Features

1. **Automatic Backup**: Creates `.backup` file before modifying
2. **JSON Validation**: Won't save if the JSON is invalid
3. **Bracket Management**: Handles commas and brackets automatically
4. **Idempotent**: Running twice with the same input is safe (overwrites)

---

## 🎯 Use Cases

| Scenario | Command |
|----------|---------|
| First-time setup | `--client claude --add` |
| Add 2nd server | `--client claude --add` (no manual JSON editing!) |
| Check what's installed | `--client claude --list` |
| Clean up old servers | `--client claude --remove old-server` |
| Backup before changes | (automatic with every `--add`) |

---

## 🔧 Advanced: Automated Use

**Non-interactive server addition** (for scripts):
```python
from mcp_injector import MCPInjector
from pathlib import Path

injector = MCPInjector(Path("~/Library/Application Support/Claude/claude_desktop_config.json"))
injector.add_server(
    name="my-server",
    command="npx",
    args=["-y", "my-package"],
    env={"API_KEY": "secret"}
)
```

---

## 🛡️ Safety Features

The tool is built with a "safety-first" mindset:
1. **Backups**: Every `--add` or `--remove` triggers a backup.
2. **Pre-flight Check**: Validates existing JSON before attempting edits.
3. **Atomic Writes**: Uses temporary files and moves to ensure no partial writes.
4. **Validation**: Won't save if the JSON is invalid.

## 📦 Share This Tool

**This file is standalone.** You can:
- Drop it into any project
- Share it in a new repo
- Include it in your installer scripts
- Use it as a library (`from mcp_injector import MCPInjector`)
---

## 🐛 Troubleshooting

### "Config file doesn't exist"
The tool will create a valid minimal config file for you automatically if none exists.

### "Invalid JSON"
If your config is already broken, the tool will warn you. You can check the backup:
```bash
cat ~/path/to/config.json.backup
```

### "Permission denied"
Ensure the config file is writable by your user:
```bash
chmod +w ~/path/to/config.json
```

---

## 🎉 No More Bracket Hell

**Before (manual editing):**
```json
{
  "mcpServers": {
    "server-1": { ... }
    "server-2": { ... }   ← Missing comma! 💥
  }
}
```

**After (using the injector):**
```bash
python mcp_injector.py --client claude --add
```
✅ Perfect JSON every time.

---

## 🤝 Better Together: Git-Packager Workspace

This tool is part of the **Git-Packager** workspace, which includes:

| Tool | Purpose |
|------|--------|
| **mcp-injector** (this tool) | Safely manage MCP server configs in IDE JSON files |
| **mcp-server-manager** | Discover and track MCP servers across your system |
| **repo-mcp-packager** | Install and package MCP servers with automation |

### Standalone vs. Integrated

- **Standalone**: This tool works perfectly on its own with zero dependencies.
- **Integrated**: When used with the other components, you get:
  - Automatic server validation before adding to IDE configs
  - One-click workspace setup with `python mcp_injector.py --bootstrap`
  - Cross-tool awareness (e.g., check if a server is running before configuring)

### Bootstrap the Workspace

```bash
python mcp_injector.py --bootstrap
```

This will:
1. Check which Git-Packager components are present
2. Offer to fetch missing components from GitHub
3. Set up the complete workspace for enhanced functionality

**You're always in control**: The bootstrap process asks for permission before fetching anything.

### Integrated Benefits
When used as part of the workspace, the injector can:
- Automatically validate servers before adding them to IDE configs.
- Bootstrap missing components with one command.

---

## 🤝 Contributing

We welcome contributions! Please see [CONTRIBUTING.md](./CONTRIBUTING.md) for details. 
**Note**: This tool is part of a 3-repo suite; ensure changes do not break integration.

---

## 📝 License

This project is open-source and provided "as-is". See the repository for license details.

---

## 👤 Author

Developed by the Git-Packager team.