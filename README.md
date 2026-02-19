# MCP Surgeon: The Configuration Injector (mcp-injector)

**The Precision Configuration Tool for the Workforce Nexus.**

The **Surgeon** (`mcp-injector`) is responsible for the delicate task of modifying IDE configuration files to "inject" MCP servers. In v3.2.1, it is fully integrated into the **True Start** protocol for seamless onboarding.

## 🚀 Quick Start (Suite Mode)

The Surgeon is automatically triggered during the master setup:
```bash
../nexus.sh
```

**Standalone Interactive Config:**
```bash
python3 mcp_injector_install.sh
```

---

## 🌟 Capabilities (v3.2.1)

### 1. Multi-Client Auto-Detection
Natively understands the configuration formats and locations for:
- **Claude Desktop** (`claude_desktop_config.json`)
- **Cursor**
- **Artifacts / AI Studio** (Experimental)

### 2. Guarded Injections
- **Atomic Backups**: Every write creates a `.bak` copy of your JSON config.
- **Syntactic Validation**: Prevents injection if the target JSON is invalid.
- **Noclobber-Ready**: Respects the Global Security Mandate for file integrity.

### 3. Suite Integration
- **Direct Attachment**: Can be called by the `Activator` to immediately register newly forged servers into your preferred IDE.
- **Zero-Dep**: No requirements outside the Python Standard Library.

---

## 🛠️ Global Command Reference

| Command | Action |
| :--- | :--- |
| `mcp-surgeon --list` | List all configured servers in detected clients. |
| `mcp-surgeon --client claude --add X` | Surgical injection into Claude Desktop. |
| `mcp-surgeon --client cursor --remove Y` | Surgical removal from Cursor. |

---

## 📝 Metadata
* **Status**: Production Ready (v3.2.1)
* **Part of**: The Workforce Nexus Suite
