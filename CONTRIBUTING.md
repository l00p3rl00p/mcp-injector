# Contributing Guide

Welcome! We appreciate your interest in improving the MCP JSON Injector.

---

## 📋 Table of Contents

1. [Our Philosophy](#-our-philosophy)
2. [The Golden Rule](#-the-golden-rule)
3. [Ways to Contribute](#-ways-to-contribute)
4. [Getting Started](#-getting-started)
5. [Review Process](#-review-process)

---

## 🔍 Our Philosophy

We believe in radical improvement. We will accept **any edit that makes the project better**. Whether it's a bug fix, a new feature, a documentation update, or a performance improvement—if it adds value, we want it.

---

## 🔱 The Golden Rule: Maintain Package Linkage

This repository is part of a 3-repository suite that forms the **Git-Packager** workspace:

1. **mcp-injector** (this tool)
2. **mcp-server-manager**
3. **repo-mcp-packager**

> **CRITICAL**: You must ensure that your changes **do not break the link** between these three repositories. They are tightly integrated and depend on each other to function correctly as a whole.

* **Do** improve individual components and logic.
* **Do not** break the interoperability or the bootstrap/integration patterns between them.

If your change affects the integration, please ensure you have tested it across all three repositories.

---

## 🌟 Ways to Contribute

* **Report Bugs**: Open an issue if you find something broken.
* **Suggest Features**: We're always looking for ways to make MCP management easier.
* **Submit PRs**: We love direct improvements to the code.
* **Documentation**: Help us make our guides clearer for everyone.

---

## ⚡ Getting Started

### Development Environment
The injector is designed to be standalone and zero-dependency.
1. Clone the repository.
2. Ensure you have Python 3.6+ installed.
3. Run `python mcp_injector.py --help` to verify the environment.

### Project Structure
* `mcp_injector.py`: The single-file entry point and library.
* `USER_OUTCOMES.md`: Use this to understand the project goals.
* `README.md`: The primary documentation.

---

## 📝 Review Process

1. **Check for integration**: Does this break the other Git-Packager tools?
2. **Validate JSON logic**: Ensure the core "no bracket hell" promise is maintained.
3. **Standalone Check**: Does the tool still work as a single file with zero dependencies?

Once these are verified, we aim for a quick review and merge cycle.
