# prokn-explorer

A skill that takes a list of gene symbols, builds a ProKN network from them, and returns
an Explorer link. See `SKILL.md` for what it does; `scripts/prokn_explorer.py` is the code.

```
skills/
├── prokn-explorer.skill        # prebuilt bundle (built here by build.sh), committed for install
└── prokn-explorer/
    ├── SKILL.md                # the skill definition (what an agent reads)
    ├── README.md               # this file
    ├── build.sh                # rebuilds the bundle into ../ (the skills/ dir)
    ├── references/             # extra detail, loaded on demand
    │   ├── id-types.md
    │   └── pitfalls.md
    └── scripts/
        └── prokn_explorer.py   # the script the skill runs
```

## Packaging it as a .skill bundle

A `.skill` file is just a zip of this folder's contents with the extension renamed from
`.zip` to `.skill`. `SKILL.md` must sit at the top level of the zip (not inside a
subfolder). Cowork shows a "Save skill" install button when you open a `.skill` file.

### Command line (recommended)

From inside this `prokn-explorer/` folder, just run the bundled script:

```bash
./build.sh
```

It does the zip for you (and clears stale caches first). If you'd rather run it by hand, that's:

```bash
zip -r ../prokn-explorer.skill SKILL.md scripts references -x '*/__pycache__/*' '*/.DS_Store'
```

### Finder (no terminal)

1. Select `SKILL.md`, the `scripts` folder, and the `references` folder together.
2. Right-click → Compress. macOS makes `Archive.zip`.
3. Rename it to `prokn-explorer.skill` and move it up into the `skills/` folder.

Note: compressing the whole `prokn-explorer` folder instead nests everything under a
`prokn-explorer/` directory inside the zip, which puts `SKILL.md` one level too deep.
Select the contents (SKILL.md, scripts, references), not the folder.

## Installing

- **Cowork:** open the `.skill` file and click "Save skill".
- **Claude Code:** copy the `prokn-explorer/` folder into `~/.claude/skills/` (personal) or
  `.claude/skills/` in a repo (project-scoped). No packaging needed there.

## Via the ProKN MCP server

No install needed: the server exposes this skill as MCP resources from the repo's `skills/`
folder (see the root README's Agent Skills section):

- `skill://prokn-explorer/SKILL.md` — the skill definition
- `skill://prokn-explorer/_manifest` — file listing (path, size, sha256)
- `skill://prokn-explorer/<path>` — supporting files, e.g. `references/id-types.md`
  or `scripts/prokn_explorer.py`

When the server is connected, the skill's **primary run path** is its `get_explorer_network`
tool; the bundled script below is the fallback for when there's no server.

The `.skill` bundle and `SKILL.md` format are Anthropic-specific, but the actual capability is
reachable three ways off Claude — via the MCP server (resources above), as a script, or as plain
instructions:

1. **Run the script directly.** Any Python 3 environment can run it, no AI platform required:

   ```bash
   python scripts/prokn_explorer.py PLK3 HIPK3 MAPK11 CDK1 CDK2
   ```

2. **Hand it to a code-capable assistant.** For an assistant that can run code (e.g. ChatGPT
   with code execution, Gemini, or a coding agent), give it `scripts/prokn_explorer.py` plus the
   text of `SKILL.md` as instructions, and ask it to run the script for a gene list. `SKILL.md`
   is plain Markdown, so any model can follow it even though it isn't a formal "skill" there.

## Maintainer rules

- **`description` stays on a single line** in `SKILL.md` frontmatter (single-quoted YAML).
  FastMCP's parser can't read `description: >-` folds and would expose `>-` as the description.
- **Bump `metadata.version`** in `SKILL.md` when the skill changes, and update any
  `prokn-explorer  vX.Y.Z` cross-references elsewhere (e.g. `prokn-analysis/SKILL.md` cites this
  skill's version in its reproducibility examples).

## Note

A prebuilt `prokn-explorer.skill` is committed in the parent `skills/` folder so people can install it
directly. It's generated from the source in this folder (`SKILL.md`, `scripts/`, `references/`),
so run `./build.sh` and re-commit the new `.skill` whenever you change those.