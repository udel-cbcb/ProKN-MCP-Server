"""Offline tests for the ProKN MCP tools: Neo4j (_run) and HTTP (urlopen) are mocked.

They guard the read-only Cypher check, the catalysis site lookup, the Explorer link and ID
mapping, and the query log + reproducibility record.

Run:  python -m pytest tests/test_tools_offline.py -v
"""
import asyncio
import importlib.util
import json
import pathlib
import urllib.parse
from unittest.mock import patch

import pytest
from fastmcp import Client

import mcpserver


# Read-only guard on the raw Cypher tool
@pytest.mark.parametrize("query", [
    "CREATE (n:Hacked) RETURN n",             # write keyword
    "CALL apoc.load.json('http://x')",        # file/network procedure
])
def test_execute_read_only_cypher_rejects(query):
    msg = mcpserver.execute_read_only_cypher(query)
    assert isinstance(msg, str) and msg.startswith("Error")


# Catalysis site lookup: full labels and the accession_residue short form
@patch("mcpserver._run")
def test_catalyzing_sites_accepts_short_form(mock_run):
    rows = [{"site_label": "PHOSPHORYLATION_O95239_S801", "protein_symbol": "PRKAA1"}]
    mock_run.return_value = rows
    assert mcpserver.get_proteins_catalyzing_sites(["o95239 s801"]) == rows
    assert "PHOSPHORYLATION_O95239_S801" in mock_run.call_args.kwargs["params"]["site_labels"]


@patch("mcpserver._run")
def test_catalyzing_sites_not_found_explains_label_forms(mock_run):
    mock_run.return_value = []
    out = mcpserver.get_proteins_catalyzing_sites(["O95239_S9999"])
    assert "PHOSPHORYLATION_O95239_S801" in out and "search_entities" in out


# Explorer links and ID mapping
class _FakeResp:
    """Minimal stand-in for a urlopen() response used as a context manager."""
    def __init__(self, data: bytes):
        self._data = data
    def read(self):
        return self._data
    def __enter__(self):
        return self
    def __exit__(self, *a):
        return False


def _filter_from_url(url):
    """The decoded JSON filter in an Explorer link."""
    return json.loads(urllib.parse.parse_qs(urllib.parse.urlparse(url).query)["filter"][0])


# PIR's real answer when some IDs fail: bare IDs, a blank line, then a MSG: trailer
_PIR_ISOFORM_MISS = (b"P04637\tTP53\nP00533-2\nX12345\n\n"
                     b'MSG: 200 -- 2 IDs have no matches: "P00533-2,X12345".\n')


def test_get_explorer_network_link_is_self_contained():
    # no server-side network_id: the gene set travels in the link (links used to go blank)
    res = mcpserver.get_explorer_network(["EGFR", "TP53"])
    assert "network_id" not in res
    assert _filter_from_url(res["explorer_url"]) == {"gene_names": ["EGFR", "TP53"]}


@patch("mcpserver.urllib.request.urlopen")
def test_get_explorer_network_maps_ids_and_isoforms(mock_open):
    mock_open.side_effect = [_FakeResp(_PIR_ISOFORM_MISS), _FakeResp(b"P00533\tEGFR\n")]
    res = mcpserver.get_explorer_network(["P04637", "P00533-2", "X12345"], from_type="ACC")
    assert res["gene_names"] == ["TP53", "EGFR"]         # the MSG: line never becomes a gene
    assert res["unmapped"] == ["X12345"]
    assert res["isoforms_via_accession"] == {"P00533-2": "P00533"}
    assert "PIR" in res["mapping"]


@patch("mcpserver._map_ids_via_graph")
@patch("mcpserver.urllib.request.urlopen", side_effect=OSError("PIR down"))
def test_get_explorer_network_falls_back_to_graph_when_pir_down(mock_open, mock_graph):
    mock_graph.side_effect = lambda ids: (
        (["TP53"], ["P00533-2"]) if ids == ["P04637", "P00533-2"] else (["EGFR"], []))
    res = mcpserver.get_explorer_network(["P04637", "P00533-2"], from_type="ACC")
    assert res["gene_names"] == ["TP53", "EGFR"]
    assert "graph search" in res["mapping"]


def test_explorer_script_maps_ids_and_isoforms(capsys):
    path = pathlib.Path(mcpserver.__file__).parent / "skills/prokn-explorer/scripts/prokn_explorer.py"
    spec = importlib.util.spec_from_file_location("prokn_explorer_script", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    assert mod.IDMAPPING_URL == mcpserver.PROKN_IDMAPPING_URL     # script and server agree
    assert mod.ENTITY_TYPES == mcpserver.EXPLORER_ENTITY_TYPES
    with patch("urllib.request.urlopen") as mock_open:
        mock_open.side_effect = [_FakeResp(_PIR_ISOFORM_MISS), _FakeResp(b"P00533\tEGFR\n")]
        assert mod.main(["P04637", "P00533-2", "X12345", "--from", "ACC"]) == 0
    out = capsys.readouterr()
    assert _filter_from_url(out.out.strip()) == {"gene_names": ["TP53", "EGFR"]}
    assert "P00533-2 -> P00533" in out.err


# Query log and reproducibility record
def test_query_log_records_tool_calls():
    async def run():
        async with Client(mcpserver.mcp) as c:
            await c.call_tool("reset_query_log", {})
            await c.call_tool("get_queries", {"name_of_tool": "get_subgraph"})
            return (await c.call_tool("get_query_log", {})).structured_content

    out = asyncio.run(run())
    row = (out.get("result", out) if isinstance(out, dict) else out)[-1]
    assert row["tool"] == "get_queries" and row["status"] == "ok"
    assert row["duration_ms"] >= 0


def test_create_reproducibility_record_writes_file(tmp_path, monkeypatch):
    monkeypatch.setenv("PROKN_RECORD_DIR", str(tmp_path))
    mcpserver.reset_query_log()
    mcpserver._session_log().append(
        {"step": 1, "tool": "get_drugs_mechanisms", "arguments": {"drug_identifiers": ["lapatinib"]}, "time": "t"})
    conf = mcpserver.create_reproducibility_record(question="what does lapatinib inhibit?",
                                                   findings="EGFR, ERBB2",
                                                   skills="prokn-search v0.3.0")
    assert "Saved the reproducibility record" in conf
    text = next(tmp_path.glob("prokn-record-*.md")).read_text()
    assert "get_drugs_mechanisms" in text and "## Findings" in text
