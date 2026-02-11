# User Outcomes - MCP JSON Injector

This document outlines the goals and expected outcomes for users of the MCP JSON Injector.

---

## ⚡ Quick Summary
* **Primary Goal**: Manage MCP server configurations safely without manual JSON editing.
* **Secondary Goal**: Ensure interoperability across different IDEs and the Git-Packager workspace.

---

## 📋 Table of Contents
1. [Core Outcomes](#-core-outcomes)
2. [Scenarios](#-scenarios)
3. [Success Metrics](#-success-metrics)

---

## 🔍 Core Outcomes

As a user, I want:

### 1. Safety and Reliability
* **No Broken Configs**: I want to add or remove servers without worrying about missing commas or mismatched brackets.
* **Automatic Backups**: I want the tool to save my current configuration before making any changes.
* **Validation**: I want the tool to verify that the final JSON is valid before saving it.

### 2. Convenience
* **Interactive Prompts**: I want to be guided through the process of adding a server, including choosing from common presets.
* **Client Auto-Detection**: I want the tool to know where my IDE config files are located without me having to look them up.
* **Idempotent Operations**: I want to be able to run the same command multiple times and have it result in a consistent state.

### 3. Integrated Experience
* **Workspace Awareness**: I want the injector to work seamlessly with `mcp-server-manager` and `repo-mcp-packager`.
* **One-Click Setup**: I want to be able to bootstrap my entire workspace from a single command.

### 4. Universal Observability
* **Visual Status**: The user can see the health and connection status of all Nexus components (Observer, Librarian, Injector, Activator) in a single dashboard.
* **Graceful Degradation**: The system functions even if components are missing, clearly indicating what is available vs. what needs installation.

### 5. Resilient Lifecycle
* **Atomic Rollback**: If an installation fails at any step, the system automatically reverts to a clean state, leaving no partial artifacts.
* **Safe Upgrades**: The installer respects existing configurations and only applies necessary updates, preventing "config drift" or data loss.

---

## 🚀 Roadmap to 100% Compliance

To fully align with these outcomes, the following enhancements are planned:

*   **Observability**: The GUI must eventually show *live* metrics (CPU/Memory) for the industrial tier, not just static "Presence".
*   **Usability**: The "Librarian CRUD" tools need a UI frontend. Currently, they are "Headless Tools" only.
*   **Resilience**: While `start_gui.sh` exists, the Python entry point (`python -m mcp_inventory.cli`) is more cross-platform compatible and should be the primary recommendation in all docs.

---

## 💻 Scenarios

### Scenario 1: First-time MCP User
* **Action**: User wants to add their first MCP server to Claude Desktop.
* **Outcome**: User runs `python mcp_injector.py --client claude --add`, selects a preset, and the server is instantly available in Claude after a restart.

### Scenario 2: Cleaning up Old Servers
* **Action**: User has several experimental servers they no longer use.
* **Outcome**: User lists servers with `--list` and removes them by name with `--remove`, keeping their config clean and valid.

---

## 📈 Success Metrics

* **Zero Syntax Errors**: Users should never experience a "broken JSON" error in their IDE after using this tool.
* **Time Saved**: Reducing the time spent looking for config paths and manually editing JSON.
* **Replication Ease**: Agents can reliably configure new environments without human intervention.
