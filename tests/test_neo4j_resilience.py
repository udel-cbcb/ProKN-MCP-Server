"""Offline tests: the server stays usable when Neo4j is unreachable.

The driver is replaced with a stand-in that raises the same exceptions the real Neo4j
driver raises, so no database is needed.

Run:  python -m pytest tests/test_neo4j_resilience.py -v
"""
import asyncio

import neo4j
import pytest
from fastmcp import Client
from fastmcp.exceptions import ToolError

import mcpserver


class _DownDriver:
    """Acts like a driver whose database is unreachable (or rejects the credentials)."""

    def __init__(self, exc):
        self.exc = exc
        self.verify_calls = 0

    def verify_connectivity(self):
        self.verify_calls += 1
        raise self.exc

    def session(self, **kwargs):
        raise self.exc


@pytest.fixture
def db_down(monkeypatch):
    d = _DownDriver(neo4j.exceptions.ServiceUnavailable("connection refused"))
    monkeypatch.setattr(mcpserver, "driver", d)
    monkeypatch.setattr(mcpserver.time, "sleep", lambda s: None)
    return d


def test_startup_check_returns_false_instead_of_exiting(db_down):
    assert mcpserver.verify_neo4j_connection(retries=3, delay=0) is False
    assert db_down.verify_calls == 3


def test_tool_call_reports_error_and_server_keeps_serving(db_down):
    async def check():
        async with Client(mcpserver.mcp) as c:
            res = await c.call_tool("get_graph_schema", {}, raise_on_error=False)
            tools = await c.list_tools()  # the server is still answering
            return res, tools

    res, tools = asyncio.run(check())
    assert res.is_error
    assert "isn't reachable" in res.content[0].text
    assert any(t.name == "get_graph_schema" for t in tools)
