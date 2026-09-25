"""Constraint: a synchronous MCP tool never runs on the whatsapp server's event loop.

FastMCP calls a plain ``def`` tool inline inside its async request handler, so on
the shared streamable-HTTP server one slow sync tool blocks every client. Measured
2026-09-24 before the fix: a new session's ``initialize`` waited 2.17 s of a
2.47 s ``list_messages`` (the whole remaining call).

This suite runs under the Makefile's pyenv interpreter, which has no ``mcp``
package, so a stand-in for FastMCP's ``add_tool`` seam exercises the mixin; the
live server is proved by a two-session probe after deployment.
"""

from __future__ import annotations

import asyncio
import importlib.util
import inspect
import threading
import time
import unittest
from pathlib import Path
from types import ModuleType
from typing import Any, Callable

_SYNC_TOOLS = (
    Path(__file__).resolve().parents[3] / "whatsapp-mcp-server" / "support" / "sync_tools.py"
)
_BOUNDED_WAIT_SECONDS = 3.0


def _load_sync_tools() -> ModuleType:
    spec = importlib.util.spec_from_file_location("whatsapp_sync_tools", _SYNC_TOOLS)
    assert spec is not None and spec.loader is not None, _SYNC_TOOLS
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class _ToolRegistry:
    def __init__(self) -> None:
        self.tools: dict[str, Callable[..., Any]] = {}

    def add_tool(
        self, fn: Callable[..., Any], name: str | None = None, **_: Any
    ) -> None:
        self.tools[name or fn.__name__] = fn


def _server() -> Any:
    mixin = _load_sync_tools().SyncToolsOffEventLoop
    return type("_Server", (mixin, _ToolRegistry), {})()


class SyncToolsOffEventLoopTest(unittest.TestCase):
    def test_sync_tool_leaves_the_event_loop_free_while_it_runs(self) -> None:
        server = _server()
        started = threading.Event()
        released = threading.Event()
        saw_release: list[bool] = []

        def blocking_tool() -> str:
            started.set()
            # Only the event loop can set `released`; on the loop this wait times out.
            saw_release.append(released.wait(timeout=_BOUNDED_WAIT_SECONDS))
            return "done"

        async def exercise() -> str:
            call = asyncio.ensure_future(server.tools["blocking_tool"]())
            await asyncio.to_thread(started.wait, _BOUNDED_WAIT_SECONDS)
            released.set()
            return await call

        server.add_tool(blocking_tool)

        self.assertEqual(asyncio.run(exercise()), "done")
        self.assertEqual(
            saw_release, [True], "sync tool ran on the event loop and blocked it"
        )

    def test_async_tool_is_registered_unchanged(self) -> None:
        server = _server()

        async def async_tool() -> str:
            return "done"

        server.add_tool(async_tool)

        self.assertIs(server.tools["async_tool"], async_tool)

    def test_offloaded_tool_keeps_the_signature_its_schema_is_built_from(self) -> None:
        server = _server()

        def list_chats(query: str, limit: int = 20) -> list[str]:
            """List chats."""
            return [query] * limit

        server.add_tool(list_chats)
        registered = server.tools["list_chats"]

        self.assertTrue(inspect.iscoroutinefunction(registered))
        self.assertEqual(inspect.signature(registered), inspect.signature(list_chats))
        self.assertEqual(
            (registered.__name__, registered.__doc__), ("list_chats", "List chats.")
        )

    def test_default_single_worker_keeps_sync_tools_serial(self) -> None:
        server = _server()
        lock = threading.Lock()
        running = 0
        overlaps: list[int] = []

        def slow_tool() -> None:
            nonlocal running
            with lock:
                running += 1
                overlaps.append(running)
            time.sleep(0.05)
            with lock:
                running -= 1

        async def exercise() -> None:
            await asyncio.gather(*(server.tools["slow_tool"]() for _ in range(3)))

        server.add_tool(slow_tool)
        asyncio.run(exercise())

        self.assertEqual(max(overlaps), 1)


if __name__ == "__main__":
    unittest.main()
