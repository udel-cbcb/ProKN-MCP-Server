"""Offline tests for the ProKN MCP tool wrappers

The Neo4j layer (_run) is mocked, so these run with no database. They cover
input validation, the not-found / guidance messaging, success passthrough, and
the get_subgraph JSON shape (mirroring how mcp-proto-okn mocks SPARQLWrapper)

Run:  python -m pytest tests/test_tools_offline.py -v
"""
import json
import urllib.parse
from unittest.mock import patch
import mcpserver

def test_search_entities_requires_min_length():
    msg = mcpserver.search_entities("a")
    assert isinstance(msg, str) and msg.startswith("Error")

def test_get_drugs_mechanisms_requires_ids():
    msg = mcpserver.get_drugs_mechanisms([])
    assert isinstance(msg, str) and "required" in msg

def test_get_protein_interactions_requires_two():
    msg = mcpserver.get_protein_interactions("EGFR", "")
    assert isinstance(msg, str) and "TWO proteins" in msg

def test_get_subgraph_requires_entity():
    msg = mcpserver.get_subgraph("")
    assert isinstance(msg, str) and msg.startswith("Error")

def test_get_subgraph_rejects_out_of_range_max_hops():
    msg = mcpserver.get_subgraph("EGFR", max_hops=9)
    assert isinstance(msg, str) and "max_hops" in msg

def test_get_relationship_given_entity_requires_entity():
    msg = mcpserver.get_relationship_given_entity("")
    assert isinstance(msg, str) and msg.startswith("Error")

# Success passthrough; mock _run to return rows
@patch("mcpserver._run")
def test_search_entities_returns_rows(mock_run):
    rows = [{"node_type": "Gene", "name": "EGFR", "identifiers": {}, "match_rank": 0}]
    mock_run.return_value = rows
    assert mcpserver.search_entities("EGFR") == rows

@patch("mcpserver._run")
def test_get_drugs_mechanisms_returns_rows(mock_run):
    rows = [{"drug_name": "lapatinib", "protein_label": "P00533"}]
    mock_run.return_value = rows
    assert mcpserver.get_drugs_mechanisms(["lapatinib"]) == rows

# Not-found guidance; mock _run to return nothing
@patch("mcpserver._run")
def test_search_entities_not_found_message(mock_run):
    mock_run.return_value = []
    msg = mcpserver.search_entities("zzzzz")
    assert isinstance(msg, str) and "No entities found" in msg

@patch("mcpserver._run")
def test_get_relationship_given_entity_not_found(mock_run):
    # main query returns nothing; the existence check then reports total 0
    mock_run.side_effect = [[], [{"total": 0}]]
    msg = mcpserver.get_relationship_given_entity("zzzzz")
    assert isinstance(msg, str) and "No entity found" in msg

# get_subgraph JSON shape
@patch("mcpserver._run")
def test_get_subgraph_returns_json_string(mock_run):
    subgraph = {
        "start": {"id": "P00533", "labels": ["Protein"], "name": "EGFR"},
        "node_count": 2,
        "relationship_count": 1,
        "nodes": [
            {"id": "P00533", "labels": ["Protein"], "name": "EGFR"},
            {"id": "P62993", "labels": ["Protein"], "name": "GRB2"},
        ],
        "relationships": [
            {"type": "INTERACTS_WITH", "start": "P00533", "end": "P62993"}
        ],
    }
    mock_run.return_value = [{"subgraph": subgraph}]
    result = mcpserver.get_subgraph("EGFR")
    assert isinstance(result, str)
    parsed = json.loads(result)
    assert parsed["node_count"] == 2
    assert len(parsed["nodes"]) == 2

@patch("mcpserver._run")
def test_get_subgraph_not_found(mock_run):
    mock_run.side_effect = [[], [{"total": 0}]]
    msg = mcpserver.get_subgraph("zzzzz")
    assert isinstance(msg, str) and "No entity found" in msg

# execute_read_only_cypher write guard
def test_is_write_query_allows_reads_with_keyword_like_names():
    reads = [
        "MATCH (n:Protein) RETURN n.label LIMIT 3",
        "MATCH (n) WHERE n.createdAt > 0 RETURN n",   # 'createdAt' must not trip CREATE
        "MATCH (n) RETURN n.set",                     # dotted property named 'set'
        "MATCH (n:Dropoff) RETURN n",                 # label containing DROP
    ]
    for q in reads:
        assert mcpserver._is_write_query(q) is False, q

def test_is_write_query_flags_mutations():
    writes = [
        "CREATE (n:X)",
        "MATCH (n) SET n.x = 1",
        "MATCH (n) DETACH DELETE n",
        "MERGE (n:X)",
        "MATCH (n) REMOVE n.p",
        "DROP INDEX foo",
    ]
    for q in writes:
        assert mcpserver._is_write_query(q) is True, q

def test_execute_read_only_cypher_rejects_writes():
    msg = mcpserver.execute_read_only_cypher("CREATE (n:Hacked) RETURN n")
    assert isinstance(msg, str) and msg.startswith("Error")

def test_is_forbidden_query_blocks_dangerous_procedures():
    for q in [
        "CALL apoc.load.json('http://evil/x')",
        "CALL apoc.export.csv.all('out.csv', {})",
        "CALL dbms.components()",
        "LOAD CSV FROM 'file:///x.csv' AS row RETURN row",
    ]:
        assert mcpserver._is_forbidden_query(q) is True, q

def test_is_forbidden_query_allows_plain_reads():
    for q in [
        "MATCH (n:Protein) RETURN n LIMIT 3",
        "MATCH (n) WHERE n.createdAt > 0 RETURN n",
    ]:
        assert mcpserver._is_forbidden_query(q) is False, q

def test_execute_read_only_cypher_rejects_forbidden_procedure():
    msg = mcpserver.execute_read_only_cypher("CALL apoc.load.json('http://x')")
    assert isinstance(msg, str) and msg.startswith("Error")

# Remaining tools: required-arg validation
def test_get_proteins_catalyzing_sites_requires_sites():
    assert mcpserver.get_proteins_catalyzing_sites([]).startswith("Error")

def test_get_phosphosites_catalyzed_by_proteins_requires_proteins():
    assert mcpserver.get_phosphosites_catalyzed_by_proteins([]).startswith("Error")

def test_get_proteins_encoded_by_genes_requires_genes():
    assert mcpserver.get_proteins_encoded_by_genes([]).startswith("Error")

def test_filter_proteins_by_ec_number_requires_proteins():
    assert mcpserver.filter_proteins_by_ec_number([]).startswith("Error")

def test_get_pathways_between_protein_sets_requires_both():
    assert mcpserver.get_pathways_between_protein_sets([], ["MAPK1"]).startswith("Error")
    assert mcpserver.get_pathways_between_protein_sets(["PLK1"], []).startswith("Error")

def test_get_genes_regulated_by_drugs_requires_ids():
    assert mcpserver.get_genes_regulated_by_drugs([]).startswith("Error")

def test_perturbagen_requires_name_and_valid_direction():
    assert mcpserver.get_phosphosites_regulated_by_perturbagen("").startswith("Error")
    assert mcpserver.get_phosphosites_regulated_by_perturbagen(
        "alpelisib", direction="sideways"
    ).startswith("Error")

# Remaining tools: success passthrough (mock _run -> rows)
@patch("mcpserver._run")
def test_remaining_tools_passthrough(mock_run):
    rows = [{"ok": 1}]
    mock_run.return_value = rows
    assert mcpserver.get_proteins_catalyzing_sites(["AKT1_S473"]) == rows
    assert mcpserver.get_phosphosites_catalyzed_by_proteins(["CDK1"]) == rows
    assert mcpserver.get_proteins_encoded_by_genes(["EGFR"]) == rows
    assert mcpserver.filter_proteins_by_ec_number(["EGFR"]) == rows
    assert mcpserver.get_pathways_between_protein_sets(["PLK1"], ["MAPK1"]) == rows
    assert mcpserver.get_genes_regulated_by_drugs(["cc-401"]) == rows
    assert mcpserver.get_phosphosites_regulated_by_perturbagen("alpelisib") == rows

# get_queries transparency tool
def test_get_queries_returns_query_for_known_tool():
    assert mcpserver.get_queries("get_subgraph") == mcpserver.QUERY_GET_SUBGRAPH_TEMPLATE

def test_get_queries_unknown_tool_message():
    msg = mcpserver.get_queries("get_relationship_type")  # phantom, no longer exists
    assert isinstance(msg, str) and "no static query" in msg

# Regression: search_entities no longer passes the dead name_keys/id_keys params
@patch("mcpserver._run")
def test_search_entities_omits_dead_params(mock_run):
    mock_run.return_value = [{"name": "EGFR"}]
    mcpserver.search_entities("EGFR")
    params = mock_run.call_args.kwargs.get("params", {})
    assert "name_keys" not in params and "id_keys" not in params
    assert "t" in params  # sanity: the real params are still passed

# Schema / introspection tools
@patch("mcpserver._run")
def test_get_graph_schema_passthrough(mock_run):
    rows = [{"Schema": "Protein --INTERACTS_WITH--> Protein"}]
    mock_run.return_value = rows
    assert mcpserver.get_graph_schema() == rows

@patch("mcpserver._run")
def test_introspection_tools_passthrough(mock_run):
    rows = [{"nodeName": "Protein", "properties": ["label", "ecNumber"]}]
    mock_run.return_value = rows
    assert mcpserver.get_node_properties() == rows
    assert mcpserver.get_relationship_properties() == rows

@patch("mcpserver._run", side_effect=Exception("TransactionTimedOut"))
def test_introspection_tools_degrade_on_timeout(mock_run):
    # The db.schema.* procedures can time out on a large graph; the tools must
    # return a guidance message pointing to get_graph_schema, not raise
    for result in (mcpserver.get_node_properties(), mcpserver.get_relationship_properties()):
        assert isinstance(result, str) and "get_graph_schema()" in result

@patch("mcpserver._run")
def test_get_protein_interactions_passthrough(mock_run):
    rows = [{"interaction_path": [{"name": "P00533", "type": "Protein"}], "path_length": 1}]
    mock_run.return_value = rows
    assert mcpserver.get_protein_interactions("EGFR", "GRB2") == rows


# ---------------------------------------------------------------------------
# get_explorer_network, ID mapping, and the query log
# ---------------------------------------------------------------------------

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


def test_get_explorer_network_requires_two():
    msg = mcpserver.get_explorer_network(["EGFR"])
    assert isinstance(msg, str) and "at least two" in msg


def test_get_explorer_network_requires_input():
    msg = mcpserver.get_explorer_network([])
    assert isinstance(msg, str) and msg.startswith("Error")


def _filter_from_url(url):
    """Pull the decoded JSON filter out of an explorer_url built by the tool."""
    q = urllib.parse.urlparse(url).query
    return json.loads(urllib.parse.parse_qs(q)["filter"][0])


def test_get_explorer_network_symbols():
    # No network call for the GENENAME path: the link is self-contained.
    res = mcpserver.get_explorer_network(["EGFR", "TP53"])
    assert isinstance(res, dict)
    assert "network_id" not in res
    assert "explorer?filter=" in res["explorer_url"]
    assert res["gene_names"] == ["EGFR", "TP53"]
    assert _filter_from_url(res["explorer_url"]) == {"gene_names": ["EGFR", "TP53"]}
    assert "mapping" not in res  # GENENAME path adds no mapping block


@patch("mcpserver.urllib.request.urlopen")
def test_get_explorer_network_from_acc(mock_open):
    # only network call is the PIR mapping; the link itself is self-contained (no POST)
    mock_open.return_value = _FakeResp(b"P00533\tEGFR\nP04637\tTP53\n")
    res = mcpserver.get_explorer_network(["P00533", "P04637"], from_type="ACC")
    assert res["gene_names"] == ["EGFR", "TP53"]
    assert "network_id" not in res
    assert _filter_from_url(res["explorer_url"]) == {"gene_names": ["EGFR", "TP53"]}
    assert res["mapping"] and "PIR" in res["mapping"]
    assert res["unmapped"] == []


@patch("mcpserver.urllib.request.urlopen")
def test_map_ids_via_pir(mock_open):
    mock_open.return_value = _FakeResp(b"P00533\tEGFR\nP04637\tTP53\nQ0\t\n")
    genes, unmapped = mcpserver._map_ids_via_pir(["P00533", "P04637", "Q0"], "ACC")
    assert genes == ["EGFR", "TP53"]
    assert unmapped == ["Q0"]


@patch("mcpserver._run")
def test_map_ids_via_graph_hit(mock_run):
    mock_run.return_value = [
        {"node_type": "Protein", "name": "EGFR", "identifiers": {"geneNames": "EGFR"}},
    ]
    genes, unmapped = mcpserver._map_ids_via_graph(["P00533"])
    assert genes == ["EGFR"] and unmapped == []


@patch("mcpserver._run")
def test_map_ids_via_graph_unmapped(mock_run):
    mock_run.return_value = []
    genes, unmapped = mcpserver._map_ids_via_graph(["ZZZ"])
    assert genes == [] and unmapped == ["ZZZ"]


def test_query_log_reset_and_get():
    mcpserver.reset_query_log()
    assert isinstance(mcpserver.get_query_log(), str)  # empty -> guidance message
    mcpserver._session_log().append(
        {"step": 1, "tool": "search_entities", "arguments": {}, "time": "t"})
    log = mcpserver.get_query_log()
    assert isinstance(log, list) and log[0]["tool"] == "search_entities"
    mcpserver.reset_query_log()
    assert isinstance(mcpserver.get_query_log(), str)


def test_create_reproducibility_record_writes_file(tmp_path, monkeypatch):
    monkeypatch.setenv("PROKN_RECORD_DIR", str(tmp_path))
    mcpserver.reset_query_log()
    mcpserver._session_log().append(
        {"step": 1, "tool": "get_drugs_mechanisms", "arguments": {"drug_identifiers": ["lapatinib"]}, "time": "t"})
    conf = mcpserver.create_reproducibility_record(question="what does lapatinib inhibit?",
                                                   findings="EGFR, ERBB2",
                                                   skills="prokn-analysis v0.3.0")
    assert isinstance(conf, str) and "Saved the reproducibility record" in conf
    files = list(tmp_path.glob("prokn-record-*.md"))
    assert files, "no record file written"
    text = files[0].read_text()
    assert "get_drugs_mechanisms" in text        # tool call pulled from the log
    assert "## Findings" in text
    # the resource serves the same saved record
    assert mcpserver.reproducibility_record_resource() == text
