# prokn-analysis

An Agent Skill that teaches a model how to investigate a biological question with the ProKN MCP
server: resolve entities, pull the relevant relationships/pathways/subgraphs, cite the evidence on
each edge, and (when useful) hand the resulting gene set to `prokn-explorer` for a network picture.

It's the methodology layer over ProKN's data tools, not a replacement for them. See `SKILL.md` for
the flow and operating rules. Pairs with the `prokn-explorer` skill for the visualization step.

```
skills/
├── prokn-analysis.skill        # prebuilt bundle (built here by build.sh), committed for install
└── prokn-analysis/
    ├── SKILL.md                # the skill definition (what an agent reads)
    ├── README.md               # this file
    ├── build.sh                # rebuilds the bundle into ../ (the skills/ dir)
    └── references/             # extra detail, loaded on demand
        ├── tool-map.md         # which tool answers which question + common chains
        ├── analysis-menu.md    # named recipes (kinase-substrate, crosstalk, repurposing, ...)
        ├── cross-source.md     # combining ProKN's source datasets, keeping provenance separate
        ├── evidence.md         # per-source citation guide and evidence tiers
        └── pitfalls.md         # recurring cross-tool mistakes and fixes
```

Status: early (v0.1.0). The core flow, tool map, and pitfalls are in place; expect it to grow as
we use it.

## Requirements

The ProKN MCP server (its data tools) must be connected in your client. This skill has no script of
its own; it drives the server's tools.

## Packaging it as a .skill bundle

A `.skill` file is just a zip of this folder's contents (with `SKILL.md` at the top level) renamed
to `.skill`. From inside this folder, run the build script:

```bash
./build.sh
```

Or by hand:

```bash
zip -r ../prokn-analysis.skill SKILL.md references -x '*/.DS_Store'
```

## Installing

- **Cowork:** open the `.skill` file and click "Save skill".
- **Claude Code:** copy the `prokn-analysis/` folder into `~/.claude/skills/` (personal) or
  `.claude/skills/` in a repo (project-scoped). No packaging needed there.

## Note

The committed `prokn-analysis.skill` (in the parent `skills/` folder) is built from the source in
this folder (`SKILL.md`, `references/`), so run `./build.sh` and re-commit the new `.skill`
whenever you change those.
