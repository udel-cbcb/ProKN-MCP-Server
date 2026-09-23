#  MCP Server for ProKN

This folder contains the code for an MCP server for Protein Knowledge Network (ProKN). It is built using FastMCP with foundational tools to enable the use cases at https://research.bioinformatics.udel.edu/ProKN/usecases.  

## Index:
- [Local Development](#local-development)
- [Agent Skills](#agent-skills)
- [Testing](#testing)
- [Build Docker Image](#build-docker-image)
- [Usage](#usage)

## Local Development

### Requirements
- Python 3.10+
- An MCP Client (e.g. Google Antigravity or Claude Desktop)
- FastMCP - `pip install -r requirements.txt`
- (Optional) if using the stdio transport: `uv` python package manager. See https://docs.astral.sh/uv/getting-started/installation/ for installation instructions

### Procedure
To run the FastMCP Server in a local terminal session for development:
1. Export the following environment variables:

```bash
export NEO4J_URI="bolt://localhost:<neo4j_local_port>"
export NEO4J_USERNAME="<neo4j_username>"
export NEO4J_PASSWORD="<neo4j_password>"
```
2. Start the MCP Server: `python mcpserver.py streamable-http`
3. Add the following config to your MCP Client's MCP server list. If the `mcpservers` key already exists, then just add the `prokn` key and value under it. 

For example, the path for the MCP server config for the Antigravity MCP client is usually `~/.gemini/antigravity/mcp_config.json`

```json
{
  "mcpServers": {
    "prokn": {
      "command": "npx",
      "args": [
        "-y",
        "mcp-remote@latest",
        "http://localhost:8000/mcp",
        "--http",
        "--allow-http"
      ]
    }
  }
}
```

## Agent Skills

The server exposes the agent skills in [`skills/`](./skills) (`prokn-analysis`, `prokn-explorer`) as MCP resources via FastMCP's `SkillsDirectoryProvider`, so any connected MCP client can discover and read them — no `.skill` install needed:

- `skill://<name>/SKILL.md` — the skill definition (markdown)
- `skill://<name>/_manifest` — JSON file listing (path, size, sha256) of everything in the skill folder
- `skill://<name>/<path>` (resource template) — supporting files, e.g. `skill://prokn-analysis/references/tool-map.md` or `skill://prokn-explorer/scripts/prokn_explorer.py`

Only subfolders of `skills/` containing a `SKILL.md` are picked up; the committed `.skill` zip bundles are ignored. The `skills/` folder must be present next to `mcpserver.py` (the Docker image copies it). FastMCP clients can enumerate them with `fastmcp.utilities.skills.list_skills()` / `download_skill()`; other clients can just list and read resources.

### Editing skills

When you change anything under `skills/`:

1. **Keep `description` on a single line** in the `SKILL.md` frontmatter (single-quoted YAML). FastMCP's line-based frontmatter parser can't read `description: >-` folded blocks — they'd be exposed as the literal string `>-`.
2. **Rebuild the bundle**: run the skill's `build.sh` and commit the updated `.skill` (the bundles in `skills/` are generated from the source folders).
3. **Keep version references in sync**: any `prokn-*  vX.Y.Z` string in prose (skill bodies, READMEs, the `skills` field example in `mcpserver.py`) must match the `metadata.version` in that skill's `SKILL.md`. Both skills are currently v0.3.0.
4. **Tool renames are guarded**: `tests/test_skills_provider.py` fails if a skill references a tool the server no longer exposes.

## Testing

Tests use `pytest` and are split into a fast offline tier (no database) and a live tier that queries Neo4j

Install the dev dependencies (adds `pytest` and `pytest-cov` on top of the runtime deps):

```bash
pip install -r requirements-dev.txt
```

Run the offline suite (no Neo4j needed — this is what CI runs on every push):

```bash
python -m pytest -m "not live" -v
```

Run the live suite against a running Neo4j (export the same env vars as Local Development, with the database reachable). Live tests auto-skip if Neo4j is unreachable:

```bash
python -m pytest -m live -v
```

Everything, with a coverage report:

```bash
python -m pytest --cov=. -v
```

Layout:
- `tests/test_arg_normalization.py` : offline, the argument-normalization middleware
- `tests/test_tools_offline.py` : offline, tool wrappers with the Neo4j layer mocked
- `tests/test_tool_routing.py` : offline, prompt → tool routing signals in descriptions
- `tests/test_skills_provider.py` : offline, skills exposed as `skill://` resources + skill↔server tool contract
- `tests/test_tools_live.py` : live, real Neo4j (marked `live`)

## Build Docker Image
Before deploying the MCP Server for production use, test the docker image. The Dockerfile is at [./Dockerfile](./Dockerfile). <br>
1. Build the Docker image using `docker build -t prokn-mcp-server -f Dockerfile .`
2. Start the container:
```sh
docker run -d \
  --name prokn-mcp-server \
  -p 8000:8000 \
  -e NEO4J_URI="bolt://host.docker.internal:<neo4j_port>" \
  -e NEO4J_USERNAME="<neo4j_username>" \
  -e NEO4J_PASSWORD="<neo4j_password>" \
  prokn-mcp-server
```

3. Run `docker container ls` and wait for the STATUS to become healthy.
4. Add the same config as in Step 3 of Local Development to your MCP Client's MCP server list.
5. Test the MCP server by running any query on the MCP Client. To see the logs: run `docker logs prokn-mcp-server` in a new terminal session and verify that the server is working as expected.

## Usage

1. This source code is also deployed to the ProKN website, i.e. https://research.bioinformatics.udel.edu/ProKN/mcp. A user would need to add the following config to their MCP client:
```json
{
  "mcpServers": {
    "prokn": {
      "command": "npx",
      "args": [
        "-y",
        "mcp-remote@latest",
        "https://research.bioinformatics.udel.edu/ProKN/mcp",
        "--http",
        "--allow-http"
      ]
    }
  }
}
```
2. The MCP Client usually needs to be refreshed (Google Antigravity) or restarted (Claude Desktop) for the new MCP Server handshake to be completed and the MCP server to be recognized.
