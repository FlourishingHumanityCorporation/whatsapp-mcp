"""Regression tests for the whatsapp-mcp STD-028 contract."""

from __future__ import annotations

import json
import stat
import tomllib
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]


class ArchitectureContractTests(unittest.TestCase):
    """Keep architecture enforcement checkout-local and live-data-free."""

    def setUp(self) -> None:
        self.config = tomllib.loads((PROJECT_ROOT / "appcheck.toml").read_text())

    def test_architecture_is_required_by_the_native_gate(self) -> None:
        makefile = (PROJECT_ROOT / "Makefile").read_text()

        self.assertIn("architecture", self.config["app"]["required_checks"])
        self.assertIs(self.config["architecture"]["enabled"], True)
        self.assertIs(self.config["architecture"]["required"], True)
        self.assertIn("architecture-check:", makefile)
        self.assertIn("architecture-contract-test:", makefile)
        self.assertIn(
            "$(PYTHON) -m unittest discover -s tests/architecture/unit "
            "-p 'test_*.py' -v 2>&1",
            makefile,
        )
        self.assertIn(
            "check: python-compile go-test test-policy architecture-contract-test architecture-check",
            makefile,
        )

    def test_persisted_runtime_paths_are_composition_roots_not_entry_points(
        self,
    ) -> None:
        architecture = self.config["architecture"]
        python_root = PROJECT_ROOT / "whatsapp-mcp-server" / "main.py"

        self.assertEqual(
            set(architecture["composition_roots"]),
            {"whatsapp-bridge/main.go", "whatsapp-mcp-server/main.py"},
        )
        self.assertEqual(architecture["entry_points"], [])
        self.assertFalse(python_root.stat().st_mode & stat.S_IXUSR)

    def test_runtime_source_roots_remain_small_and_explicit(self) -> None:
        self.assertEqual(self.config["architecture"]["max_root_files"], 8)
        self.assertEqual(
            {
                path.name
                for path in (PROJECT_ROOT / "whatsapp-mcp-server").glob("*.py")
            },
            {"audio.py", "main.py", "tools.py", "whatsapp.py"},
        )
        self.assertEqual(
            {
                path.name
                for path in (PROJECT_ROOT / "whatsapp-bridge").glob("*.go")
            },
            {"main.go"},
        )
        self.assertEqual(
            {
                path.name
                for path in (PROJECT_ROOT / "whatsapp-bridge" / "bridge").glob("*.go")
            },
            {"bridge.go"},
        )
        self.assertLessEqual(
            len((PROJECT_ROOT / "whatsapp-bridge" / "main.go").read_text().splitlines()),
            200,
        )
        self.assertLessEqual(
            len((PROJECT_ROOT / "whatsapp-mcp-server" / "main.py").read_text().splitlines()),
            200,
        )
        baseline = json.loads(
            (PROJECT_ROOT / ".appcheck" / "architecture-baseline.json").read_text()
        )
        self.assertEqual(baseline["violations"], {})

    def test_appcheck_validates_the_active_checkout(self) -> None:
        commands = {
            check["name"]: check["command"]
            for check in self.config["custom_checks"]
        }

        self.assertEqual(commands["check"], "make check")


if __name__ == "__main__":
    unittest.main()
