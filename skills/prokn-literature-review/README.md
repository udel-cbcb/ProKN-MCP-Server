# prokn-literature-review

An Agent Skill that teaches a model to do the literature step of the ProKN pipeline: take a
gene/protein/drug/disease set (often from `prokn-search`) or a biological question, search PubMed
through the PubMed MCP, write an evidence-backed review that cites papers by PMID and reconciles them
with the PMIDs ProKN already carries on its edges, and optionally draw cited, confidence-graded
inferences (calibration, mechanism, ABC bridging hypotheses) on top of that evidence.

It has no tool of its own; it describes how to use the connected PubMed and ProKN tools. The graph
tells you *that* things connect; the literature tells you *how strong* that is. See `SKILL.md` for
the pipeline and operating rules. Pairs with `prokn-search` (entity set + graph evidence) and
`prokn-explorer` (network view).

```
skills/
├── prokn-literature-review.skill  # prebuilt bundle (built here by build.sh), committed for install
└── prokn-literature-review/
    ├── SKILL.md                   # the skill definition (what an agent reads)
    ├── README.md                  # this file
    ├── build.sh                   # rebuilds the bundle into ../ (the skills/ dir)
    └── references/                # extra detail, loaded on demand
        ├── pubmed-tools.md        # which PubMed tool answers which need + query building
        ├── synthesis.md           # turning hits into a cited, tiered review; graph reconciliation
        ├── inference.md           # ABC / literature-based discovery, confidence rubric, patterns
        └── pitfalls.md            # recurring mistakes and fixes
```

Status: early (v0.2.2). Core pipeline, reconciliation, and an optional inference layer (confidence
calibration, mechanism, ABC bridging hypotheses, output as a table) are in place; expect it to grow.

## Requirements

The **PubMed MCP** must be connected in your client for the literature search. For the full pipeline
(graph set + evidence reconciliation), the **ProKN MCP server** and the `prokn-search` skill
should also be available. This skill has no script of its own; it drives the connected servers'
tools.

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
- `skill://prokn-literature-review/<path>`: supporting files, e.g. `references/pubmed-tools.md`
  or `references/inference.md`

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

The committed `prokn-literature-review.skill` (in the parent `skills/` folder) is built from the source in
this folder (`SKILL.md`, `references/`), so run `./build.sh` and re-commit the new `.skill` whenever
you change those.
