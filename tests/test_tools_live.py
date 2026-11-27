"""Live integration tests: the real tools against a running Neo4j.

Marked live, so the default offline run skips them; if Neo4j isn't reachable the whole
module is skipped.

Run:
    export NEO4J_URI=bolt://localhost:4687   # tunnel
    export NEO4J_USERNAME=neo4j
    export NEO4J_PASSWORD=...
    python -m pytest tests/test_tools_live.py -v -m live
"""
import asyncio
import json
import pytest
from fastmcp import Client
import mcpserver
pytestmark = pytest.mark.live


@pytest.fixture(scope="module", autouse=True)
def require_neo4j():
    """Skip the whole module if Neo4j isn't reachable, rather than failing."""
    try:
        mcpserver.driver.verify_connectivity()
    except Exception as exc:
        pytest.skip(f"Neo4j not reachable at {mcpserver.NEO4J_URI}: {exc}")


def _result_data(result):
    """A tool's return value from a CallToolResult: rows as list/dict, a message as str."""
    data = getattr(result, "data", None)
    if isinstance(data, (list, dict)):
        return data
    text = "\n".join(getattr(b, "text", "") for b in (getattr(result, "content", []) or [])).strip()
    try:
        return json.loads(text)
    except (ValueError, TypeError):
        return text


def test_get_graph_schema():
    result = mcpserver.get_graph_schema()
    assert isinstance(result, list) and result and "Schema" in result[0]


def test_search_entities_egfr():
    result = mcpserver.search_entities("EGFR")
    assert isinstance(result, list) and any("EGFR" in str(r.get("name", "")) for r in result)


@pytest.mark.parametrize("site", [
    "PHOSPHORYLATION_O95239_S801",  # full label, as other tools return it
    "O95239_S801",                  # accession + residue (the form models tend to send)
])
def test_kinase_for_kif4a_s801_in_both_forms(site):
    # BYL719 downregulates KIF4A S801 (LINCS P100); PhosphoSIGNOR records PRKAA1 as its
    # kinase (PMID 28992084). The short form used to return nothing.
    result = mcpserver.get_proteins_catalyzing_sites([site])
    assert isinstance(result, list), result
    assert any(r["protein_symbol"] == "PRKAA1" and r["protein_accession"] == "Q13131"
               for r in result)


def test_write_query_rejected():
    result = mcpserver.execute_read_only_cypher("CREATE (n:Hacked) RETURN n")
    assert isinstance(result, str) and result.startswith("Error")


def test_drug_targets_to_neighbors_workflow():
    """Through the MCP client: a drug's targets, then one target's neighbours (chained)."""
    async def run():
        async with Client(mcpserver.mcp) as client:
            probe = _result_data(await client.call_tool("execute_read_only_cypher", {
                "query": "MATCH (d:Drug)-[:HAS_MECHANISM|INTERACTS_WITH]->(:Protein) "
                         "RETURN d.label AS drug LIMIT 1"}))
            if not isinstance(probe, list) or not probe:
                return None, None, None
            drug = probe[0]["drug"]
            targets = _result_data(await client.call_tool(
                "get_drugs_mechanisms", {"drug_identifiers": [drug], "ec_filter": ""}))
            target = next((r["protein_label"] for r in targets or []
                           if isinstance(r, dict) and r.get("protein_label")), None)
            if not target:
                return drug, targets, None
            neighbors = _result_data(await client.call_tool(
                "get_relationship_given_entity", {"entity": target, "limit": 5}))
            return drug, targets, neighbors

    drug, targets, neighbors = asyncio.run(run())
    if drug is None:
        pytest.skip("no drug-target data (Drug -> Protein) in this graph")
    assert isinstance(targets, list) and targets, f"{drug}: no targets"
    assert isinstance(neighbors, (list, str)), "the chained neighbour lookup did not return"
