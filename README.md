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
9. [Standalone vs Integrated: Understanding the Trade-offs](#-standalone-vs-integrated-understanding-the-trade-offs)
10. [Contributing](#-contributing)
11. [License](#-license)

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
python mcp_injector.py --bootstrap
```

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
| --- | --- |
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

* Drop it into any project
* Share it in a new repo
* Include it in your installer scripts
* Use it as a library (`from mcp_injector import MCPInjector`)

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
| --- | --- |
| **mcp-injector** (this tool) | Safely manage MCP server configs in IDE JSON files |
| **mcp-server-manager** | Discover and track MCP servers across your system |
| **repo-mcp-packager** | Install and package MCP servers with automation |

### Standalone vs. Integrated

* **Standalone**: This tool works perfectly on its own with zero dependencies.
* **Integrated**: When used with the other components, you get:
  + Automatic server validation before adding to IDE configs
  + One-click workspace setup with `python mcp_injector.py --bootstrap`
  + Cross-tool awareness (e.g., check if a server is running before configuring)

### Bootstrap the Workspace

```bash
python mcp_injector.py --bootstrap
```

This will:

1. Check which Git-Packager components are present
2. Offer to fetch missing components from GitHub
3. Set up the complete workspace for enhanced functionality

**You're always in control**: The bootstrap process asks for permission before fetching anything.

---

## 🎯 Standalone vs Integrated: Understanding the Trade-offs

### Can This Tool Work Standalone?

**Yes, absolutely.** This is a zero-dependency tool that works perfectly on its own. Understanding what you gain and lose helps you decide how to use it.

---

### 📊 Standalone Usage

**What you can do:**
- ✅ **Edit IDE configs safely** without breaking JSON
- ✅ **Add/remove servers** with automatic validation
- ✅ **Create backups** before every change
- ✅ **List configured servers** across all IDEs
- ✅ **Detect IDE installations** automatically
- ✅ **Work with any JSON config** (not just predefined IDEs)
- ✅ **Use as a library** in your own scripts

**What you cannot do:**
- ❌ **Know if servers are valid** before adding (requires `mcp-server-manager` for validation)
- ❌ **Install servers automatically** (requires `repo-mcp-packager`)
- ❌ **Verify servers are running** before configuring (requires `mcp-server-manager`)
- ❌ **One-click "discover and configure"** (requires full suite)

**Best for:**
- Users who already have MCP servers installed elsewhere
- Manual server management workflows
- Teams with custom installation processes
- Integration into existing automation scripts
- Anyone who just needs safe JSON editing

---

### 🚀 Integrated Usage (Full Git-Packager Suite)

**What you gain with `mcp-server-manager`:**
- ✅ **Validation before config** - check if server exists and is valid
- ✅ **Running status checks** - don't add servers that aren't working
- ✅ **Inventory integration** - see all servers, click to add to IDE
- ✅ **Auto-discovery** - injector knows about all detected servers
- ✅ **Consistency** - ensure IDE configs match actual installations

**What you gain with `repo-mcp-packager`:**
- ✅ **End-to-end flow** - install server → auto-configure IDE
- ✅ **No manual paths** - packager tells injector where servers live
- ✅ **Environment awareness** - correct venv/Docker paths automatically
- ✅ **One command setup** - from repo to working IDE integration
- ✅ **Uninstall coordination** - remove from IDE when server uninstalled

**Best for:**
- Users building MCP ecosystems from scratch
- Teams wanting automated, consistent setups
- Anyone who values "drop and run" simplicity
- Developers managing multiple MCP servers
- Organizations standardizing MCP deployments

---

### 🤔 Decision Matrix

| Your Situation | Recommended Setup |
| --- | --- |
| "I just need to fix my broken IDE config JSON" | **Standalone** `mcp-injector` |
| "I manually install servers, just need safe config editing" | **Standalone** `mcp-injector` |
| "I want to validate servers exist before adding" | **Add** `mcp-server-manager` |
| "I want automated install → configure workflow" | **Add** `repo-mcp-packager` |
| "I want complete automation: discover → install → configure" | **Full suite** (all 3 tools) |
| "I'm integrating into my own automation" | **Standalone** `mcp-injector` (use as library) |

---

### 💡 Real-World Scenarios

**Scenario 1: You broke your Claude config manually**
```bash
# Standalone is perfect
python mcp_injector.py --client claude --list
# Fix it or restore from backup
```

**Scenario 2: You installed an MCP server manually**
```bash
# Standalone works great
python mcp_injector.py --client claude --add
# Enter the path manually
```

**Scenario 3: You want to try a new MCP server from GitHub**
```bash
# Without full suite: Manual install, then manual config
git clone https://github.com/example/mcp-server
cd mcp-server
npm install
# Now use injector with manual paths

# With full suite: One command
python bootstrap.py --install-and-configure example/mcp-server
# Done. Server installed and IDE configured.
```

---

### 💡 Philosophy: True to Itself

This tool follows the principle of being **completely self-contained** with **zero required dependencies**. It does exactly what it promises: safely manages IDE JSON configs.

When integrated with the other components, it becomes part of a **truly autonomous system** where:
1. Servers are discovered automatically
2. Servers are installed automatically
3. IDEs are configured automatically
4. Everything stays in sync

**The injector is the "bridge" between your servers and your IDE.**
- Standalone = you build both ends of the bridge manually
- Integrated = the full system builds the bridge for you

You choose the level of automation you need.

---

## 🤝 Contributing

We welcome contributions! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for details.
**Note**: This tool is part of a 3-repo suite; ensure changes do not break integration.

---

## 📝 License

This project is open-source and provided "as-is". See the repository for license details.

---

## 👤 Author

Developed by the Git-Packager team.
