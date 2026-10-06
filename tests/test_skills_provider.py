"""Offline tests for the agent-skill resources and the skill<->server contract

Covers two things that would silently break skills if they drifted:
  1. All skills in skills/ are exposed as skill:// resources (SKILL.md, manifest,
     supporting files) by the SkillsDirectoryProvider registered on the server.
  2. Every tool a skill references is actually registered on the server, so a
     renamed/removed tool can't strand the skills.

Run:  python -m pytest tests/test_skills_provider.py -v
"""
import asyncio
import re
from pathlib import Path

from fastmcp import Client
from fastmcp.utilities.skills import get_skill_manifest, list_skills

import mcpserver

SKILLS_DIR = Path(__file__).resolve().parent.parent / "skills"
EXPECTED_SKILLS = {"prokn-search", "prokn-explorer", "prokn-literature-review"}

# Tools that skills call on *other* MCP servers (prokn-literature-review drives the PubMed MCP).
# They are not expected on the ProKN server, so the contract test ignores them.
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


def test_all_skills_are_discovered():
    async def check():
        async with Client(mcpserver.mcp) as c:
            skills = await list_skills(c)
            return {s.name for s in skills}

    names = _run(check())
    missing = EXPECTED_SKILLS - names
    assert not missing, f"skills not exposed as resources: {sorted(missing)}"
    # only folders with SKILL.md count; the .skill zips must not appear
    extra = names - EXPECTED_SKILLS
    assert not extra, f"unexpected skills exposed: {sorted(extra)}"


def test_skill_resources_are_readable():
    async def check():
        async with Client(mcpserver.mcp) as c:
            md = await c.read_resource("skill://prokn-search/SKILL.md")
            main = md[0].text if isinstance(md, list) else md
            # supporting file via the resource template
            ref = await c.read_resource("skill://prokn-explorer/references/id-types.md")
            ref_text = ref[0].text if isinstance(ref, list) else ref
            return main, ref_text

    main, ref_text = _run(check())
    assert main.startswith("---") and "# ProKN search" in main
    assert "GENENAME" in ref_text


def test_skill_manifest_lists_expected_files():
    async def check():
        async with Client(mcpserver.mcp) as c:
            man = await get_skill_manifest(c, "prokn-explorer")
            return {f.path for f in man.files}

    files = _run(check())
    assert "SKILL.md" in files
    assert "scripts/prokn_explorer.py" in files
    assert "references/pitfalls.md" in files


# ---------------------------------------------------------------------------
# Prompts: each skill is also selectable from client "/" menus
# ---------------------------------------------------------------------------

def test_all_skills_are_exposed_as_prompts():
    async def check():
        async with Client(mcpserver.mcp) as c:
            return {p.name for p in await c.list_prompts()}

    names = _run(check())
    missing = EXPECTED_SKILLS - names
    assert not missing, f"skills not exposed as prompts: {sorted(missing)}"


def test_prompt_body_is_skill_content_without_frontmatter():
    async def check():
        async with Client(mcpserver.mcp) as c:
            prompts = {p.name: p for p in await c.list_prompts()}
            out = {}
            for name in EXPECTED_SKILLS:
                result = await c.get_prompt(name, {})
                # first user message text
                msg = result.messages[0]
                out[name] = msg.content.text if hasattr(msg.content, "text") else str(msg.content)
            return out

    bodies = _run(check())
    for name, body in bodies.items():
        assert not body.lstrip().startswith("---"), f"{name}: frontmatter not stripped"
        assert "# ProKN" in body, f"{name}: skill body missing"


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
