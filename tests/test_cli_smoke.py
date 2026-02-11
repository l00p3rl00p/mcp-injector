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

    def test_startup_detect_noninteractive_cancel(self):
        result = run_cmd(INJECTOR, "--startup-detect", input_text="n\n")
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_add_remove_roundtrip_custom_config(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "mcp_config.json"
            add = run_cmd(INJECTOR, "--config", config_path, "--add", input_text="4\nsuite-test\npython3\n-c,print('ok')\nn\n\n")
            self.assertEqual(add.returncode, 0, add.stderr)

            payload = json.loads(config_path.read_text(encoding="utf-8"))
            self.assertIn("suite-test", payload.get("mcpServers", {}))

            remove = run_cmd(INJECTOR, "--config", config_path, "--remove", "suite-test")
            self.assertEqual(remove.returncode, 0, remove.stderr)
            payload_after = json.loads(config_path.read_text(encoding="utf-8"))
            self.assertNotIn("suite-test", payload_after.get("mcpServers", {}))


if __name__ == "__main__":
    unittest.main()
