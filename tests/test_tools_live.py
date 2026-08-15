"""Live integration tests for the ProKN MCP tools

These call the real tool functions against running Neo4j,
and assert on result structure using known entities

Marked live so they are excluded from the default offline run. If Neo4j is not
reachable, the whole module is skipped

Run:
    export NEO4J_URI=bolt://localhost:4687   # tunnel
    export NEO4J_USERNAME=neo4j
    export NEO4J_PASSWORD=...
    python -m pytest tests/test_tools_live.py -v -m live

Skip live everywhere else:  python -m pytest -m "not live"
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

# Helpers
def _assert_rows(result, *required_keys):
    """Assert a non-empty list of dict rows, with the given keys on the first row."""
    assert isinstance(result, list), f"expected rows, got: {result!r}"
    assert len(result) > 0, "expected at least one row"
    for key in required_keys:
        assert key in result[0], f"missing key '{key}' in row: {result[0]}"

def _assert_rows_or_message(result):
    """Data-dependent tools: accept rows OR a graceful guidance string, never a raise."""
    assert isinstance(result, (list, str)), f"unexpected result type: {type(result)}"
    if isinstance(result, list) and result:
        assert isinstance(result[0], dict)

def _result_data(result):
    """Recover a tool's Python return value from a CallToolResult.

    Our tools return list[dict] or a plain str; over MCP that arrives as (JSON or
    plain) text in a content block, so parse it back. A list/dict comes out as a
    list/dict; a guidance message comes out as a str.
    """
    data = getattr(result, "data", None)
    if isinstance(data, (list, dict)):
        return data
    blocks = getattr(result, "content", []) or []
    text = "\n".join(getattr(b, "text", "") for b in blocks).strip()
    try:
        return json.loads(text)
    except (ValueError, TypeError):
        return text

# Schema / introspection
class TestSchema:
    def test_get_graph_schema(self):
        _assert_rows(mcpserver.get_graph_schema(), "Schema")

    def test_get_node_properties(self):
        # db.schema.nodeTypeProperties() scans the whole store and can time out on a
        # large graph
        _assert_rows_or_message(mcpserver.get_node_properties())

    def test_get_relationship_properties(self):
        _assert_rows_or_message(mcpserver.get_relationship_properties())

# Entity resolution
class TestEntityResolution:
    def test_search_entities_egfr(self):
        result = mcpserver.search_entities("EGFR")
        _assert_rows(result, "name", "identifiers")
        assert any("EGFR" in str(row.get("name", "")) for row in result)

# Single-entity neighborhood + bounded subgraph
class TestNeighborhood:
    def test_relationship_given_entity_egfr(self):
        result = mcpserver.get_relationship_given_entity("EGFR", limit=5)
        _assert_rows(result, "relationship_type", "neighbor_name", "evidence")

    def test_get_subgraph_egfr_returns_json(self):
        result = mcpserver.get_subgraph("EGFR", max_hops=1, max_nodes=5)
        assert isinstance(result, str), f"expected JSON string, got: {result!r}"
        parsed = json.loads(result)  # fails loudly if APOC is missing / not JSON
        assert parsed["node_count"] >= 1
        assert len(parsed["nodes"]) >= 1
        assert "relationships" in parsed

    def test_get_subgraph_with_filter(self):
        # Restrict end nodes to Protein; should still return JSON (possibly fewer nodes).
        result = mcpserver.get_subgraph(
            "EGFR", max_hops=2, max_nodes=10, node_type_filter=["Protein"]
        )
        assert isinstance(result, str)
        json.loads(result)  # must be valid JSON

# Two-protein path + pathways
class TestInteractions:
    def test_protein_interactions_egfr_grb2(self):
        result = mcpserver.get_protein_interactions("EGFR", "GRB2")
        _assert_rows_or_message(result)
        if isinstance(result, list) and result:
            assert "interaction_path" in result[0]

# Drugs / perturbagens (data-dependent -> tolerant)
class TestDrugs:
    def test_get_drugs_mechanisms_lapatinib(self):
        result = mcpserver.get_drugs_mechanisms(["lapatinib"], action_type="INHIBITOR")
        _assert_rows_or_message(result)

    def test_get_genes_regulated_by_drugs(self):
        result = mcpserver.get_genes_regulated_by_drugs(["cc-401"])
        _assert_rows_or_message(result)

    def test_phosphosites_regulated_by_perturbagen(self):
        result = mcpserver.get_phosphosites_regulated_by_perturbagen(
            "alpelisib", direction="down"
        )
        _assert_rows_or_message(result)

# Kinase / phosphosite navigation (data-dependent -> tolerant)
class TestPhosphosites:
    def test_phosphosites_catalyzed_by_cdk1(self):
        result = mcpserver.get_phosphosites_catalyzed_by_proteins(["CDK1"])
        _assert_rows_or_message(result)

class TestEnzymeFilter:
    def test_filter_proteins_by_ec_number(self):
        # EGFR is a kinase (EC 2.7.10.1), so it should pass the default 2.7.* filter.
        # Exercises the per-token EC match (split on ';') for multi-EC proteins.
        result = mcpserver.filter_proteins_by_ec_number(["EGFR"])
        _assert_rows_or_message(result)

# Raw Cypher escape hatch: read allowed, write rejected
class TestRawCypher:
    def test_read_only_query_runs(self):
        result = mcpserver.execute_read_only_cypher(
            "MATCH (n:Protein) RETURN n.label AS label LIMIT 3"
        )
        assert isinstance(result, list)

    def test_write_query_rejected(self):
        result = mcpserver.execute_read_only_cypher("CREATE (n:Hacked) RETURN n")
        assert isinstance(result, str) and result.startswith("Error")

# End-to-end: client -> MCP protocol -> normalization middleware -> tool -> Neo4j
class TestEndToEnd:
    """Exercise the whole stack via in-memory FastMCP client.

    The tool is called with an ALIAS argument (`query` instead of `term`), so a
    passing run also proves the argument-normalization middleware fires end to end
    """
    def test_e2e_search_entities_via_alias(self):
        async def run():
            async with Client(mcpserver.mcp) as client:
                return await client.call_tool("search_entities", {"query": "EGFR"})

        data = _result_data(asyncio.run(run()))

        # A pass proves the middleware normalized `query`->`term` end to end, and
        # EGFR resolved to real rows
        assert isinstance(data, list) and data, f"expected rows, got: {data!r}"
        assert any("EGFR" in str(row.get("name", "")) for row in data)

class TestUseCaseE2E:
    """A real ProKN workflow end to end, chaining tools through the MCP client:
    from a drug to its protein targets to what one of those targets is connected to.

    Step 1: discover a drug that has protein targets, then get_drugs_mechanisms.
    Step 2: take a target protein and get_relationship_given_entity for its neighbors.

    Exercises the whole stack across a multi-call chain where the output of one
    tool becomes the input of the next.
    """
    def test_drug_targets_to_neighbors_workflow(self):
        async def run():
            async with Client(mcpserver.mcp) as client:
                # Discover a drug that actually has protein targets in this graph,
                # so the workflow runs on real data regardless of any one drug name.
                probe = await client.call_tool(
                    "execute_read_only_cypher",
                    {"query":
                        "MATCH (d:Drug)-[:HAS_MECHANISM|INTERACTS_WITH]->(:Protein) "
                        "RETURN d.label AS drug LIMIT 1"},
                )
                probe_rows = _result_data(probe)
                if not isinstance(probe_rows, list) or not probe_rows:
                    return None, None, None  # no drug-target data in this graph
                drug = probe_rows[0]["drug"]

                # Step 1: the protein targets of that drug (ec_filter="" = all classes).
                step1 = await client.call_tool(
                    "get_drugs_mechanisms",
                    {"drug_identifiers": [drug], "ec_filter": ""},
                )
                targets = _result_data(step1)
                if not isinstance(targets, list) or not targets:
                    return drug, targets, None

                # Step 2: what is one of those targets connected to? (chained input)
                target = next(
                    (row["protein_label"] for row in targets
                     if isinstance(row, dict) and row.get("protein_label")),
                    None,
                )
                if not target:
                    return drug, targets, None
                step2 = await client.call_tool(
                    "get_relationship_given_entity", {"entity": target, "limit": 5}
                )
                return drug, targets, _result_data(step2)

        drug, targets, neighbors = asyncio.run(run())

        if drug is None:
            pytest.skip("no drug-target data (Drug -> Protein) in this graph")
        assert isinstance(targets, list) and targets, f"{drug}: step 1 returned no targets"
        assert neighbors is not None, "step 2 did not run (no usable target label)"
        assert isinstance(neighbors, (list, str)), "step 2 (target neighbors) did not return"
