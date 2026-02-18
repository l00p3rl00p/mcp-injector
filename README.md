# MCP Surgeon: The Configuration Injector (mcp-injector)

**The Precision Configuration Tool for the Workforce Nexus.**

The **Surgeon** (`mcp-injector`) is responsible for the delicate task of modifying IDE configuration files to "inject" MCP servers. It handles the complexity of JSON manipulation, path resolution, and backups, ensuring your IDEs (Claude Desktop, Cursor, etc.) are always correctly connected.

---

## 🌟 Core Capabilities

### 1. Multi-Client Support
Natively understands the configuration formats and locations for:
- **Claude Desktop** (`claude_desktop_config.json`)
- **Cursor** (via `.cursor/mcp.json` or equivalent)
- **Generic Clients** (Standardized MCP config compliance)

### 2. Safety First
- **Automatic Backups**: Never modifies a file without creating a timestamped backup first.
- **Validation**: Verifies the JSON syntax before and after modification.
- **Atomic Writes**: Ensures no partial updates corrupt your config.

### 3. Interactive & Headless
- **Interactive**: Guides you through selecting clients and servers.
- **Headless**: Can be scripted by agents to auto-configure environments during setup.

---

## 🛠️ Usage

### Quick Injection
```bash
# Add a server to Claude Desktop
python3 mcp_injector.py --client claude --add "my-server" --command "python3" --args "server.py"
```

### Removal
```bash
# Remove a server
python3 mcp_injector.py --client claude --remove "my-server"
```

### Discovery
```bash
# List all configured servers in Claude
python3 mcp_injector.py --client claude --list
```

### Standalone Operation
The Surgeon is a single-file python script (`mcp_injector.py`) with zero external dependencies beyond the standard library. It can be dropped into any project to manage MCP configurations.

---

## 📝 Metadata
* **Status**: Production Ready
* **Author**: l00p3rl00p
* **Part of**: The Nexus Workforce Suite
