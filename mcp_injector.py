#!/usr/bin/env python3
"""
MCP JSON Injector - Safely add MCP servers to IDE config files

This is a standalone tool that handles the bracket/comma logic for you.
Just point it at your config file and tell it what to add.

Usage:
    python mcp_injector.py --config ~/path/to/config.json --add
    python mcp_injector.py --config ~/path/to/config.json --remove server-name
    python mcp_injector.py --list-clients
"""

import json
import sys
import os
import argparse
import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List
import importlib.util
import shutil
import shlex

try:
    from nexus_session_logger import NexusSessionLogger
    session_logger = NexusSessionLogger()
except ImportError:
    session_logger = None

__version__ = "3.3.1"

# Best-practice guardrails: these Nexus binaries are CLIs, not MCP servers over stdio.
# Injecting them into MCP clients (Claude/Codex/etc.) will cause JSON parse errors.
KNOWN_NONSERVER_BINARIES = {
    "mcp-activator",
    "mcp-observer",
    "mcp-surgeon",
}

# Known MCP client config locations
GLOBAL_CONFIG_KEY = "ide_config_paths"

# Nexus Support: Try to load high-confidence libraries from the central venv
def inject_nexus_env():
    try:
        home = Path.home() if sys.platform != "win32" else Path(os.environ['USERPROFILE'])
        nexus_venv = home / ".mcp-tools" / ".venv"
        if nexus_venv.exists():
            # Add site-packages to sys.path
            import platform
            if platform.system() == "Windows":
                site_pkgs = nexus_venv / "Lib" / "site-packages"
            else:
                # Find python version dir
                lib_dir = nexus_venv / "lib"
                py_dirs = list(lib_dir.glob("python3*"))
                if py_dirs:
                    site_pkgs = py_dirs[0] / "site-packages"
                else:
                    return
            
            if site_pkgs.exists() and str(site_pkgs) not in sys.path:
                sys.path.insert(0, str(site_pkgs))
    except Exception:
        pass

inject_nexus_env()

def get_global_config_path():
    if sys.platform == "win32":
        return Path(os.environ['USERPROFILE']) / ".mcp-tools" / "config.json"
    return Path.home() / ".mcp-tools" / "config.json"

def update_global_config(ide_name: str, path: str):
    """Sync IDE config path to global Nexus config"""
    config_path = get_global_config_path()
    try:
        if config_path.exists():
            try:
                data = json.loads(config_path.read_text())
            except json.JSONDecodeError:
                stamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
                corrupt_backup = config_path.with_suffix(f".json.corrupt.{stamp}")
                config_path.replace(corrupt_backup)
                print(f"⚠️  Recovered malformed global config: {corrupt_backup}")
                data = {}
        else:
            config_path.parent.mkdir(parents=True, exist_ok=True)
            data = {}

        if not isinstance(data, dict):
            data = {}
        if GLOBAL_CONFIG_KEY not in data or not isinstance(data.get(GLOBAL_CONFIG_KEY), dict):
            data[GLOBAL_CONFIG_KEY] = {}
        
        data[GLOBAL_CONFIG_KEY][ide_name] = str(Path(path).expanduser().resolve())
        
        with open(config_path, 'w') as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        print(f"⚠️  Failed to sync global config: {e}")

def _client_specs() -> Dict[str, Dict[str, List[str]]]:
    return {
        "xcode": {
            "configs": ["~/Library/Developer/Xcode/UserData/MCPServers/config.json"],
            "markers": ["/Applications/Xcode.app"]
        },
        "codex": {
            "configs": [
                "~/Library/Application Support/Codex/mcp_servers.json",
                "~/.config/codex/mcp_servers.json",
                "%APPDATA%/Codex/mcp_servers.json"
            ],
            "markers": [
                "/Applications/Codex.app",
                "~/Applications/Codex.app",
                "~/.config/Codex"
            ]
        },
        "claude": {
            "configs": [
                "~/Library/Application Support/Claude/claude_desktop_config.json",
                "~/.config/Claude/claude_desktop_config.json",
                "%APPDATA%/Claude/claude_desktop_config.json"
            ],
            "markers": [
                "/Applications/Claude.app",
                "~/Applications/Claude.app"
            ]
        },
        "cursor": {
            "configs": [
                "~/.cursor/mcp.json",
                "~/Library/Application Support/Cursor/mcp.json",
                "%APPDATA%/Cursor/mcp.json"
            ],
            "markers": ["/Applications/Cursor.app", "~/Applications/Cursor.app"]
        },
        "vscode": {
            "configs": [
                "~/.vscode/mcp_settings.json",
                "~/Library/Application Support/Code/User/mcp_settings.json",
                "%APPDATA%/Code/User/mcp_settings.json"
            ],
            "markers": ["/Applications/Visual Studio Code.app", "~/Applications/Visual Studio Code.app"]
        },
        "aistudio": {
            "configs": [
                "~/.config/aistudio/mcp_servers.json",
                "~/Library/Application Support/Google/AIStudio/mcp_servers.json",
                "%APPDATA%/Google/AIStudio/mcp_servers.json"
            ],
            "markers": [
                "/Applications/Google AI Studio.app",
                "~/Applications/Google AI Studio.app"
            ]
        },
        "google-antigravity": {
            "configs": [
                "~/.config/aistudio/mcp_servers.json",
                "~/Library/Application Support/Google/AIStudio/mcp_servers.json",
                "%APPDATA%/Google/AIStudio/mcp_servers.json"
            ],
            "markers": [
                "/Applications/Google AI Studio.app",
                "~/Applications/Google AI Studio.app"
            ]
        }
    }


def _expand_path(raw_path: str) -> Path:
    expanded = os.path.expandvars(raw_path)
    return Path(expanded).expanduser()


def get_known_clients() -> Dict[str, str]:
    mapping: Dict[str, str] = {}
    specs = _client_specs()
    for name, spec in specs.items():
        for candidate in spec["configs"]:
            path = _expand_path(candidate)
            if path.exists():
                mapping[name] = str(path)
                break
        if name not in mapping:
            mapping[name] = str(_expand_path(spec["configs"][0]))
    return mapping


KNOWN_CLIENTS = get_known_clients()


def detect_installed_clients() -> Dict[str, Dict[str, Any]]:
    detected: Dict[str, Dict[str, Any]] = {}
    for client, spec in _client_specs().items():
        config_candidates = [_expand_path(path) for path in spec["configs"]]
        marker_candidates = [_expand_path(path) for path in spec["markers"]]

        existing_config = next((p for p in config_candidates if p.exists()), None)
        marker_hit = next((p for p in marker_candidates if p.exists()), None)

        installed = existing_config is not None or marker_hit is not None
        detected[client] = {
            "installed": installed,
            "config_path": existing_config or config_candidates[0],
            "has_config": existing_config is not None,
            "has_marker": marker_hit is not None,
            "marker": str(marker_hit) if marker_hit else None
        }
    return detected


def get_nexus_home() -> Path:
    if sys.platform == "win32":
        return Path(os.environ['USERPROFILE']) / ".mcp-tools"
    return Path.home() / ".mcp-tools"


def detect_package_components() -> Dict[str, Dict[str, Any]]:
    """
    Detect Nexus-created executable components and build injectable server configs.
    """
    nexus_home = get_nexus_home()
    bin_dir = nexus_home / "bin"

    components: Dict[str, Dict[str, Any]] = {}
    if not bin_dir.exists():
        return components

    # Important: Only include binaries that speak MCP over stdio (JSON-RPC on stdout).
    # Many Nexus CLIs (e.g. `mcp-activator`, `mcp-observer`, `mcp-surgeon`) are *not*
    # MCP servers and will cause clients like Claude to throw JSON parse errors if injected.
    candidates = {
        "nexus-librarian": ("mcp-librarian", ["--server"]),
    }

    for server_name, (binary_name, args) in candidates.items():
        binary_path = bin_dir / binary_name
        if binary_path.exists():
            components[server_name] = {
                "command": str(binary_path),
                "args": args,
                "source": "nexus-bin"
            }

    return components


class MCPInjector:
    def __init__(self, config_path: Path):
        self.config_path = config_path.expanduser()
        self.backup_path = self.config_path.with_suffix('.json.backup')
    
    def load_config(self) -> Dict[str, Any]:
        """Load existing config or create empty structure"""
        if not self.config_path.exists():
            print(f"⚠️  Config file doesn't exist. Will create: {self.config_path}")
            try:
                self.config_path.parent.mkdir(parents=True, exist_ok=True)
            except PermissionError:
                print(f"❌ Permission denied creating parent directory: {self.config_path.parent}")
                print("   Hint: choose --config in a writable location or adjust directory permissions.")
                sys.exit(1)
            except Exception as e:
                print(f"❌ Failed to prepare config directory: {e}")
                sys.exit(1)
            return {"mcpServers": {}}
        
        try:
            with open(self.config_path, 'r') as f:
                config = json.load(f)
            
            # Ensure mcpServers key exists
            if "mcpServers" not in config:
                config["mcpServers"] = {}
            
            return config
        except json.JSONDecodeError as e:
            print(f"❌ Invalid JSON in {self.config_path}")
            print(f"   Error: {e}")
            stamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
            corrupt_backup = self.config_path.with_suffix(f".json.corrupt.{stamp}")
            try:
                self.config_path.replace(corrupt_backup)
                print(f"🩹 Recovered by moving corrupt file to: {corrupt_backup}")
                return {"mcpServers": {}}
            except Exception as backup_error:
                print(f"❌ Recovery failed: {backup_error}")
                sys.exit(1)
        except Exception as e:
            print(f"❌ Failed to load config: {e}")
            sys.exit(1)
    
    def _structural_audit(self, old: Dict, new: Dict, path: str = ""):
        """
        Deep compare structures to detect unintended type changes (Schema Drift).
        Standard Tier (96% Confidence) protection.
        """
        for key, new_val in new.items():
            if key in old:
                old_val = old[key]
                if type(old_val) != type(new_val) and old_val is not None and new_val is not None:
                    print(f"❌ Structural Integrity Violation at '{path}{key}':")
                    print(f"   Expected {type(old_val).__name__}, got {type(new_val).__name__}")
                    raise TypeError(f"Schema drift detected at {key}")
                
                if isinstance(new_val, dict) and isinstance(old_val, dict):
                    self._structural_audit(old_val, new_val, f"{path}{key}.")

    def _validate_with_schema(self, config: Dict):
        """
        Validate against official JSON Schema if jsonschema is available.
        Industrial Tier protection.
        """
        try:
            from jsonschema import validate
            # Basic MCP server config schema
            schema = {
                "type": "object",
                "properties": {
                    "mcpServers": {
                        "type": "object",
                        "additionalProperties": {
                            "type": "object",
                            "properties": {
                                "command": {"type": "string"},
                                "args": {"type": "array", "items": {"type": "string"}},
                                "env": {"type": "object", "additionalProperties": {"type": "string"}}
                            },
                            "required": ["command"]
                        }
                    }
                }
            }
            validate(instance=config, schema=schema)
            # print("✅ Schema validation passed")
        except ImportError:
            pass # jsonschema not installed, skip
        except Exception as e:
            print(f"❌ JSON Schema Validation Failed: {e}")
            raise

    def save_config(self, config: Dict[str, Any]):
        """
        Save config with structural auditing, backup, and atomic write.
        """
        # 0. Validation (Tiered)
        if self.config_path.exists():
            try:
                old_data = self.config_path.read_text()
                if old_data.strip():
                    old_config = json.loads(old_data)
                    self._structural_audit(old_config, config)
            except Exception as e:
                print(f"⚠️  Structural audit failed: {e}")
                if not input("   Continue anyway? [y/N]: ").strip().lower() == 'y':
                    sys.exit(1)
        
        try:
            self._validate_with_schema(config)
        except Exception:
            sys.exit(1)

        # Create backup if file exists (best-effort)
        if self.config_path.exists():
            try:
                with open(self.backup_path, 'w') as f:
                    f.write(self.config_path.read_text())
                print(f"📦 Backup created: {self.backup_path}")
            except Exception as e:
                print(f"⚠️  Warning: Backup creation failed: {e}")
                print(f"   Continuing with config update...")
        
        # Validate JSON before writing
        try:
            json_str = json.dumps(config, indent=2)
        except Exception as e:
            print(f"❌ Failed to serialize JSON: {e}")
            sys.exit(1)
        
        # Atomic write: write to temp file, then rename
        temp_path = self.config_path.with_suffix('.json.tmp')
        try:
            with open(temp_path, 'w') as f:
                f.write(json_str)
            
            # Atomic rename (POSIX guarantees atomicity)
            temp_path.replace(self.config_path)
            print(f"✅ Config updated: {self.config_path}")
        except Exception as e:
            print(f"❌ Failed to write config: {e}")
            print(f"   Possible causes: disk full, permissions, or I/O error")
            # Clean up temp file if it exists
            if temp_path.exists():
                try:
                    temp_path.unlink()
                except Exception:
                    pass
            sys.exit(1)
            sys.exit(1)
    
        # Sync to global config if we can identify the IDE
        try:
            abs_path = str(self.config_path.resolve())
            for name, path in KNOWN_CLIENTS.items():
                if Path(path).expanduser().resolve() == self.config_path.resolve():
                    update_global_config(name, abs_path)
                    break 
        except Exception:
            pass

    def add_server(self, name: str, command: str, args: list, env: Optional[Dict[str, str]] = None, *, allow_unsafe_cli: bool = False):
        """Add or update an MCP server entry"""
        cmd_base = Path(command).name if "/" in command else command
        if cmd_base in KNOWN_NONSERVER_BINARIES and not allow_unsafe_cli:
            raise ValueError(
                f"Refusing to inject '{cmd_base}' as an MCP server. "
                "This appears to be a CLI, not an MCP stdio server. "
                "If you really intend this, pass allow_unsafe_cli=True at the callsite."
            )
        config = self.load_config()
        
        # Check if server already exists
        if name in config["mcpServers"]:
            print(f"⚠️  Server '{name}' already exists. Overwriting...")
        
        # Build server config
        server_config = {
            "command": command,
            "args": args
        }
        
        if env:
            server_config["env"] = env
        
        # Add marker for tracking
        server_config["_shesha_managed"] = True
        
        # Inject
        config["mcpServers"][name] = server_config
        
        # Save
        self.save_config(config)
        
        if session_logger:
            session_logger.log_command(f"inject {name}", "SUCCESS", result=str(self.config_path))
            
        print(f"🎉 Added server '{name}'")
        self.show_summary(config)
    
    def remove_server(self, name: str):
        """Remove an MCP server entry"""
        config = self.load_config()
        
        if name not in config["mcpServers"]:
            print(f"❌ Server '{name}' not found in config")
            return
        
        del config["mcpServers"][name]
        self.save_config(config)
        
        if session_logger:
            session_logger.log_command(f"remove {name}", "SUCCESS", result=str(self.config_path))
            
        print(f"🗑️  Removed server '{name}'")
        self.show_summary(config)
    
    def list_servers(self, *, json_mode: bool = False):
        """List all configured MCP servers"""
        config = self.load_config()
        servers = config.get("mcpServers", {})
        
        if json_mode:
            print(json.dumps(servers))
            return

        if not servers:
            print("📭 No MCP servers configured")
            return
        
        print(f"\n📋 Configured MCP Servers ({len(servers)}):\n")
        for name, cfg in servers.items():
            managed = "🔧 " if cfg.get("_shesha_managed") else "   "
            print(f"{managed}{name}")
            print(f"   Command: {cfg['command']} {' '.join(cfg.get('args', []))}")
            if cfg.get('env'):
                print(f"   Env: {list(cfg['env'].keys())}")
            print()
    
    def show_summary(self, config: Dict[str, Any]):
        """Show a summary of all servers after modification"""
        servers = config.get("mcpServers", {})
        print(f"\n📊 Current servers: {', '.join(servers.keys()) if servers else '(none)'}")


def interactive_add(injector: MCPInjector):
    """Interactive mode for adding a server"""
    print("\n🔧 Add MCP Server (Interactive Mode)\n")
    
    components = detect_package_components()
    has_npx = bool(shutil.which("npx"))

    # Menu options are intentionally "truthy":
    # - Suite servers are detected from the local install (recommended).
    # - npx items are templates (not detected) and only shown if npx exists.
    menu: Dict[str, tuple] = {}
    idx = 1
    if components:
        menu[str(idx)] = ("nexus-detected", None, None)
        idx += 1
    if has_npx:
        menu[str(idx)] = ("agent-browser", "npx", ["-y", "@vercel/agent-browser", "mcp"])
        idx += 1
        menu[str(idx)] = ("aistudio", "npx", ["-y", "aistudio-mcp-server"])
        idx += 1
        menu[str(idx)] = ("notebooklm", "npx", ["-y", "notebooklm-mcp-cli"])
        idx += 1
    menu[str(idx)] = ("custom", None, None)
    
    print("Choices:")
    if components:
        print(f"  1. MCP Nexus Suite (internal stdio servers)")
    if has_npx:
        base = 2 if components else 1
        print("\nTemplates (requires Node.js + npx; not auto-detected):")
        print(f"  {base}. Agent Browser (Vercel)")
        print(f"  {base + 1}. AI Studio (Google)")
        print(f"  {base + 2}. NotebookLM")
        idx_custom = base + 3
    else:
        idx_custom = 2 if components else 1
    print(f"\n  {idx_custom}. Custom (manual entry)")
    
    choice = input("\nSelect choice number (or 'custom' / 'nexus', Enter to cancel): ").strip().lower()
    if not choice:
        print("❌ Cancelled")
        sys.exit(0)

    if choice in {"c", "custom"}:
        # Map to the custom option regardless of numbering.
        for k, (name, _cmd, _args) in menu.items():
            if name == "custom":
                choice = k
                break
    if choice in {"n", "nexus"}:
        # Map to the suite-detected option regardless of numbering.
        for k, (name, _cmd, _args) in menu.items():
            if name == "nexus-detected":
                choice = k
                break
    
    if choice not in menu:
        print("❌ Invalid choice")
        sys.exit(1)
    
    preset_name, preset_cmd, preset_args = menu[choice]
    
    if preset_name == "nexus-detected":
        # Suite-detected MCP stdio servers (stdio JSON-RPC on stdout)
        ordered = sorted(components.items(), key=lambda kv: kv[0])
        print("\n📦 Detected Nexus MCP stdio servers:")
        for idx, (comp_name, comp) in enumerate(ordered, start=1):
            cmd = comp.get("command")
            args = comp.get("args", [])
            printable = f"{cmd} {' '.join(args)}".strip()
            print(f"  {idx}) {comp_name}: {printable}")

        raw = input("\nSelect server number (or Enter to cancel): ").strip()
        if not raw:
            print("❌ Cancelled")
            sys.exit(0)
        try:
            n = int(raw)
        except Exception:
            print("❌ Invalid choice")
            sys.exit(1)
        if n < 1 or n > len(ordered):
            print("❌ Invalid choice")
            sys.exit(1)

        name, comp = ordered[n - 1]
        command = str(comp["command"])
        args = list(comp.get("args", []))
        print(f"\n📦 Using suite server: {name}")
        print(f"   Command: {command} {' '.join(args)}".strip())

    elif preset_name == "custom":
        # Custom entry
        name = input("Server name: ").strip()
        command = input("Command (e.g., /path/to/bin or python3): ").strip()
        print("\nArgs tips:")
        print("  - Shell-style args:   --server --foo bar")
        print("  - Comma-separated:    --server,--foo,bar")
        print("  - Example (Librarian stdio): --server")
        args_input = input("Args: ").strip()
        if not args_input:
            args = []
        elif "," in args_input:
            args = [a.strip() for a in args_input.split(",") if a.strip()]
        else:
            args = shlex.split(args_input)
    else:
        # Preset
        name = preset_name
        command = preset_cmd
        args = preset_args
        print(f"\n📦 Using preset: {name}")
        print(f"   Command: {command} {' '.join(args)}")

    # Guardrail warning: avoid injecting known CLIs as MCP servers.
    cmd_base = Path(command).name if "/" in command else command
    if cmd_base in KNOWN_NONSERVER_BINARIES:
        print("\n⚠️  Warning: This command looks like a Nexus CLI, not an MCP stdio server.")
        print("   Injecting it into an MCP client can cause JSON parse errors and disconnects.")
        print("   If you meant to run a web MCP proxy, use an HTTP/SSE/WS proxy and connect web clients to it.")
        warn_confirm = input("Proceed anyway? [y/N]: ").strip().lower()
        if warn_confirm != "y":
            print("❌ Cancelled")
            sys.exit(0)
        allow_unsafe_cli = True
    else:
        allow_unsafe_cli = False
    
    # Env vars (optional)
    env = None
    add_env = input("\nAdd environment variables? [y/N]: ").strip().lower()
    if add_env == 'y':
        env = {}
        while True:
            key = input("  Env var name (or press Enter to finish): ").strip()
            if not key:
                break
            value = input(f"  {key} = ").strip()
            env[key] = value
    
    # Confirm
    print(f"\n📝 Summary:")
    print(f"   Name: {name}")
    print(f"   Command: {command}")
    print(f"   Args: {args}")
    if env:
        print(f"   Env: {list(env.keys())}")
    
    confirm = input("\nProceed? [Y/n]: ").strip().lower()
    if confirm == 'n':
        print("❌ Cancelled")
        sys.exit(0)
    
    # Execute
    injector.add_server(name, command, args, env, allow_unsafe_cli=allow_unsafe_cli)


def list_known_clients():
    """Show all known client config locations"""
    print("\n📂 Known MCP Client Locations:\n")
    for client, path in get_known_clients().items():
        expanded = Path(path).expanduser()
        exists = "✅" if expanded.exists() else "❌"
        print(f"{exists} {client.upper()}")
        print(f"   {path}")
        print()


def startup_auto_detect_prompt():
    if not sys.stdin.isatty():
        return

    detected = detect_installed_clients()
    promptable: Dict[str, Dict[str, Any]] = {}
    for name, info in detected.items():
        if info["installed"]:
            promptable[name] = info
    if not promptable:
        return

    print("\nDetected MCP-capable IDE clients:")
    ordered = sorted(promptable.items(), key=lambda kv: kv[0])
    for idx, (name, info) in enumerate(ordered, start=1):
        cfg = info["config_path"]
        if info["has_config"]:
            if info.get("has_marker"):
                state = "configured"
            else:
                state = "config file exists (app not detected)"
        else:
            state = "install detected (no MCP config yet)"
        print(f"  {idx}) {name}: {state}")
        print(f"    config: {cfg}")

    want = input("\nDo you want to inject/remove MCP servers in any of these clients now? [y/N]: ").strip().lower()
    if want != "y":
        return

    raw = input("Select target clients (e.g. 1 or 1,3) or 'all' (Enter to cancel): ").strip().lower()
    if not raw:
        return
    if raw == "all":
        targets = [name for name, _info in ordered]
    else:
        targets = []
        parts = [p.strip() for p in raw.split(",") if p.strip()]
        for p in parts:
            try:
                n = int(p)
            except Exception:
                continue
            if 1 <= n <= len(ordered):
                targets.append(ordered[n - 1][0])
    if not targets:
        print("No valid clients selected (use numbers from the list).")
        return

    print("\nWhat do you want to do?")
    print("  1) Inject detected suite servers (if available)")
    print("  2) Define a custom server and inject it")
    print("  3) Remove an existing server from client config(s)")
    action = input("\nChoice [1/2/3] (Enter to cancel): ").strip()
    if not action:
        return
    if action not in {"1", "2", "3"}:
        print("Invalid choice.")
        return

    if action == "3":
        name = input("\nServer name to remove (exact): ").strip()
        if not name:
            return
        for client in targets:
            print(f"\nTarget client: {client}")
            injector = MCPInjector(Path(str(promptable[client]["config_path"])))
            injector.remove_server(name)
        return

    if action == "2":
        for client in targets:
            print(f"\nTarget client: {client}")
            injector = MCPInjector(Path(str(promptable[client]["config_path"])))
            interactive_add(injector)
        return

    # Forge Target Injection (SC-7)
    forge_target = getattr(sys, "_nexus_forge_target", None)
    if action == "1" and forge_target:
        for client in targets:
            print(f"\nTarget client: {client}")
            injector = MCPInjector(Path(str(promptable[client]["config_path"])))
            name = forge_target.name
            cmd = f"python3 {forge_target / 'mcp_server.py'}"
            injector.add_server(name, "python3", [str(forge_target / 'mcp_server.py')])
        return

    components = detect_package_components()
    if not components:
        print("\nNo package-created components detected in ~/.mcp-tools/bin.")
        print("   Falling back to custom single-server interactive injection.")
        for client in targets:
            print(f"\nTarget client: {client}")
            injector = MCPInjector(Path(str(promptable[client]["config_path"])))
            interactive_add(injector)
        return

    print("\nDetected package-created components:")
    for comp_name, comp in components.items():
        print(f"  - {comp_name}: {comp['command']} {' '.join(comp['args'])}".strip())

    for client in targets:
        print(f"\nTarget client: {client}")
        injector = MCPInjector(Path(str(promptable[client]["config_path"])))
        for comp_name, comp in components.items():
            ask = input(f"Inject '{comp_name}' into {client}? [Y/n]: ").strip().lower()
            if ask == "n":
                continue
            try:
                injector.add_server(comp_name, comp["command"], comp["args"])
            except Exception as e:
                print(f"Warning: failed injecting {comp_name} into {client}: {e}")


def _load_mcp_servers(path: Path) -> Dict[str, Any]:
    """
    Best-effort load of a client MCP config file.
    Never prompts. Never exits the process.
    """
    try:
        if not path.exists():
            return {}
        data = json.loads(path.read_text(encoding="utf-8"))
        servers = data.get("mcpServers", {})
        return servers if isinstance(servers, dict) else {}
    except Exception:
        return {}


def list_all_clients_servers(*, allow_prompt_removal: bool = True) -> None:
    detected = detect_installed_clients()
    installed = [(name, info) for name, info in sorted(detected.items()) if info.get("installed")]
    if not installed:
        print("No MCP-capable clients detected.")
        return

    entries: List[Dict[str, Any]] = []
    idx = 1
    for client, info in installed:
        cfg_path = Path(str(info.get("config_path"))).expanduser()
        servers = _load_mcp_servers(cfg_path)
        for server_name, server_cfg in sorted(servers.items()):
            if not isinstance(server_cfg, dict):
                continue
            cmd = server_cfg.get("command", "")
            args = server_cfg.get("args", [])
            managed = bool(server_cfg.get("_shesha_managed") is True)
            entries.append(
                {
                    "idx": idx,
                    "client": client,
                    "config": str(cfg_path),
                    "name": server_name,
                    "command": cmd,
                    "args": args if isinstance(args, list) else [],
                    "managed": managed,
                }
            )
            idx += 1

    print("\nMCP servers across detected clients\n")
    last_client = None
    for item in entries:
        if item["client"] != last_client:
            last_client = item["client"]
            print(f"\n[{item['client']}]")
            print(f"config: {item['config']}")
        managed = "*" if item["managed"] else " "
        cmdline = " ".join([str(item["command"]), *[str(a) for a in item["args"]]]).strip()
        print(f"{item['idx']:>3}) {managed} {item['name']}")
        print(f"     {cmdline}")

    if not entries:
        print("(none found)")
        return

    if not (allow_prompt_removal and sys.stdin.isatty()):
        return

    confirm = input("\nRemove any entries by number? [y/N]: ").strip().lower()
    if confirm != "y":
        return

    raw = input("Enter number(s) to remove (comma-separated): ").strip()
    if not raw:
        return

    targets = set()
    for part in [p.strip() for p in raw.split(",") if p.strip()]:
        try:
            targets.add(int(part))
        except Exception:
            continue

    to_remove = [e for e in entries if e["idx"] in targets]
    if not to_remove:
        print("No valid selections.")
        return

    by_config: Dict[str, List[Dict[str, Any]]] = {}
    for e in to_remove:
        by_config.setdefault(e["config"], []).append(e)

    for config_path_str, group in by_config.items():
        config_path = Path(config_path_str).expanduser()
        injector = MCPInjector(config_path)
        for e in group:
            if not e["managed"]:
                warn = input(f"'{e['name']}' in {e['client']} is not marked _shesha_managed. Remove anyway? [y/N]: ").strip().lower()
                if warn != "y":
                    continue
            injector.remove_server(e["name"])



def main():
    parser = argparse.ArgumentParser(
        description="MCP JSON Injector - Safely modify MCP config files",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Commands (what they do):
  mcp-surgeon --startup-detect        Detect clients and guide inject/remove (TTY only)
  mcp-surgeon --list-clients          Show known client config locations
  mcp-surgeon --client claude --list  List servers in Claude config
  mcp-surgeon --client claude --add   Add a server entry to Claude (interactive)
  mcp-surgeon --client claude --remove <name>
                                     Remove one server entry by name

Examples:
  # Interactive mode (recommended)
  python mcp_injector.py --config ~/Library/Application\ Support/Claude/claude_desktop_config.json --add
  
  # Quick add using a known client name
  python mcp_injector.py --client claude --add
  
  # List all servers in a config
  python mcp_injector.py --client claude --list
  
  # Remove a server
  python mcp_injector.py --client claude --remove agent-browser
  
  # Show known client locations
  python mcp_injector.py --list-clients
        """
    )
    
    parser.add_argument("--config", type=Path, help="Path to MCP config JSON file")
    parser.add_argument("--client", choices=get_known_clients().keys(), help="Use a known client (xcode, claude, etc.)")
    parser.add_argument("--add", action="store_true", help="Add a new server (interactive)")
    parser.add_argument("--name", help="Server name (for non-interactive --add)")
    parser.add_argument("--command", help="Command to run (for non-interactive --add)")
    parser.add_argument("--args", nargs='+', help="Arguments for command (for non-interactive --add)")
    
    parser.add_argument("--remove", metavar="NAME", help="Remove a server by name")
    parser.add_argument("--list", action="store_true", help="List all configured servers")
    parser.add_argument('--list-clients', action='store_true', help="List all known client locations")
    parser.add_argument('--json', action='store_true', help="Output in raw JSON format for agent-side processing")
    parser.add_argument("--bootstrap", action="store_true", help="Bootstrap the Git-Packager workspace (fetch missing components)")
    
    parser.add_argument("--startup-detect", action="store_true", help="Auto-detect installed clients and prompt for injection")
    parser.add_argument("--forge-target", type=Path, help="Inject a specific forged server path")
    args = parser.parse_args()
    
    if args.forge_target:
        # Pass this to the startup prompt logic
        sys._nexus_forge_target = args.forge_target
        startup_auto_detect_prompt()
        return
    
    # Handle --bootstrap
    if args.bootstrap:
        try:
            # Import and run the universal bootstrapper
            bootstrap_path = Path(__file__).parent / "bootstrap.py"
            if not bootstrap_path.exists():
                print("❌ bootstrap.py not found. Please download it from:")
                print("   https://github.com/l00p3rl00p/repo-mcp-packager/blob/main/bootstrap.py")
                sys.exit(1)
            
            # Load and execute bootstrap module
            spec = importlib.util.spec_from_file_location("bootstrap", bootstrap_path)
            bootstrap = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(bootstrap)
            bootstrap.main()
            return
        except Exception as e:
            print(f"❌ Bootstrap failed: {e}")
            sys.exit(1)
    
    # Handle --list-clients
    if args.list_clients:
        list_known_clients()
        return
    
    if args.startup_detect:
        startup_auto_detect_prompt()
        return

    # Determine config path
    if args.client:
        config_path = Path(get_known_clients()[args.client]).expanduser()
    elif args.config:
        config_path = args.config
    else:
        if args.list:
            # --list without --client gives a cryptic error — provide clarity
            print("❌ --list requires a target client. Specify one of:")
            print("     --client claude|codex|cursor|vscode|xcode|aistudio|google-antigravity")
            print("\nExample:")
            print("  python3 mcp_injector.py --client claude --list")
            sys.exit(1)
        if args.add:
            if not sys.stdin.isatty():
                print("❌ Missing target client/config for --add (non-interactive).")
                print("   Provide one of:")
                print("     - --client claude|codex|cursor|vscode|xcode|aistudio")
                print("     - --config /path/to/mcp_config.json")
                print("\nExample (inject suite server into Claude):")
                print("  mcp-surgeon --client claude --add")
                sys.exit(1)
            startup_auto_detect_prompt()
            return
        startup_auto_detect_prompt()
        parser.print_help()
        sys.exit(1)
    
    injector = MCPInjector(config_path)
    
    # Execute action
    if args.add:
        if args.name and args.command:
            # Non-interactive Mode
            cmd_args = args.args or []
            injector.add_server(args.name, args.command, cmd_args)
        else:
            # Interactive Mode
            interactive_add(injector)
    elif args.remove:
        injector.remove_server(args.remove)
    elif args.list:
        injector.list_servers(json_mode=args.json)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
