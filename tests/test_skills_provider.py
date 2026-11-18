"""Offline tests for the agent-skill resources and the skill<->server contract

Covers what would silently break skills if it drifted: every skill is served (as a
skill:// resource and a prompt), every tool a skill names still exists, and the server
instructions point to the skills and stay under 2 KB.

Run:  python -m pytest tests/test_skills_provider.py -v
"""
import asyncio
import re
from pathlib import Path

from fastmcp import Client
from fastmcp.utilities.skills import list_skills

import mcpserver

SKILLS_DIR = Path(__file__).resolve().parent.parent / "skills"
EXPECTED_SKILLS = {"prokn-search", "prokn-explorer", "prokn-literature-review"}

# Tools that skills call on *other* MCP servers (prokn-literature-review drives the PubMed MCP,
# and the Paperclip MCP when connected). They are not expected on the ProKN server, so the
# contract test ignores them. Paperclip's tool names (evidence, search, lookup, grep, cat, ...)
# don't match the prefixes the extractor looks for, so they don't need listing here.
EXTERNAL_TOOLS = {
    "search_articles",
    "get_article_metadata",
    "get_full_text_article",
    "get_copyright_status",
    "find_related_articles",
    "lookup_article_by_citation",
    "convert_article_ids",
}


def _run(coro):
    return asyncio.run(coro)


def test_every_skill_is_a_resource_and_a_prompt():
    async def check():
        async with Client(mcpserver.mcp) as c:
            return {s.name for s in await list_skills(c)}, {p.name for p in await c.list_prompts()}

    resources, prompts = _run(check())
    assert resources == EXPECTED_SKILLS, f"skill resources: {sorted(resources)}"  # no .skill zips
    assert EXPECTED_SKILLS <= prompts, f"skills missing as prompts: {sorted(EXPECTED_SKILLS - prompts)}"


# ---------------------------------------------------------------------------
# Contract: every tool referenced by a skill must be registered on the server
# ---------------------------------------------------------------------------

def _skill_referenced_tools() -> set[str]:
    """Tool-like identifiers (get_*, search_*, ...) mentioned in skills/**.md."""
    found = set()
    for p in SKILLS_DIR.rglob("*.md"):
        for m in re.findall(r"`([a-z][a-z0-9_]{3,})`", p.read_text(encoding="utf-8")):
            if m.startswith(("get_", "search_", "reset_", "create_", "execute_", "filter_")):
                found.add(m)
    return found


def test_skills_reference_only_registered_tools():
    async def check():
        async with Client(mcpserver.mcp) as c:
            return {t.name for t in await c.list_tools()}

    registered = _run(check())
    referenced = _skill_referenced_tools()
    assert referenced, "no tool references found in skills — extraction regex broke"
    missing = referenced - registered - EXTERNAL_TOOLS
    assert not missing, (
        f"skills reference tools the server does not expose: {sorted(missing)}"
    )


# ---------------------------------------------------------------------------
# Server instructions point clients at the skills; every skill:// address they
# name must resolve, and they must stay under the ~2 KB clients may keep.
# ---------------------------------------------------------------------------

def test_instructions_point_to_readable_skills():
    async def check():
        async with Client(mcpserver.mcp) as c:
            instr = c.initialize_result.instructions or ""
            uris = sorted(set(re.findall(r"skill://[a-z-]+/SKILL\.md", instr)))
            texts = {}
            for u in uris:
                r = await c.read_resource(u)
                texts[u] = r[0].text if isinstance(r, list) else r
            return instr, uris, texts

    instr, uris, texts = _run(check())
    assert {u.split("/")[2] for u in uris} == EXPECTED_SKILLS, "instructions should name every skill"
    for u, body in texts.items():
        assert body.startswith("---"), f"{u} did not resolve to a SKILL.md"
    assert len(instr.encode()) <= 2048, f"server instructions are {len(instr.encode())} bytes"
