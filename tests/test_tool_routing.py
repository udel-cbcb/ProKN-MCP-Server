"""Tool-routing / selection contract tests, a tier between smoke and end-to-end

For each representative prompt we assert two things:
  1. the tool that should handle it is actually exposed by the server, and
  2. that tool's description carries the routing signal (a keyword the model
     relies on to pick it).

This guards against a tool being renamed/removed or a description being reworded
in a way that would silently break tool selection
"""
import asyncio
import pytest
from fastmcp import Client
import mcpserver

# (prompt, tool that should handle it, keyword that must be in that tool's description)
PROMPT_ROUTES = [
    ("What phosphosites does alpelisib downregulate?",
     "get_phosphosites_regulated_by_perturbagen", "perturbagen"),
    ("Which kinases does lapatinib inhibit?",
     "get_drugs_mechanisms", "mechanism"),
    ("What is EGFR connected to?",
     "get_relationship_given_entity", "neighbor"),
    ("How are EGFR and GRB2 connected?",
     "get_protein_interactions", "two protein"),
    ("Show the neighborhood around EGFR as a graph.",
     "get_subgraph", "neighborhood"),
    ("What proteins does the EGFR gene encode?",
     "get_proteins_encoded_by_genes", "encoded"),
    ("Resolve the entity EGFR to its node.",
     "search_entities", "resolve"),
    ("Which kinases catalyze AKT1_S473?",
     "get_proteins_catalyzing_sites", "catalyze"),
]

@pytest.fixture(scope="module")
def tool_index():
    """The tool inventory exactly as an MCP client sees it (name -> tool). No DB."""
    async def run():
        async with Client(mcpserver.mcp) as client:
            tools = await client.list_tools()
            return {t.name: t for t in tools}
    return asyncio.run(run())

def test_expected_tools_are_exposed(tool_index):
    expected = {tool for _, tool, _ in PROMPT_ROUTES}
    missing = expected - set(tool_index)
    assert not missing, f"tools not exposed by the server: {sorted(missing)}"

def test_every_tool_has_a_description(tool_index):
    for name, tool in tool_index.items():
        assert (tool.description or "").strip(), f"{name} is exposed with no description"

@pytest.mark.parametrize("prompt,tool_name,keyword", PROMPT_ROUTES)
def test_prompt_routes_to_tool_with_signal(prompt, tool_name, keyword, tool_index):
    assert tool_name in tool_index, f"'{prompt}' should route to {tool_name}, which is not exposed"
    description = (tool_index[tool_name].description or "").lower()
    assert keyword.lower() in description, (
        f"routing signal '{keyword}' is missing from {tool_name}'s description; "
        f"an LLM may fail to select it for: {prompt!r}"
    )
