"""Regression tests for the whatsapp-mcp STD-028 contract."""

from __future__ import annotations

import json
import re
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
            {
                "audio_analysis.go",
                "bridge.go",
                "history.go",
                "media.go",
                "messaging.go",
                "naming.go",
                "pure_helpers_test.go",
                "rest.go",
                "store.go",
            },
        )
        for source_path in (
            PROJECT_ROOT / "whatsapp-bridge" / "bridge"
        ).glob("*.go"):
            self.assertLessEqual(
                len(source_path.read_text().splitlines()),
                500,
                f"{source_path.name} exceeds the file-level ownership ratchet",
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

    def test_capability_owners_match_the_physical_go_and_python_boundaries(
        self,
    ) -> None:
        modules = {
            module["name"]: module
            for module in self.config["architecture"]["modules"]
        }

        self.assertEqual(
            modules["bridge_composition"]["paths"],
            ["whatsapp-bridge/main.go"],
        )
        self.assertEqual(
            modules["bridge_session"]["paths"],
            ["whatsapp-bridge/bridge/bridge.go"],
        )
        self.assertEqual(
            modules["bridge_history"]["paths"],
            ["whatsapp-bridge/bridge/history.go"],
        )
        self.assertEqual(
            modules["bridge_naming"]["paths"],
            ["whatsapp-bridge/bridge/naming.go"],
        )
        self.assertEqual(
            modules["bridge_store"]["paths"],
            ["whatsapp-bridge/bridge/store.go"],
        )
        self.assertEqual(
            modules["bridge_messaging"]["paths"],
            ["whatsapp-bridge/bridge/messaging.go"],
        )
        self.assertEqual(
            modules["bridge_media"]["paths"],
            ["whatsapp-bridge/bridge/media.go"],
        )
        self.assertEqual(
            modules["bridge_rest"]["paths"],
            ["whatsapp-bridge/bridge/rest.go"],
        )
        self.assertEqual(
            modules["bridge_audio_analysis"]["paths"],
            ["whatsapp-bridge/bridge/audio_analysis.go"],
        )
        self.assertEqual(
            modules["bridge_test_consumers"]["paths"],
            ["whatsapp-bridge/bridge/*_test.go"],
        )
        self.assertEqual(modules["test_consumers"]["may_depend_on"], [])

    def test_same_package_go_calls_match_the_declared_acyclic_graph(self) -> None:
        modules = {
            module["name"]: module
            for module in self.config["architecture"]["modules"]
        }
        source_owners = {
            "whatsapp-bridge/main.go": "bridge_composition",
            "whatsapp-bridge/bridge/bridge.go": "bridge_session",
            "whatsapp-bridge/bridge/history.go": "bridge_history",
            "whatsapp-bridge/bridge/naming.go": "bridge_naming",
            "whatsapp-bridge/bridge/store.go": "bridge_store",
            "whatsapp-bridge/bridge/messaging.go": "bridge_messaging",
            "whatsapp-bridge/bridge/media.go": "bridge_media",
            "whatsapp-bridge/bridge/rest.go": "bridge_rest",
            "whatsapp-bridge/bridge/audio_analysis.go": "bridge_audio_analysis",
            "whatsapp-bridge/bridge/pure_helpers_test.go": "bridge_test_consumers",
        }
        symbols_by_owner = {
            "bridge_session": {"Run"},
            "bridge_history": {"handleHistorySync"},
            "bridge_naming": {"GetChatName"},
            "bridge_store": {
                "MessageStore",
                "NewMessageStore",
                "StoreChat",
                "GetStoredChatName",
                "StoreMessage",
                "GetMediaInfo",
                "GetBasicMediaInfo",
            },
            "bridge_messaging": {
                "extractTextContent",
                "sendWhatsAppMessage",
                "extractMediaInfo",
                "handleMessage",
            },
            "bridge_media": {
                "MediaDownloader",
                "downloadMedia",
                "extractDirectPathFromURL",
            },
            "bridge_rest": {
                "SendMessageRequest",
                "SendMessageResponse",
                "DownloadMediaRequest",
                "DownloadMediaResponse",
                "startRESTServer",
            },
            "bridge_audio_analysis": {
                "analyzeOggOpus",
                "placeholderWaveform",
            },
        }
        type_symbols = {
            "MessageStore",
            "MediaDownloader",
            "SendMessageRequest",
            "SendMessageResponse",
            "DownloadMediaRequest",
            "DownloadMediaResponse",
        }

        for relative_path, source_owner in source_owners.items():
            source = (PROJECT_ROOT / relative_path).read_text()
            actual_dependencies = {
                target_owner
                for target_owner, symbols in symbols_by_owner.items()
                if target_owner != source_owner
                and any(
                    re.search(
                        (
                            rf"\b{re.escape(symbol)}\b"
                            if symbol in type_symbols
                            else r"\bbridge\.Run\s*\("
                            if symbol == "Run"
                            else rf"\b{re.escape(symbol)}\s*\("
                        ),
                        source,
                    )
                    for symbol in symbols
                )
            }
            declared_dependencies = set(
                modules[source_owner]["may_depend_on"]
            )
            self.assertLessEqual(
                actual_dependencies,
                declared_dependencies,
                f"{relative_path} has undeclared same-package dependencies",
            )

        graph = {
            owner: {
                dependency
                for dependency in modules[owner]["may_depend_on"]
                if dependency in source_owners.values()
            }
            for owner in source_owners.values()
        }
        visiting: set[str] = set()
        visited: set[str] = set()

        def visit(owner: str) -> None:
            self.assertNotIn(owner, visiting, f"dependency cycle reaches {owner}")
            if owner in visited:
                return
            visiting.add(owner)
            for dependency in graph[owner]:
                visit(dependency)
            visiting.remove(owner)
            visited.add(owner)

        for owner in graph:
            visit(owner)

    def test_sqlite_schema_knowledge_stays_inside_the_store_owner(self) -> None:
        for source_path in (
            PROJECT_ROOT / "whatsapp-bridge" / "bridge"
        ).glob("*.go"):
            if source_path.name == "store.go":
                continue
            source = source_path.read_text()
            self.assertNotIn("messageStore.db", source)
            self.assertNotRegex(
                source,
                r'(?i)"\s*(SELECT|INSERT|UPDATE|DELETE|CREATE)\b',
                f"{source_path.name} contains SQL outside bridge_store",
            )

    def test_architecture_document_describes_the_zero_debt_file_owners(
        self,
    ) -> None:
        architecture = (
            PROJECT_ROOT / "docs" / "architecture" / "ARCHITECTURE.md"
        ).read_text()

        for owner in (
            "bridge_composition",
            "bridge_session",
            "bridge_history",
            "bridge_naming",
            "bridge_store",
            "bridge_messaging",
            "bridge_media",
            "bridge_rest",
            "bridge_audio_analysis",
            "bridge_test_consumers",
        ):
            self.assertIn(f"`{owner}`", architecture)
        normalized_architecture = re.sub(r"\s+", " ", architecture)
        self.assertIn(
            "no Go capability owner exceeds 500 lines",
            normalized_architecture,
        )
        self.assertNotIn("Further decomposition of the large implementation", architecture)

    def test_appcheck_validates_the_active_checkout(self) -> None:
        commands = {
            check["name"]: check["command"]
            for check in self.config["custom_checks"]
        }

        self.assertEqual(commands["check"], "make check")


if __name__ == "__main__":
    unittest.main()
