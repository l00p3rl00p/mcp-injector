import os
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch


REPO_ROOT = Path(__file__).resolve().parents[1]
BOOTSTRAP = REPO_ROOT / "bootstrap.py"


class TestBootstrapInstallSuiteFlag(unittest.TestCase):
    def test_install_suite_flag_clones_to_central(self):
        with TemporaryDirectory() as tmp:
            # Import bootstrap as a module so we can patch subprocess.run
            import importlib.util

            spec = importlib.util.spec_from_file_location("inj_bootstrap_test", BOOTSTRAP)
            mod = importlib.util.module_from_spec(spec)
            assert spec and spec.loader
            sys.path.insert(0, str(REPO_ROOT))
            spec.loader.exec_module(mod)

            clone_targets = []

            def fake_clone(repo_name, target, devlog=None):
                clone_targets.append((repo_name, str(target)))
                return True

            with patch.dict(os.environ, {"HOME": tmp}, clear=False):
                with patch.object(mod, "_git_available", return_value=True):
                    with patch.object(mod, "_clone_repo", side_effect=fake_clone):
                        mod.sys.argv = ["bootstrap.py", "--install-suite", "--permanent"]
                        rc = mod.main()
                        self.assertIn(rc, (0, 2))

            self.assertTrue(clone_targets)
            # Central-only target path should include ~/.mcp-tools
            self.assertTrue(any("/.mcp-tools/" in t for _, t in clone_targets))


if __name__ == "__main__":
    unittest.main()
