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

__version__ = "3.3.2"

# Best-practice guardrails: these Nexus binaries are CLIs, not MCP servers over stdio.
# Injecting them into MCP clients (Claude/Codex/etc.) will cause JSON parse errors.
KNOWN_NONSERVER_BINARIES = {
    "mcp-activator",
    "mcp-observer",
    "mcp-surgeon",
}

# If a server entry points at a local file that doesn't exist, clients will fail with
# "can't open file ... [Errno 2]". Provide a frictionless cleanup path.
def _server_entrypoints_missing(server_cfg: Dict[str, Any]) -> Optional[str]:
    try:
        cmd = str(server_cfg.get("command") or "").strip()
        args = server_cfg.get("args") or []
        if not cmd or not isinstance(args, list) or not args:
            return None
        first = str(args[0])
        if first.endswith(".py"):
            path = Path(first).expanduser()
            if not path.is_absolute():
                # Most clients execute with an arbitrary CWD; relative paths are unreliable.
                return first
            if not path.exists():
                return str(path)
        return None
    except Exception:
        return None

# Known MCP client config locations
GLOBAL_CONFIG_KEY = "ide_config_paths"

# Allow user overrides for IDE config paths (stored in ~/.mcp-tools/config.json).
def _load_global_ide_config_paths() -> Dict[str, str]:
    config_path = get_global_config_path()
    try:
        if not config_path.exists():
            return {}
        data = json.loads(config_path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            return {}
        raw = data.get(GLOBAL_CONFIG_KEY, {})
        if not isinstance(raw, dict):
            return {}
        out: Dict[str, str] = {}
        for k, v in raw.items():
            if isinstance(k, str) and isinstance(v, str) and v.strip():
                out[k] = v
        return out
    except Exception:
        return {}

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
                "~/.gemini/antigravity/mcp_server.json",
                "~/.gemini/antigravity/mcp_config.json",
                "~/.gemini/antigravity/mcp/mcp_config.json"
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
    overrides = _load_global_ide_config_paths()
    specs = _client_specs()
    for name, spec in specs.items():
        override = overrides.get(name)
        if override:
            mapping[name] = str(_expand_path(override))
            continue
        for candidate in spec["configs"]:
            path = _expand_path(candidate)
            if path.exists():
                mapping[name] = str(path)
                break
        if name not in mapping:
            mapping[name] = str(_expand_path(spec["configs"][0]))
    return mapping


KNOWN_CLIENTS = get_known_clients()

REPAIR_RECIPES_FILENAME = "repair_recipes.json"


def _load_repair_recipes() -> Dict[str, Dict[str, Any]]:
    """
    Load repair recipes from a local registry file.

    Why:
      - Keeps "what to run" out of hard-coded logic.
      - Enables pick-from-a-list UX for humans.
      - Allows orgs/users to maintain their own recipes without code edits.
    """
    # 1) Prefer a co-located file next to this script (repo install).
    local_path = Path(__file__).parent / REPAIR_RECIPES_FILENAME
    # 2) Optionally allow a central override living under ~/.mcp-tools (installed suite).
    #    We do not create this file automatically; it's an opt-in power-user hook.
    central_override = get_nexus_home() / "mcp-injector" / REPAIR_RECIPES_FILENAME

    for path in (local_path, central_override):
        try:
            if not path.exists():
                continue
            data = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(data, dict):
                continue
            recipes = data.get("recipes")
            if recipes is None:
                recipes = data
            if not isinstance(recipes, dict):
                continue
            out: Dict[str, Dict[str, Any]] = {}
            for key, value in recipes.items():
                if not (isinstance(key, str) and isinstance(value, dict)):
                    continue
                cmd = value.get("command")
                args = value.get("args")
                label = value.get("label")
                added = value.get("added")
                if not isinstance(cmd, str) or not cmd.strip():
                    continue
                if args is None:
                    args = []
                if not isinstance(args, list) or any(not isinstance(a, str) for a in args):
                    continue
                out[key.strip()] = {
                    "command": cmd.strip(),
                    "args": [a for a in args],
                    "label": label.strip() if isinstance(label, str) else key.strip(),
                    "added": added.strip() if isinstance(added, str) else None,
                    "source": str(path),
                }
            if out:
                return out
        except Exception:
            continue
    return {}


def _load_templates() -> Dict[str, Dict[str, Any]]:
    """
    Load npx/server templates from the same registry file as repair recipes.
    """
    local_path = Path(__file__).parent / REPAIR_RECIPES_FILENAME
    central_override = get_nexus_home() / "mcp-injector" / REPAIR_RECIPES_FILENAME
    for path in (local_path, central_override):
        try:
            if not path.exists():
                continue
            data = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(data, dict):
                continue
            templates = data.get("templates", {})
            if not isinstance(templates, dict):
                continue
            out: Dict[str, Dict[str, Any]] = {}
            for key, value in templates.items():
                if not (isinstance(key, str) and isinstance(value, dict)):
                    continue
                cmd = value.get("command")
                args = value.get("args")
                label = value.get("label")
                added = value.get("added")
                if not isinstance(cmd, str) or not cmd.strip():
                    continue
                if args is None:
                    args = []
                if not isinstance(args, list) or any(not isinstance(a, str) for a in args):
                    continue
                out[key.strip()] = {
                    "command": cmd.strip(),
                    "args": [a for a in args],
                    "label": label.strip() if isinstance(label, str) else key.strip(),
                    "added": added.strip() if isinstance(added, str) else None,
                    "source": str(path),
                }
            return out
        except Exception:
            continue
    return {}


def list_repair_recipes(*, json_mode: bool = False) -> None:
    recipes = _load_repair_recipes()
    if json_mode:
        print(json.dumps({"recipes": recipes}, indent=2))
        return
    if not recipes:
        print("No repair recipes found.")
        print("Expected one of:")
        print(f"  - {Path(__file__).parent / REPAIR_RECIPES_FILENAME}")
        print(f"  - {get_nexus_home() / 'mcp-injector' / REPAIR_RECIPES_FILENAME}")
        return
    print("\nRepair recipes\n")
    keys = sorted(
        recipes.keys(),
        key=lambda k: (recipes[k].get("added") or "9999-99-99", recipes[k].get("label") or k, k),
    )
    for k in keys:
        r = recipes[k]
        label = r.get("label") or k
        added = r.get("added") or "unknown"
        cmdline = " ".join([str(r.get("command") or ""), *[str(a) for a in (r.get("args") or [])]]).strip()
        print(f"- {label} ({k}) [{added}]")
        print(f"  {cmdline}")


def _pick_repair_recipe(recipes: Dict[str, Dict[str, Any]], *, preferred_key: Optional[str] = None) -> Optional[Dict[str, Any]]:
    if not recipes:
        return None

    keys = sorted(
        recipes.keys(),
        key=lambda k: (recipes[k].get("added") or "9999-99-99", recipes[k].get("label") or k, k),
    )
    if preferred_key and preferred_key in recipes:
        # Still allow selection when TTY is available; do not auto-select silently.
        keys = [preferred_key] + [k for k in keys if k != preferred_key]

    if not sys.stdin.isatty():
        return None

    page_size = 8
    page = 0
    while True:
        start = page * page_size
        end = min(start + page_size, len(keys))
        if start >= len(keys):
            page = 0
            continue

        print("\nRepair recipes (pick one)\n")
        for i, k in enumerate(keys[start:end], start=1):
            r = recipes[k]
            label = r.get("label") or k
            added = r.get("added") or "unknown"
            cmdline = " ".join([str(r.get("command") or ""), *[str(a) for a in (r.get("args") or [])]]).strip()
            print(f"{i:>2}) {label} [{added}]")
            print(f"    id:  {k}")
            print(f"    run: {cmdline}")

        more = end < len(keys)
        nav = []
        if page > 0:
            nav.append("b=back")
        if more:
            nav.append("n=next")
        nav.append("x=exit")
        nav_hint = " / ".join(nav)
        print(f"\nEnter a number to select ({start+1}-{end} of {len(keys)}), or {nav_hint}.")
        raw = input("Choice: ").strip().lower()
        if not raw or raw == "x":
            return None
        if raw == "n" and more:
            page += 1
            continue
        if raw == "b" and page > 0:
            page -= 1
            continue
        try:
            idx = int(raw)
        except Exception:
            continue
        if idx < 1 or idx > (end - start):
            continue
        return recipes[keys[start + idx - 1]]


def detect_installed_clients() -> Dict[str, Dict[str, Any]]:
    detected: Dict[str, Dict[str, Any]] = {}
    overrides = _load_global_ide_config_paths()
    for client, spec in _client_specs().items():
        override = overrides.get(client)
        config_candidates = ([_expand_path(override)] if override else []) + [_expand_path(path) for path in spec["configs"]]
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

    Returns all verified stdio MCP servers in the Nexus suite:
      - nexus-librarian    → ~/.mcp-tools/bin/mcp-librarian --server
      - atp-engine         → python3 <AgentFixes>/agent/atp/mcp_server.py
      - webmcp-knowledge-server → python3 <webmcp>/mcpbuild/webmcp_server/mcp_server.py

    Only include binaries/scripts that speak MCP JSON-RPC over stdio.
    CLIs (mcp-activator, mcp-observer, mcp-surgeon) must NOT be injected.
    """
    home = get_nexus_home().parent  # ~/.mcp-tools/.. == $HOME

    nexus_home = get_nexus_home()
    bin_dir = nexus_home / "bin"

    components: Dict[str, Dict[str, Any]] = {}

    # 1. nexus-librarian — binary in ~/.mcp-tools/bin/
    mcp_librarian = bin_dir / "mcp-librarian"
    if mcp_librarian.exists():
        components["nexus-librarian"] = {
            "command": str(mcp_librarian),
            "args": ["--server"],
            "source": "nexus-bin"
        }

    # 2. atp-engine — Python script in ~/Developer/AgentFixes/agent/atp/
    atp_candidates = [
        home / "Developer" / "AgentFixes" / "agent" / "atp" / "mcp_server.py",
    ]
    for atp_path in atp_candidates:
        if atp_path.exists():
            components["atp-engine"] = {
                "command": "python3",
                "args": [str(atp_path)],
                "source": "agentfixes-local"
            }
            break

    # 3. webmcp-knowledge-server — Python script in ~/Developer/Github/webmcp/
    webmcp_candidates = [
        home / "Developer" / "Github" / "webmcp" / "mcpbuild" / "webmcp_server" / "mcp_server.py",
    ]
    for webmcp_path in webmcp_candidates:
        if webmcp_path.exists():
            components["webmcp-knowledge-server"] = {
                "command": "python3",
                "args": [str(webmcp_path)],
                "source": "webmcp-local"
            }
            break

    return components


def _load_inventory_servers() -> Dict[str, Dict[str, Any]]:
    """
    Load forged/registered servers from the local Nexus inventory (if present) and
    return them in the same injectable shape as detect_package_components().
    """
    inv_path = get_nexus_home() / "mcp-server-manager" / "inventory.yaml"
    if not inv_path.exists():
        return {}

    try:
        import yaml  # type: ignore
    except Exception:
        return {}

    try:
        data = yaml.safe_load(inv_path.read_text(encoding="utf-8")) or {}
        servers = data.get("servers", []) or []
        if not isinstance(servers, list):
            return {}
    except Exception:
        return {}

    out: Dict[str, Dict[str, Any]] = {}
    for s in servers:
        try:
            s_id = str(s.get("id") or s.get("name") or "").strip()
            run = s.get("run") or {}
            start_cmd = str(run.get("start_cmd") or "").strip()
            if not s_id or not start_cmd:
                continue

            argv = shlex.split(start_cmd)
            if not argv:
                continue

            # Guardrails: only include obvious stdio MCP servers (python entrypoints).
            is_python = Path(argv[0]).name in ("python", "python3") or Path(argv[0]).name.startswith("python")
            looks_stdio = ("mcp_server.py" in argv) or ("--server" in argv) or ("-m" in argv)
            if not (is_python and looks_stdio):
                continue

            out[s_id] = {
                "command": argv[0],
                "args": argv[1:],
                "source": f"inventory:{inv_path}"
            }
        except Exception:
            continue

    return out


class MCPInjector:
    def __init__(self, config_path: Path):
        self.config_path = config_path.expanduser()
        self.backup_path = self.config_path.with_suffix('.json.backup')

    @staticmethod
    def _sanitize_loaded_config(config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Remove deprecated/legacy keys that should not persist across rewrites.
        This is intentionally narrow to avoid deleting user data.
        """
        servers = config.get("mcpServers")
        if not isinstance(servers, dict):
            return config
        for _name, cfg in servers.items():
            if not isinstance(cfg, dict):
                continue
            # Legacy dev artifact (must not persist).
            cfg.pop("_shesha_managed", None)
        return config
    
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

            return self._sanitize_loaded_config(config)
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
        
        # NOTE: Do NOT add _nexus_managed or any extra keys to the server entry.
        # Claude Desktop and most MCP clients only support: command, args, env.
        # Extra keys are either silently ignored or cause JSON parse errors in some clients.
        # Tracking is done at the injector level, not inside client config files.
        
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
            managed = "🔧 " if isinstance(cfg, dict) and cfg.get("_nexus_managed") else "   "
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
    
    suite_components = detect_package_components()
    inventory_components = _load_inventory_servers()
    has_npx = bool(shutil.which("npx"))
    templates = _load_templates() if has_npx else {}

    # Menu options are intentionally "truthy":
    # - Suite servers are detected from the local install (recommended).
    # - npx items are templates (not detected) and only shown if npx exists.
    menu: Dict[str, tuple] = {}
    idx = 1
    if suite_components:
        menu[str(idx)] = ("nexus-detected", None, None)
        idx += 1
    if inventory_components:
        menu[str(idx)] = ("inventory-detected", None, None)
        idx += 1
    template_keys: List[str] = []
    if templates:
        template_keys = sorted(
            templates.keys(),
            key=lambda k: (templates[k].get("added") or "9999-99-99", templates[k].get("label") or k, k),
        )
        for k in template_keys:
            t = templates[k]
            menu[str(idx)] = (k, str(t.get("command") or ""), list(t.get("args") or []))
            idx += 1
    menu[str(idx)] = ("custom", None, None)
    
    print("Choices:")
    current = 1
    if suite_components:
        print(f"  {current}. MCP Nexus Suite (internal stdio servers)")
        current += 1
    if inventory_components:
        print(f"  {current}. Nexus Inventory (forged/registered servers)")
        current += 1
    if template_keys:
        base = current
        print("\nTemplates (requires Node.js + npx; not auto-detected):")
        for off, k in enumerate(template_keys):
            label = templates[k].get("label") or k
            print(f"  {base + off}. {label}")
        idx_custom = base + len(template_keys)
    else:
        idx_custom = current
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
    if choice in {"i", "inv", "inventory"}:
        for k, (name, _cmd, _args) in menu.items():
            if name == "inventory-detected":
                choice = k
                break
    
    if choice not in menu:
        print("❌ Invalid choice")
        sys.exit(1)
    
    preset_name, preset_cmd, preset_args = menu[choice]
    
    if preset_name == "nexus-detected":
        # Suite-detected MCP stdio servers (stdio JSON-RPC on stdout)
        ordered = sorted(suite_components.items(), key=lambda kv: kv[0])
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

    elif preset_name == "inventory-detected":
        ordered = sorted(inventory_components.items(), key=lambda kv: kv[0])
        print("\n🗃️  Detected Nexus inventory servers (forged/registered):")
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
        print(f"\n🗃️  Using inventory server: {name}")
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
        for client in targets:
            print(f"\nTarget client: {client}")
            config_path = Path(str(promptable[client]["config_path"]))
            injector = MCPInjector(config_path)
            servers = _load_mcp_servers(config_path.expanduser())
            names = sorted([str(k) for k in servers.keys() if isinstance(k, str)])

            if not names:
                print("  (no servers found)")
                continue

            print("  Servers:")
            for idx, n in enumerate(names, start=1):
                print(f"   {idx:>2}) {n}")

            raw = input("\nRemove which? (number, comma-list, or exact name; Enter to skip): ").strip()
            if not raw:
                continue

            to_remove: List[str] = []
            if raw.lower() == "all":
                to_remove = names
            else:
                parts = [p.strip() for p in raw.split(",") if p.strip()]
                for part in parts:
                    if part.isdigit():
                        i = int(part)
                        if 1 <= i <= len(names):
                            to_remove.append(names[i - 1])
                        continue
                    # treat as exact name
                    if part in servers:
                        to_remove.append(part)

            # de-dupe, preserve order
            seen = set()
            deduped: List[str] = []
            for n in to_remove:
                if n in seen:
                    continue
                seen.add(n)
                deduped.append(n)

            if not deduped:
                print("  No valid selection.")
                continue

            for name in deduped:
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
            managed = bool(server_cfg.get("_nexus_managed"))
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
                warn = input(f"'{e['name']}' in {e['client']} is not marked _nexus_managed. Remove anyway? [y/N]: ").strip().lower()
                if warn != "y":
                    continue
            injector.remove_server(e["name"])

def remove_missing_entrypoints(*, client: str) -> None:
    """
    Remove entries that point at missing local entrypoints (TTY only).
    This is a deterministic "repair" for stale configs without manual JSON edits.
    """
    if not sys.stdin.isatty():
        print("❌ --remove-missing requires an interactive terminal (TTY).")
        sys.exit(1)

    config_path = Path(get_known_clients()[client]).expanduser()
    injector = MCPInjector(config_path)
    config = injector.load_config()
    servers = config.get("mcpServers", {})
    if not isinstance(servers, dict) or not servers:
        print("📭 No MCP servers configured")
        return

    missing: List[Dict[str, Any]] = []
    for name, cfg in servers.items():
        if not isinstance(cfg, dict):
            continue
        miss = _server_entrypoints_missing(cfg)
        if miss:
            missing.append(
                {
                    "name": name,
                    "missing": miss,
                    "command": cfg.get("command", ""),
                    "args": cfg.get("args", []),
                    "managed": bool(cfg.get("_nexus_managed")),
                }
            )

    if not missing:
        print("✅ No entries with missing local entrypoints.")
        return

    print("\nEntries with missing entrypoints\n")
    for idx, item in enumerate(missing, start=1):
        managed = "*" if item["managed"] else " "
        cmdline = " ".join([str(item["command"]), *[str(a) for a in (item["args"] or [])]]).strip()
        print(f"{idx:>2}) {managed} {item['name']}")
        print(f"    missing: {item['missing']}")
        print(f"    run:     {cmdline}")

    raw = input("\nRemove which entries? (numbers comma-separated, Enter to cancel): ").strip()
    if not raw:
        print("❌ Cancelled")
        return

    picks: set[int] = set()
    for part in [p.strip() for p in raw.split(",") if p.strip()]:
        try:
            picks.add(int(part))
        except Exception:
            continue

    targets = [missing[i - 1] for i in sorted(picks) if 1 <= i <= len(missing)]
    if not targets:
        print("No valid selections.")
        return

    for t in targets:
        if not t["managed"]:
            warn = input(f"'{t['name']}' is not marked _nexus_managed. Remove anyway? [y/N]: ").strip().lower()
            if warn != "y":
                continue
        injector.remove_server(t["name"])



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
  mcp-surgeon --client claude --repair <name>
                                     Repair/overwrite an existing entry in one step

Examples:
  # Interactive mode (recommended)
  python mcp_injector.py --config "~/Library/Application Support/Claude/claude_desktop_config.json" --add
  
  # Quick add using a known client name
  python mcp_injector.py --client claude --add
  
  # Non-interactive add with args that start with '-' (recommended form)
  python mcp_injector.py --client claude --add --name notebooklm-npx --command npx --args -y github:jacob-bd/notebooklm-mcp-cli
  
  # List all servers in a config
  python mcp_injector.py --client claude --list
  
  # Remove a server
  python mcp_injector.py --client claude --remove agent-browser

  # Repair a template entry in one step (pick from a list; no remove+add)
  python mcp_injector.py --list-recipes
  python mcp_injector.py --client claude --repair notebooklm-npx
  python mcp_injector.py --client claude --repair notebooklm-npx --recipe notebooklm-npx-github
  
  # Show known client locations
  python mcp_injector.py --list-clients
        """
    )
    
    parser.add_argument("--config", type=Path, help="Path to MCP config JSON file")
    parser.add_argument("--client", choices=get_known_clients().keys(), help="Use a known client (xcode, claude, etc.)")
    parser.add_argument("--add", action="store_true", help="Add a new server (interactive)")
    parser.add_argument("--name", help="Server name (for non-interactive --add)")
    parser.add_argument("--command", help="Command to run (for non-interactive --add)")
    # Important: accept args that start with '-' (e.g. `npx -y ...`).
    # Using REMAINDER prevents argparse from treating '-y' as a top-level flag.
    parser.add_argument("--args", nargs=argparse.REMAINDER, help="Arguments for command (for non-interactive --add)")
    
    parser.add_argument("--remove", metavar="NAME", help="Remove a server by name")
    parser.add_argument("--repair", metavar="NAME", help="Repair (overwrite) a server by name in one step")
    parser.add_argument(
        "--recipe",
        metavar="RECIPE_ID",
        help="Repair recipe id (avoids hard-coded defaults). Use --repair with TTY for pick-list.",
    )
    parser.add_argument("--list-recipes", action="store_true", help="List available repair recipes")
    parser.add_argument(
        "--remove-missing",
        action="store_true",
        help="Interactive cleanup: remove entries that point at missing local entrypoints",
    )
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

    if args.list_recipes:
        list_repair_recipes(json_mode=args.json)
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
            # If a user included an explicit "--" separator, treat it as "end of options" and drop it.
            if cmd_args and cmd_args[0] == "--":
                cmd_args = cmd_args[1:]
            injector.add_server(args.name, args.command, cmd_args)
        else:
            # Interactive Mode
            interactive_add(injector)
    elif args.repair:
        name = args.repair
        if args.command:
            cmd = args.command
            cmd_args = args.args or []
            if cmd_args and cmd_args[0] == "--":
                cmd_args = cmd_args[1:]
            injector.add_server(name, cmd, cmd_args)
            return

        recipes = _load_repair_recipes()
        if args.recipe:
            recipe = recipes.get(args.recipe)
            if not recipe:
                print(f"❌ Unknown recipe id: {args.recipe}")
                print("   Tip: run with a TTY and omit --recipe to pick from a list.")
                sys.exit(1)
        else:
            recipe = _pick_repair_recipe(recipes, preferred_key=name)

        if not recipe:
            print("❌ No recipe selected.")
            if not recipes:
                print(f"   No recipes registry found. Expected one of:")
                print(f"     - {Path(__file__).parent / REPAIR_RECIPES_FILENAME}")
                print(f"     - {get_nexus_home() / 'mcp-injector' / REPAIR_RECIPES_FILENAME}")
            print("   Provide explicit desired command/args, e.g.:")
            print(f"  mcp-surgeon --client {args.client or '<client>'} --repair {name} --command <cmd> --args <args...>")
            sys.exit(1)

        injector.add_server(name, str(recipe.get("command")), list(recipe.get("args") or []))
    elif args.remove:
        injector.remove_server(args.remove)
    elif args.remove_missing:
        if not args.client:
            print("❌ --remove-missing requires --client <name> (e.g. --client claude)")
            sys.exit(1)
        remove_missing_entrypoints(client=args.client)
    elif args.list:
        injector.list_servers(json_mode=args.json)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
