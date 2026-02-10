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
from pathlib import Path
from typing import Dict, Any, Optional
import importlib.util

__version__ = "0.1.0"

# Known MCP client config locations
GLOBAL_CONFIG_KEY = "ide_config_paths"

def get_global_config_path():
    if sys.platform == "win32":
        return Path(os.environ['USERPROFILE']) / ".mcp-tools" / "config.json"
    return Path.home() / ".mcp-tools" / "config.json"

def update_global_config(ide_name: str, path: str):
    """Sync IDE config path to global Nexus config"""
    config_path = get_global_config_path()
    try:
        if config_path.exists():
            data = json.loads(config_path.read_text())
        else:
            config_path.parent.mkdir(parents=True, exist_ok=True)
            data = {}
        
        if GLOBAL_CONFIG_KEY not in data:
            data[GLOBAL_CONFIG_KEY] = {}
        
        data[GLOBAL_CONFIG_KEY][ide_name] = str(Path(path).expanduser().resolve())
        
        with open(config_path, 'w') as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        print(f"⚠️  Failed to sync global config: {e}")

KNOWN_CLIENTS = {
    "xcode": "~/Library/Developer/Xcode/UserData/MCPServers/config.json",
    "codex": "~/Library/Application Support/Codex/mcp_servers.json",
    "claude": "~/Library/Application Support/Claude/claude_desktop_config.json",
    "cursor": "~/.cursor/mcp.json",
    "vscode": "~/.vscode/mcp_settings.json",
    "aistudio": "~/.config/aistudio/mcp_servers.json",
}


class MCPInjector:
    def __init__(self, config_path: Path):
        self.config_path = config_path.expanduser()
        self.backup_path = self.config_path.with_suffix('.json.backup')
    
    def load_config(self) -> Dict[str, Any]:
        """Load existing config or create empty structure"""
        if not self.config_path.exists():
            print(f"⚠️  Config file doesn't exist. Will create: {self.config_path}")
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
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
            # SECURITY: Do not automatically overwrite corrupt config without user consent
            sys.exit(1)
        except Exception as e:
            print(f"❌ Failed to load config: {e}")
            sys.exit(1)
    
    def save_config(self, config: Dict[str, Any]):
        """
        Save config with backup and atomic write.
        
        This method implements defensive file I/O:
        1. Creates backup (with error handling)
        2. Validates JSON serialization
        3. Writes to temp file first (atomic)
        4. Renames temp to target (atomic operation)
        
        Failure modes:
        - Backup failure: Warns but continues (backup is best-effort)
        - Serialization failure: Exits (config is invalid)
        - Write failure: Exits (disk full, permissions, etc.)
        """
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
    for client, path in KNOWN_CLIENTS.items():
        expanded = Path(path).expanduser()
        exists = "✅" if expanded.exists() else "❌"
        print(f"{exists} {client.upper()}")
        print(f"   {path}")
        print()


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
    parser.add_argument("--client", choices=KNOWN_CLIENTS.keys(), help="Use a known client (xcode, claude, etc.)")
    parser.add_argument("--add", action="store_true", help="Add a new server (interactive)")
    parser.add_argument("--remove", metavar="NAME", help="Remove a server by name")
    parser.add_argument("--list", action="store_true", help="List all configured servers")
    parser.add_argument("--list-clients", action="store_true", help="Show all known client locations")
    parser.add_argument("--bootstrap", action="store_true", help="Bootstrap the Git-Packager workspace (fetch missing components)")
    
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
    
    # Determine config path
    if args.client:
        config_path = Path(KNOWN_CLIENTS[args.client]).expanduser()
    elif args.config:
        config_path = args.config
    else:
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
