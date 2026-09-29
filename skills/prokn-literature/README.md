# prokn-literature

An Agent Skill that teaches a model to do the literature step of the ProKN pipeline: take a
gene/protein/drug/disease set (often from `prokn-analysis`) or a biological question, search PubMed
through the PubMed MCP, write an evidence-backed review that cites papers by PMID and reconciles them
with the PMIDs ProKN already carries on its edges, and optionally draw cited, confidence-graded
inferences (calibration, mechanism, ABC bridging hypotheses) on top of that evidence.

It's a methodology layer, not a tool of its own. The graph tells you *that* things connect; the
literature tells you *how strong* that is. See `SKILL.md` for the pipeline and operating rules.
Pairs with `prokn-analysis` (entity set + graph evidence) and `prokn-explorer` (network view).

```
skills/
├── prokn-literature.skill      # prebuilt bundle (built here by build.sh), committed for install
└── prokn-literature/
    ├── SKILL.md                # the skill definition (what an agent reads)
    ├── README.md               # this file
    ├── build.sh                # rebuilds the bundle into ../ (the skills/ dir)
    └── references/             # extra detail, loaded on demand
        ├── pubmed-tools.md     # which PubMed tool answers which need + query building
        ├── synthesis.md        # turning hits into a cited, tiered review; graph reconciliation
        ├── inference.md        # ABC / literature-based discovery, confidence rubric, patterns
        └── pitfalls.md         # recurring mistakes and fixes
```

Status: early (v0.2.1). Core pipeline, reconciliation, and an optional inference layer (confidence
calibration, mechanism, ABC bridging hypotheses, output as a table) are in place; expect it to grow.

## Requirements

The **PubMed MCP** must be connected in your client for the literature search. For the full pipeline
(graph set + evidence reconciliation), the **ProKN MCP server** and the `prokn-analysis` skill
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
zip -r ../prokn-literature.skill SKILL.md references -x '*/.DS_Store'
```

## Installing

- **Cowork:** open the `.skill` file and click "Save skill".
- **Claude Code:** copy the `prokn-literature/` folder into `~/.claude/skills/` (personal) or
  `.claude/skills/` in a repo (project-scoped). No packaging needed there.

## Maintainer rules

- **Bump `metadata.version`** in `SKILL.md` when the skill changes.
- Keep the reproducibility guidance (section 8) in sync with `prokn-analysis`: PubMed calls are not
  in ProKN's query log, so the queries and PMIDs must be recorded by hand and folded into the ProKN
  `create_reproducibility_record` findings when there was a graph step.

## Note

The committed `prokn-literature.skill` (in the parent `skills/` folder) is built from the source in
this folder (`SKILL.md`, `references/`), so run `./build.sh` and re-commit the new `.skill` whenever
you change those.
