"""Regression tests for whatsapp-mcp read paths that used to fail silently.

On 2026-08-15 the MCP tools reported an empty result for every query while the
local store held 882 chats. Two defects combined: ``list_chats`` selected message
columns without the join that supplies them, and every reader caught
``sqlite3.Error`` and returned ``[]``. A broken query and an empty account were
therefore indistinguishable, and the integration read as "you have no contacts".

These tests pin the two constraints that make that failure impossible to repeat:

1. ``list_chats`` works with and without ``include_last_message``.
2. A read that cannot be answered raises, and never returns an empty result.

The probe runs in a subprocess from a temp file so no file under ``tests/``
imports the runtime, which keeps the ``test_consumers`` architecture module at
its declared zero dependencies.
"""

from __future__ import annotations

import json
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import pytest

# Declared boundaries: the fixture store is a real (throwaway) SQLite file and the
# probe is a real subprocess. Neither touches the operator's message store, the
# bridge, or the network, so these run in the default non-live lane. The markers
# are metadata only under `make check`, which discovers via unittest.
pytestmark = [pytest.mark.sqlite, pytest.mark.filesystem]

PROJECT_ROOT = Path(__file__).resolve().parents[3]
SERVER_DIR = PROJECT_ROOT / "whatsapp-mcp-server"

# The bridge's own schema, copied from whatsapp-bridge/bridge/store.go. Reads are
# exercised against this rather than the operator's real message store, so the
# tests touch no personal data.
FIXTURE_SCHEMA = """
CREATE TABLE chats (
    jid TEXT PRIMARY KEY,
    name TEXT,
    last_message_time TIMESTAMP
);
CREATE TABLE messages (
    id TEXT,
    chat_jid TEXT,
    sender TEXT,
    content TEXT,
    timestamp TIMESTAMP,
    is_from_me BOOLEAN,
    media_type TEXT,
    filename TEXT,
    url TEXT,
    media_key BLOB,
    file_sha256 BLOB,
    file_enc_sha256 BLOB,
    file_length INTEGER,
    PRIMARY KEY (id, chat_jid),
    FOREIGN KEY (chat_jid) REFERENCES chats(jid)
);
"""

# Port 1 is reserved and never listening, so the bridge always reads as
# unreachable. That makes the "empty result cannot be trusted" path deterministic
# instead of depending on whether a real bridge happens to be running.
DEAD_BRIDGE_URL = "http://127.0.0.1:1/api"

PROBE_SOURCE = '''
import json
import os
import sys

sys.path.insert(0, os.environ["WHATSAPP_SERVER_DIR"])

import whatsapp

whatsapp.MESSAGES_DB_PATH = os.environ["WHATSAPP_DB_PATH"]
whatsapp.WHATSAPP_API_BASE_URL = os.environ["WHATSAPP_API_BASE_URL"]

outcome = {}


def record(name, call):
    """Record what a call did, so the test can assert on returned-vs-raised."""
    try:
        outcome[name] = {"raised": None, "count": len(call())}
    except whatsapp.WhatsAppError as error:
        outcome[name] = {"raised": "WhatsAppError", "detail": str(error)}
    except Exception as error:  # noqa: BLE001 - reported, never swallowed
        outcome[name] = {"raised": type(error).__name__, "detail": str(error)}


record("with_last_message", lambda: whatsapp.list_chats(include_last_message=True))
record("without_last_message", lambda: whatsapp.list_chats(include_last_message=False))
record("no_match", lambda: whatsapp.list_chats(query="nothing-matches-this"))
record("contacts", lambda: whatsapp.search_contacts("fixture"))

whatsapp.MESSAGES_DB_PATH = os.environ["WHATSAPP_MISSING_DB_PATH"]
record("missing_store", lambda: whatsapp.list_chats())

print(json.dumps(outcome))
'''


class ReadPathFailureTests(unittest.TestCase):
    """A failed read must never be returned as an empty result."""

    @classmethod
    def setUpClass(cls) -> None:
        cls._workspace = tempfile.TemporaryDirectory()
        workspace = Path(cls._workspace.name)

        database_path = workspace / "messages.db"
        connection = sqlite3.connect(database_path)
        try:
            connection.executescript(FIXTURE_SCHEMA)
            connection.execute(
                "INSERT INTO chats (jid, name, last_message_time) VALUES (?, ?, ?)",
                (
                    "15550000001@s.whatsapp.net",
                    "Fixture Contact",
                    "2026-01-01T09:00:00",
                ),
            )
            connection.execute(
                "INSERT INTO chats (jid, name, last_message_time) VALUES (?, ?, ?)",
                ("15550000002@g.us", "Fixture Group", "2026-01-02T09:00:00"),
            )
            connection.execute(
                "INSERT INTO messages (id, chat_jid, sender, content, timestamp, is_from_me)"
                " VALUES (?, ?, ?, ?, ?, ?)",
                (
                    "msg-1",
                    "15550000001@s.whatsapp.net",
                    "15550000001@s.whatsapp.net",
                    "fixture message",
                    "2026-01-01T09:00:00",
                    False,
                ),
            )
            connection.commit()
        finally:
            connection.close()

        probe_path = workspace / "probe.py"
        probe_path.write_text(PROBE_SOURCE)

        completed = subprocess.run(
            [sys.executable, str(probe_path)],
            capture_output=True,
            text=True,
            timeout=120,
            env={
                "PATH": "/usr/bin:/bin",
                "WHATSAPP_SERVER_DIR": str(SERVER_DIR),
                "WHATSAPP_DB_PATH": str(database_path),
                "WHATSAPP_MISSING_DB_PATH": str(workspace / "absent" / "messages.db"),
                "WHATSAPP_API_BASE_URL": DEAD_BRIDGE_URL,
            },
        )
        if completed.returncode != 0:
            raise AssertionError(
                f"read-path probe failed ({completed.returncode}): {completed.stderr}"
            )
        cls.outcome = json.loads(completed.stdout)

    @classmethod
    def tearDownClass(cls) -> None:
        cls._workspace.cleanup()

    def test_list_chats_works_without_the_last_message_join(self) -> None:
        """The message columns must only be selected alongside their join.

        Selecting them unconditionally raised "no such column: messages.content"
        for every include_last_message=False caller, which surfaced as [].
        """
        result = self.outcome["without_last_message"]

        self.assertIsNone(result["raised"], result)
        self.assertEqual(result["count"], 2)

    def test_list_chats_still_works_with_the_last_message_join(self) -> None:
        result = self.outcome["with_last_message"]

        self.assertIsNone(result["raised"], result)
        self.assertEqual(result["count"], 2)

    def test_search_contacts_excludes_groups_but_finds_direct_chats(self) -> None:
        result = self.outcome["contacts"]

        self.assertIsNone(result["raised"], result)
        self.assertEqual(result["count"], 1)

    def test_an_untrustworthy_empty_result_is_raised_not_returned(self) -> None:
        """Empty is only reportable when the bridge could have supplied data."""
        result = self.outcome["no_match"]

        self.assertEqual(result["raised"], "WhatsAppError", result)
        self.assertIn("bridge", result["detail"].lower())

    def test_a_missing_store_is_an_error_not_an_empty_store(self) -> None:
        """sqlite3.connect creates an empty database for a missing path.

        Without the explicit check that becomes a store with no tables, whose
        reads fail in exactly the way that used to be swallowed into [].
        """
        result = self.outcome["missing_store"]

        self.assertEqual(result["raised"], "WhatsAppError", result)
        self.assertIn("message store", result["detail"].lower())


if __name__ == "__main__":
    unittest.main()
