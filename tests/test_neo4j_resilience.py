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


def test_startup_check_reads_retries_from_env(db_down, monkeypatch):
    monkeypatch.setenv("NEO4J_STARTUP_RETRIES", "2")
    assert mcpserver.verify_neo4j_connection() is False
    assert db_down.verify_calls == 2


def test_startup_check_stops_early_on_bad_credentials(monkeypatch):
    d = _DownDriver(neo4j.exceptions.AuthError("unauthorized"))
    monkeypatch.setattr(mcpserver, "driver", d)
    assert mcpserver.verify_neo4j_connection(retries=5, delay=0) is False
    assert d.verify_calls == 1  # retrying can't fix credentials


def test_run_raises_clear_tool_error_when_db_down(db_down):
    with pytest.raises(ToolError, match="isn't reachable"):
        mcpserver._run("MATCH (n) RETURN n")


def test_run_raises_auth_message_on_bad_credentials(monkeypatch):
    monkeypatch.setattr(mcpserver, "driver", _DownDriver(neo4j.exceptions.AuthError("nope")))
    with pytest.raises(ToolError, match="rejected the credentials"):
        mcpserver._run("MATCH (n) RETURN n")


def test_introspection_reports_db_down_not_timeout(db_down):
    with pytest.raises(ToolError, match="isn't reachable"):
        mcpserver._run_introspection("CALL db.labels()", "labels")


def test_raw_cypher_tool_returns_db_down_message(db_down):
    out = mcpserver.execute_read_only_cypher("MATCH (n) RETURN n LIMIT 1")
    assert isinstance(out, str) and "isn't reachable" in out


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
