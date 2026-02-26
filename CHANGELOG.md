# Changelog - MCP Surgeon (mcp-injector)

## [3.3.1] - 2026-02-20

### Changed
- **Suite Version Sync**: Aligned component and docs to Nexus `v3.3.1`.

## [3.2.1] - 2026-02-19

### Improvements
- **Interactive Setup**: Integrated Surgeon into the root `./nexus.sh` flow for guided IDE configuration.
- **Suite Sync**: Version alignment with Nexus v3.2.1.

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

## [3.3.5] - 2026-02-25

### Added
- **Concurrent Injection ORT (GAP-R4)**: `tests/test_ort_concurrent_injection.py` — 2 tests, 6 total thread assertions. Proves that simultaneous `MCPInjector.add_server()` calls produce valid JSON (no corruption, no stray `.tmp` files). The atomic `temp_path.replace()` rename-guard holds under POSIX races; one thread retries cleanly when the tmp is already promoted.

### Fixed
- No source changes — the atomic write was already correct. Test adds the missing evidence.

---
*Status: Production Ready (v3.3.5)*

