"""Offline unit tests for the argument-normalization middleware.

Pure-logic tests: no Neo4j, no network, no running server. They validate that
the middleware rewrites mis-named / wrong-shape tool arguments into the canonical
form, and that a single-protein interaction call is redirected instead of failing.

Run just these:  python -m pytest tests/test_arg_normalization.py -v
"""
from arg_normalization import normalize_args, normalize_call

# Alias renaming + list coercion
def test_search_entities_alias_query_to_term():
    assert normalize_args("search_entities", {"query": "EGFR"}) == {"term": "EGFR"}

def test_search_entities_list_coercion():
    out = normalize_args("search_entities", {"term": "EGFR", "entity_types": "Protein"})
    assert out["entity_types"] == ["Protein"]

def test_drugs_mechanisms_alias_and_list_coercion():
    out = normalize_args("get_drugs_mechanisms", {"identifiers": "aspirin"})
    assert out == {"drug_identifiers": ["aspirin"]}

def test_relationship_given_entity_protein_alias():
    out = normalize_args("get_relationship_given_entity", {"protein_name": "EGFR"})
    assert out["entity"] == "EGFR"

def test_catalyzed_single_string_becomes_list():
    out = normalize_args("get_phosphosites_catalyzed_by_proteins", {"protein_name": "PRKAA1"})
    assert out == {"proteins": ["PRKAA1"]}

# Routing a stray value to the tool's primary parameter
def test_stray_value_routed_to_primary():
    out = normalize_args("search_entities", {"foobar": "EGFR"})
    assert out.get("term") == "EGFR"

def test_empty_stray_value_not_routed():
    out = normalize_args("search_entities", {"foobar": ""})
    assert "term" not in out

# Two-protein funnel (get_protein_interactions)
def test_interactions_two_via_protein_ids():
    out = normalize_args(
        "get_protein_interactions", {"protein_ids": ["EGFR", "GRB2"], "limit": 50}
    )
    assert out == {"protein1": "EGFR", "protein2": "GRB2"}

def test_interactions_two_via_proteins_list():
    out = normalize_args("get_protein_interactions", {"proteins": ["EGFR", "GRB2"]})
    assert out == {"protein1": "EGFR", "protein2": "GRB2"}

def test_interactions_dedup_case_insensitive():
    out = normalize_args("get_protein_interactions", {"protein1": "EGFR", "protein2": "egfr"})
    assert out == {"protein1": "EGFR"}  # deduped -> only one protein survives

# Unknown tools pass through untouched
def test_unknown_tool_passthrough():
    assert normalize_args("not_a_tool", {"anything": 1}) == {"anything": 1}

# normalize_call: single protein redirects to a neighbor lookup
def test_single_protein_redirects_to_neighbor_lookup():
    name, out = normalize_call("get_protein_interactions", {"protein_name": "PIK3CA"})
    assert name == "get_relationship_given_entity"
    assert out == {"entity": "PIK3CA"}

def test_two_proteins_do_not_redirect():
    name, out = normalize_call("get_protein_interactions", {"protein_ids": ["EGFR", "GRB2"]})
    assert name == "get_protein_interactions"
    assert out == {"protein1": "EGFR", "protein2": "GRB2"}

def test_normalize_call_normal_tool_keeps_name():
    name, out = normalize_call("search_entities", {"query": "EGFR"})
    assert name == "search_entities"
    assert out == {"term": "EGFR"}