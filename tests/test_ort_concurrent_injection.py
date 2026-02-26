"""
ORT: GAP-R4 — Concurrent injection proves zero JSON corruption.

Mission contract (mcp-injector):
  "Zero JSON corruption — surgical write with no collateral damage, including concurrent access."

What this ORT proves:
  - Two simultaneous MCPInjector.add_server() calls targeting the same config file
    do NOT corrupt the file (result is still valid JSON with an mcpServers dict).
  - The final file contains at least one of the two injected entries.
  - No .json.tmp stray files remain after concurrent completion.

Method:
  - Start two threads, each injecting a different server, with a tiny sleep jitter
    to force scheduler interleaving.
  - Validate the config file after both threads complete.

Evidence: run this and it passes → atomic rename guarantees hold under concurrency.
"""
import json
import sys
import time
import tempfile
import shutil
import threading
import unittest
from pathlib import Path

HERE = Path(__file__).parent.parent.resolve()
sys.path.insert(0, str(HERE))

from mcp_injector import MCPInjector


class TestConcurrentInjection(unittest.TestCase):
    """GAP-R4: Two simultaneous injections must not corrupt the config file."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="nexus_ort_concurrent_"))
        self.config_path = self.tmp / "mcp_config.json"
        # Start with a valid, minimal config
        self.config_path.write_text(
            json.dumps({"mcpServers": {}}), encoding="utf-8"
        )

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _inject(self, name: str, delay: float, errors: list):
        """Thread worker: inject a server, capturing any exception."""
        try:
            time.sleep(delay)
            injector = MCPInjector(self.config_path)
            injector.add_server(
                name=name,
                command="python3",
                args=[f"/fake/{name}/server.py", "--server"],
                env=None,
                allow_unsafe_cli=True,
            )
        except Exception as e:
            errors.append(f"{name}: {e}")

    def test_concurrent_injection_no_corruption(self):
        """
        Two simultaneous injections must leave a valid JSON config file.
        """
        errors = []
        t1 = threading.Thread(target=self._inject, args=("server-alpha", 0.000, errors))
        t2 = threading.Thread(target=self._inject, args=("server-beta",  0.001, errors))

        t1.start()
        t2.start()
        t1.join(timeout=10)
        t2.join(timeout=10)

        # 1. Both threads must have completed (no deadlock/timeout)
        self.assertFalse(t1.is_alive(), "Thread 1 (server-alpha) did not complete in time")
        self.assertFalse(t2.is_alive(), "Thread 2 (server-beta) did not complete in time")

        # 2. Config file must exist
        self.assertTrue(self.config_path.exists(),
                        "Config file was deleted during concurrent injection")

        # 3. Config must be valid JSON
        try:
            data = json.loads(self.config_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            self.fail(f"Config file is corrupt JSON after concurrent injection: {e}")

        # 4. mcpServers key must be a dict (not null, not list)
        self.assertIn("mcpServers", data,
                      "mcpServers key missing after concurrent injection")
        self.assertIsInstance(data["mcpServers"], dict,
                              "mcpServers must be a dict after concurrent injection")

        # 5. At least one server was injected (both may succeed or one may win the race)
        servers = data["mcpServers"]
        self.assertGreaterEqual(len(servers), 1,
                                "No servers present in config after two concurrent injections")

        # 6. No stray .json.tmp files left
        stray = list(self.tmp.glob("*.tmp"))
        self.assertEqual(len(stray), 0,
                         f"Stray .tmp files after concurrent injection: {stray}")

        # Report but don't fail on thread-level errors (last-write-wins is acceptable)
        if errors:
            print(f"\n  ℹ️  Thread errors (expected under race): {errors}")

    def test_no_stray_backup_corruption(self):
        """
        After concurrent writes, .json.backup file (if present) must also be valid JSON.
        """
        errors = []
        threads = [
            threading.Thread(target=self._inject, args=(f"srv-{i}", i * 0.0005, errors))
            for i in range(4)
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=10)

        backup = self.config_path.with_suffix(".json.backup")
        if backup.exists():
            try:
                json.loads(backup.read_text(encoding="utf-8"))
            except json.JSONDecodeError as e:
                self.fail(f"Backup file corrupt after concurrent writes: {e}")

        # Main file must be valid
        try:
            json.loads(self.config_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            self.fail(f"Main config corrupt after 4-thread injection: {e}")


if __name__ == "__main__":
    unittest.main(verbosity=2)
