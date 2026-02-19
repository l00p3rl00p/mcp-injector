# Changelog - MCP Surgeon (mcp-injector)

## [3.2.0] - 2026-02-19

### Fixes
- `--list` without `--client` now exits with code 1 and a clear, actionable error message instead of a cryptic failure.

---

## [2.0.0] - 2026-02-18

### 🛡️ Safety & Governance
- **ATP Safe List Integration**: Implemented tiered execution categories (Green, Yellow, Black) to govern agent behavior.
- **Noclobber Enforcement**: Hardened shell injection to respect `set -o noclobber` protocol.
- **Improved Validation**: Added pre-injection checks for configuration schema compatibility with Nexus 2.0.

### Added
- **Startup Detection**: Enhanced detection for aistudio, claude-desktop, and cursor.
- **Component-Aware Injection**: Prompts for specific Nexus server injection (e.g., Librarian) while keeping CLI tools (Activator/Observer) out of MCP configs.

### Fixed
- **Permission Resilience**: Improved error handling for unwritable configuration directories.

---

## [1.0.0] - 2026-02-09
- Initial release of the MCP Surgeon.
- Support for atomic JSON injection in IDE configs.
- Surgical rollback capabilities.

---
*Status: Production Ready (v2.0.0)*
