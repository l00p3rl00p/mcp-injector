import os
import stat
import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import mcp_injector


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


class InjectorResilienceTests(unittest.TestCase):
    def test_malformed_global_config_is_recovered_on_sync(self):
        with tempfile.TemporaryDirectory() as temp_home:
            home = Path(temp_home)
            config_path = home / ".mcp-tools" / "config.json"
            config_path.parent.mkdir(parents=True, exist_ok=True)
            config_path.write_text("{ malformed", encoding="utf-8")

            with mock.patch("pathlib.Path.home", return_value=home):
                mcp_injector.update_global_config("claude", str(home / "claude.json"))

            data = json.loads(config_path.read_text(encoding="utf-8"))
            self.assertIn("ide_config_paths", data)
            self.assertIn("claude", data["ide_config_paths"])
            backups = list((home / ".mcp-tools").glob("config.json.corrupt.*"))
            self.assertTrue(backups)

    def test_malformed_json_is_backed_up_and_recovered(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "bad.json"
            config_path.write_text("{ bad-json", encoding="utf-8")
            result = run_cmd(INJECTOR, "--config", config_path, "--list")
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("Recovered by moving corrupt file", result.stdout)
            backups = list(Path(temp_dir).glob("bad.json.corrupt.*"))
            self.assertTrue(backups)

    def test_permission_error_surfaces_clean_message(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            locked = Path(temp_dir) / "locked"
            locked.mkdir()
            os.chmod(locked, stat.S_IREAD | stat.S_IEXEC)
            try:
                config_path = locked / "config.json"
                result = run_cmd(
                    INJECTOR,
                    "--config",
                    config_path,
                    "--add",
                    input_text="4\nperm-test\npython3\n-c,print('ok')\nn\n\n",
                )
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("Failed to write config", result.stderr + result.stdout)
            finally:
                os.chmod(locked, stat.S_IRWXU)


if __name__ == "__main__":
    unittest.main()
