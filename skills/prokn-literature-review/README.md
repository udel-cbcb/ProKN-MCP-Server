# prokn-literature-review

An Agent Skill that teaches a model to draw inferences from the ProKN graph and then test them
against the literature. It pulls the ProKN edges that bear on a gene/protein/drug/disease set
(often from `prokn-search`), states confidence-graded inferences from those edges (edge strength,
mechanisms, A-B-C bridges, shared context, gaps), and then searches PubMed through the PubMed MCP
for papers that support or contradict each one. The result is a verdict table (supported, mixed,
contradicted, or no literature found) with a short summary.

Inferences are written down before any PubMed search, so the papers test them instead of shaping
them. It has no tool of its own; it describes how to use the connected ProKN and PubMed tools. See
`SKILL.md` for the pipeline and operating rules. Pairs with `prokn-search` (entity set + graph
evidence) and `prokn-explorer` (network view).

```
skills/
├── prokn-literature-review.skill  # prebuilt bundle (built here by build.sh), committed for install
└── prokn-literature-review/
    ├── SKILL.md                   # the skill definition (what an agent reads)
    ├── README.md                  # this file
    ├── build.sh                   # rebuilds the bundle into ../ (the skills/ dir)
    └── references/                # extra detail, loaded on demand
        ├── pubmed-tools.md        # which PubMed tool answers which need + query building
        ├── inference.md           # inference patterns from graph edges, prior confidence
        ├── verification.md        # PubMed checks, verdicts, final confidence, table
        └── pitfalls.md            # recurring mistakes and fixes
```

Status: early (v0.3.0). Version 0.3.0 reverses the order of earlier versions: inferences now come
from the graph first and PubMed is used to test them, instead of reviewing the literature first and
inferring from it.

## Requirements

Both the **ProKN MCP server** (for the graph evidence the inferences come from) and the **PubMed
MCP** (for the literature check) must be connected in your client. The `prokn-search` skill is
useful for gathering the graph evidence. This skill has no script of its own; it drives the
connected servers' tools.

## Packaging it as a .skill bundle

A `.skill` file is just a zip of this folder's contents (with `SKILL.md` at the top level) renamed
to `.skill`. From inside this folder:

```bash
./build.sh
```

Or by hand:

```bash
zip -r ../prokn-literature-review.skill SKILL.md references -x '*/.DS_Store'
```

## Installing

- **Cowork:** open the `.skill` file and click "Save skill".
- **Claude Code:** copy the `prokn-literature-review/` folder into `~/.claude/skills/` (personal) or
  `.claude/skills/` in a repo (project-scoped). No packaging needed there.

## Via the ProKN MCP server

No install needed: the server exposes this skill as MCP resources from the repo's `skills/`
folder (see the root README's Agent Skills section), and as the `prokn-literature-review` MCP
prompt:

- `skill://prokn-literature-review/SKILL.md`: the skill definition
- `skill://prokn-literature-review/_manifest`: file listing (path, size, sha256)
- `skill://prokn-literature-review/<path>`: supporting files, e.g. `references/inference.md`
  or `references/verification.md`

The PubMed search itself still needs the PubMed MCP connected in the client; the ProKN server does
not proxy it.

## Maintainer rules

- **`description` stays on a single line** in `SKILL.md` frontmatter (single-quoted YAML).
  FastMCP's parser can't read `description: >-` folds and would expose `>-` as the description.
- **Bump `metadata.version`** in `SKILL.md` when the skill changes.
- Keep the reproducibility guidance (section 9) in sync with `prokn-search`: PubMed calls are not
  in ProKN's query log, so the queries and PMIDs are passed in the `literature` argument of
  `create_reproducibility_record`, which records them in their own section.

## Note

The committed `prokn-literature-review.skill` (in the parent `skills/` folder) is built from the
source in this folder (`SKILL.md`, `references/`), so run `./build.sh` and re-commit the new
`.skill` whenever you change those.
