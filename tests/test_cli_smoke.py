import json
import subprocess
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
INJECTOR = REPO_ROOT / "mcp_injector.py"


def run_cmd(*args, input_text=None):
    return subprocess.run(
        ["python3"] + [str(arg) for arg in args],
        cwd=REPO_ROOT,
        input=input_text,
        text=True,
        capture_output=True,
    )


class InjectorCliSmokeTests(unittest.TestCase):
    def test_help(self):
        result = run_cmd(INJECTOR, "--help")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("--startup-detect", result.stdout)

    def test_list_clients(self):
        result = run_cmd(INJECTOR, "--list-clients")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("CLAUDE", result.stdout)
        self.assertIn("CODEX", result.stdout)

    def test_add_menu_surfaces_nexus_preset_when_components_present(self):
        # Menu should always render; suite option and templates are conditional.
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "mcp_config.json"
            result = run_cmd(INJECTOR, "--config", config_path, "--add", input_text="x\n")
            out = (result.stdout or "") + (result.stderr or "")
            self.assertIn("Add MCP Server (Interactive Mode)", out)
            self.assertIn("Custom (manual entry)", out)
            # If suite components exist, option will be offered.
            if "Detected Nexus MCP stdio servers" in out or "MCP Nexus Suite (internal stdio servers)" in out:
                self.assertIn("MCP Nexus Suite (internal stdio servers)", out)
            # If npx exists, templates heading should appear.
            if "Templates (requires Node.js + npx; not auto-detected)" in out:
                self.assertIn("Agent Browser", out)

    def test_startup_detect_noninteractive_cancel(self):
        result = run_cmd(INJECTOR, "--startup-detect", input_text="n\n")
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_add_remove_roundtrip_custom_config(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "mcp_config.json"
            add = run_cmd(INJECTOR, "--config", config_path, "--add", input_text="custom\nsuite-test\npython3\n-c,print('ok')\nn\n\n")
            self.assertEqual(add.returncode, 0, add.stderr)

            payload = json.loads(config_path.read_text(encoding="utf-8"))
            self.assertIn("suite-test", payload.get("mcpServers", {}))

            remove = run_cmd(INJECTOR, "--config", config_path, "--remove", "suite-test")
            self.assertEqual(remove.returncode, 0, remove.stderr)
            payload_after = json.loads(config_path.read_text(encoding="utf-8"))
            self.assertNotIn("suite-test", payload_after.get("mcpServers", {}))

    def test_add_without_target_noninteractive_shows_helpful_error(self):
        result = run_cmd(INJECTOR, "--add", input_text="custom\n")
        self.assertNotEqual(result.returncode, 0)
        out = (result.stdout or "") + (result.stderr or "")
        self.assertIn("Missing target client/config for --add", out)
        self.assertIn("--client claude", out)


if __name__ == "__main__":
    unittest.main()
