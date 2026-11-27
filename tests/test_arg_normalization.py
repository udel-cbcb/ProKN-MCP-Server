"""Offline unit tests for the argument-normalization middleware (no Neo4j, no network).

Run just these:  python -m pytest tests/test_arg_normalization.py -v
"""
from arg_normalization import normalize_args, normalize_call


def test_alias_renamed_and_string_coerced_to_list():
    out = normalize_args("get_drugs_mechanisms", {"identifiers": "aspirin"})
    assert out == {"drug_identifiers": ["aspirin"]}


def test_empty_list_entries_dropped():
    # models sometimes send [null] for "no filter"; it used to fail validation
    out = normalize_args("get_explorer_network", {"gene_names": ["CDK1", "CDK2"], "entity_types": [None]})
    assert out == {"gene_names": ["CDK1", "CDK2"]}


def test_stray_value_routed_to_primary():
    assert normalize_args("search_entities", {"foobar": "EGFR"}).get("term") == "EGFR"


def test_two_proteins_from_a_list():
    out = normalize_args("get_protein_interactions", {"protein_ids": ["EGFR", "GRB2"], "limit": 50})
    assert out == {"protein1": "EGFR", "protein2": "GRB2"}


def test_single_protein_redirects_to_neighbor_lookup():
    name, out = normalize_call("get_protein_interactions", {"protein_name": "PIK3CA"})
    assert (name, out) == ("get_relationship_given_entity", {"entity": "PIK3CA"})
