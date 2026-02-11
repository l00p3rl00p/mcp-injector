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

__version__ = "0.1.0"

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

    candidates = {
        "nexus-activator": ("mcp-activator", []),
        "nexus-observer": ("mcp-observer", []),
        "nexus-surgeon": ("mcp-surgeon", []),
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

    def add_server(self, name: str, command: str, args: list, env: Optional[Dict[str, str]] = None):
        """Add or update an MCP server entry"""
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
        
        print(f"🗑️  Removed server '{name}'")
        self.show_summary(config)
    
    def list_servers(self):
        """List all configured MCP servers"""
        config = self.load_config()
        servers = config.get("mcpServers", {})
        
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
    
    # Common presets
    presets = {
        "1": ("agent-browser", "npx", ["-y", "@vercel/agent-browser", "mcp"]),
        "2": ("aistudio", "npx", ["-y", "aistudio-mcp-server"]),
        "3": ("notebooklm", "npx", ["-y", "notebooklm-mcp-cli"]),
        "4": ("custom", None, None),
    }
    
    print("Quick Presets:")
    print("  1. Agent Browser (Vercel)")
    print("  2. AI Studio (Google)")
    print("  3. NotebookLM")
    print("  4. Custom (manual entry)")
    
    choice = input("\nSelect preset [1-4]: ").strip()
    
    if choice not in presets:
        print("❌ Invalid choice")
        sys.exit(1)
    
    preset_name, preset_cmd, preset_args = presets[choice]
    
    if choice == "4":
        # Custom entry
        name = input("Server name: ").strip()
        command = input("Command (e.g., npx, /path/to/bin): ").strip()
        args_input = input("Args (comma-separated, e.g., -y,package-name): ").strip()
        args = [a.strip() for a in args_input.split(",")] if args_input else []
    else:
        # Preset
        name = preset_name
        command = preset_cmd
        args = preset_args
        print(f"\n📦 Using preset: {name}")
        print(f"   Command: {command} {' '.join(args)}")
    
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
    injector.add_server(name, command, args, env)


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
        if info["installed"] or name == "claude":
            promptable[name] = info
    if not promptable:
        return

    print("\n🔎 Detected MCP-capable IDE clients:")
    for name, info in promptable.items():
        cfg = info["config_path"]
        if info["has_config"]:
            state = "configured"
        elif info["installed"]:
            state = "install detected (no MCP config yet)"
        else:
            state = "not detected (common target)"
        print(f"  - {name}: {state}")
        print(f"    config: {cfg}")

    confirm = input("\nInject MCP server config into detected clients now? [y/N]: ").strip().lower()
    if confirm != "y":
        return

    selected = input("Enter client names (comma) or 'all': ").strip().lower()
    if not selected:
        return
    if selected == "all":
        targets = list(promptable.keys())
    else:
        targets = [item.strip() for item in selected.split(",") if item.strip() in promptable]
    if not targets:
        print("No valid clients selected.")
        return

    components = detect_package_components()
    if not components:
        print("\nℹ️  No package-created Nexus components detected in ~/.mcp-tools/bin.")
        print("   Falling back to custom single-server interactive injection.")
        for client in targets:
            print(f"\n🎯 Target client: {client}")
            injector = MCPInjector(Path(str(promptable[client]["config_path"])))
            interactive_add(injector)
        return

    print("\n📦 Detected package-created components:")
    for comp_name, comp in components.items():
        print(f"  - {comp_name}: {comp['command']} {' '.join(comp['args'])}".strip())

    for client in targets:
        print(f"\n🎯 Target client: {client}")
        injector = MCPInjector(Path(str(promptable[client]["config_path"])))
        for comp_name, comp in components.items():
            ask = input(f"Inject '{comp_name}' into {client}? [Y/n]: ").strip().lower()
            if ask == "n":
                continue
            try:
                injector.add_server(comp_name, comp["command"], comp["args"])
            except Exception as e:
                print(f"⚠️  Failed injecting {comp_name} into {client}: {e}")



def main():
    parser = argparse.ArgumentParser(
        description="MCP JSON Injector - Safely modify MCP config files",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
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
    parser.add_argument("--remove", metavar="NAME", help="Remove a server by name")
    parser.add_argument("--list", action="store_true", help="List all configured servers")
    parser.add_argument("--list-clients", action="store_true", help="Show all known client locations")
    parser.add_argument("--bootstrap", action="store_true", help="Bootstrap the Git-Packager workspace (fetch missing components)")
    
    parser.add_argument("--startup-detect", action="store_true", help="Auto-detect installed clients and prompt for injection")
    args = parser.parse_args()
    
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
        startup_auto_detect_prompt()
        parser.print_help()
        sys.exit(1)
    
    injector = MCPInjector(config_path)
    
    # Execute action
    if args.add:
        interactive_add(injector)
    elif args.remove:
        injector.remove_server(args.remove)
    elif args.list:
        injector.list_servers()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
