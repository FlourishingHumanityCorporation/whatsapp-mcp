"""Run synchronous MCP tools on a worker thread instead of the server's event loop.

COPY of ``common_python.mcp.sync_tools`` (common-python 30b178ea), kept here
because this server's runtime venv is Python 3.11 and common-python requires
3.12 or newer, so it cannot be installed here. Change the canonical module
first and mirror it here.

FastMCP (the MCP SDK's ``mcp.server.fastmcp``) calls a plain ``def`` tool inline
inside its async request handler. On a shared streamable-HTTP server that makes
one slow sync tool a stall for every client, including a new session's
``initialize`` (304 s measured on the shared-data server on 2026-09-24).
"""

from __future__ import annotations

import asyncio
import contextvars
import functools
import inspect
from concurrent.futures import ThreadPoolExecutor
from typing import TYPE_CHECKING, Any, Protocol, cast

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable


class _ToolRegistry(Protocol):
    def add_tool(self, fn: Callable[..., Any], *args: Any, **kwargs: Any) -> None: ...


def is_async_callable(fn: Callable[..., Any]) -> bool:
    """Whether ``fn`` is a coroutine function, or an object whose call is one."""
    return inspect.iscoroutinefunction(fn) or inspect.iscoroutinefunction(fn.__call__)


def run_off_event_loop(
    fn: Callable[..., Any], executor: ThreadPoolExecutor
) -> Callable[..., Awaitable[Any]]:
    """Wrap sync ``fn`` in a coroutine function that awaits it on ``executor``."""

    @functools.wraps(fn)
    async def run_on_worker_thread(*args: Any, **kwargs: Any) -> Any:
        call = functools.partial(contextvars.copy_context().run, fn, *args, **kwargs)
        return await asyncio.get_running_loop().run_in_executor(executor, call)

    return run_on_worker_thread


class SyncToolsOffEventLoop:
    """FastMCP mixin: every sync tool registered on the server runs on a worker thread.

    List it before ``FastMCP``. ``sync_tool_workers = 1`` keeps tool calls serial,
    as they were on the loop.
    """

    sync_tool_workers: int = 1

    @functools.cached_property
    def _sync_tool_executor(self) -> ThreadPoolExecutor:
        return ThreadPoolExecutor(
            max_workers=self.sync_tool_workers, thread_name_prefix="mcp-sync-tool"
        )

    def add_tool(self, fn: Callable[..., Any], *args: Any, **kwargs: Any) -> None:
        if not is_async_callable(fn):
            fn = run_off_event_loop(fn, self._sync_tool_executor)
        cast("_ToolRegistry", super()).add_tool(fn, *args, **kwargs)
