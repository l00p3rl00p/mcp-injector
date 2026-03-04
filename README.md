# MCP Surgeon: The Configuration Injector (mcp-injector)

**The Precision Configuration Tool for the Workforce Nexus.**

The **Surgeon** (`mcp-injector`) is responsible for the delicate task of modifying IDE configuration files to "inject" MCP servers. It provides a safe, schema-aware way to manage IDE toolsets.

---

## 🚀 Quick Start (Suite Mode)

The Surgeon is automatically triggered during the master setup:
```bash
../nexus.sh
```

**Standalone Interactive Config:**
```bash
bash mcp_injector_install.sh
```

---

## 🌟 Capabilities

### 1. Multi-Client Auto-Detection
Natively understands the configuration formats and locations for:
- **Claude Desktop** (`claude_desktop_config.json`)
- **Cursor**
- **AI Studio / Codex**

### 2. Guarded Injections
- **Atomic Backups**: Every write creates a timestamped `.bak` copy.
- **Syntactic Validation**: Prevents injection into malformed JSON files.
- **Noclobber-Ready**: Respects suite-wide file integrity standards.

### 3. Suite Integration
- **Direct Attachment**: Can be called by the `Activator` to register newly forged servers.
- **Zero-Dep**: No requirements outside the Python Standard Library.

---

## 🛠️ Global Command Reference

| Command | Action |
| :--- | :--- |
| `mcp-surgeon --list` | List all configured servers in detected clients. |
| `mcp-surgeon --client claude --add X` | Surgical injection into Claude Desktop. |
| `mcp-surgeon --client cursor --remove Y` | Surgical removal from Cursor. |

---

## 🔄 Drift Lifecycle Integration

The Nexus Injector works in tandem with the Drift Lifecycle system:
- **Detection**: Monitors injected configurations for drift against current inventory.
- **Safe Updates**: Surgical JSON edits ensure zero configuration corruption.
- **Targeting**: Supports both core and forged server injections.

---

## 📝 Metadata
* **Status**: 🟢 Production Ready (v3.4.2)
* **Part of**: The Workforce Nexus Suite
