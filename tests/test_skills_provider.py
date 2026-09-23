"""Offline tests for the agent-skill resources and the skill<->server contract

Covers two things that would silently break skills if they drifted:
  1. Both skills in skills/ are exposed as skill:// resources (SKILL.md, manifest,
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
EXPECTED_SKILLS = {"prokn-analysis", "prokn-explorer"}


def _run(coro):
    return asyncio.run(coro)


def test_both_skills_are_discovered():
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
            md = await c.read_resource("skill://prokn-analysis/SKILL.md")
            main = md[0].text if isinstance(md, list) else md
            # supporting file via the resource template
            ref = await c.read_resource("skill://prokn-explorer/references/id-types.md")
            ref_text = ref[0].text if isinstance(ref, list) else ref
            return main, ref_text

    main, ref_text = _run(check())
    assert main.startswith("---") and "# ProKN analysis" in main
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

def test_both_skills_are_exposed_as_prompts():
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
    missing = referenced - registered
    assert not missing, (
        f"skills reference tools the server does not expose: {sorted(missing)}"
    )
