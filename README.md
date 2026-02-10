# MCP JSON Injector

**A standalone tool to safely add/remove MCP servers config from config files.**

No more broken JSON. No more bracket hell.

---

## 📦 Installation

Get the GIT REPOSITORY and MCP PACKAGER from the [repo-mcp-packager](https://github.com/l00p3rl00p/repo-mcp-packager/) repository and drop it in the root of your project. That's it—no additional setup required.

**Or use the Universal Bootstrapper:**
```bash
python mcp_injector.py --bootstrap
```
This will check for and optionally fetch the other Git-Packager workspace components (`mcp-server-manager`, `repo-mcp-packager`) to enable enhanced functionality.

## 🚀 Quick Start

### 1. Copy the tool anywhere
```bash
# Copy to your PATH
cp mcp_injector.py ~/bin/mcp-inject
chmod +x ~/bin/mcp-inject

# Or use it directly
python mcp_injector.py --help
```

### 2. Add a server (Interactive Mode)
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

## 📖 Usage Examples

### List All Known Clients
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
```bash
python mcp_injector.py --client claude --remove agent-browser
```

### Use a Custom Config Path
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

## 📦 Share This Tool

**This file is standalone.** You can:
- Drop it into any project
- Share it in a new repo
- Include it in your installer scripts
- Use it as a library (`from mcp_injector import MCPInjector`)

**Zero dependencies.** Just Python 3.6+.

---

## 🆘 Troubleshooting

### "Config file doesn't exist"
The tool will create it for you automatically.

### "Invalid JSON"
Your config is broken. Check the backup:
```bash
cat ~/path/to/config.json.backup
```

### "Permission denied"
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
