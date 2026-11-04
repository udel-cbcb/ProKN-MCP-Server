# prokn-literature-review

An Agent Skill that draws inferences from the ProKN graph and tests them against the literature.
It pulls the ProKN edges for a gene, protein, drug, or disease set (often via `prokn-search`),
writes confidence-graded inferences from them (edge strength, mechanisms, A-B-C bridges, shared
context, gaps) before any literature search, then searches PubMed, plus Paperclip when it's
connected, for papers that support or contradict each one. The result is a verdict table
(Supported, Mixed, Contradicted, No literature found) whose citations link to the exact sentences
behind them, a short summary, and a reproducibility record.

It has no tools of its own; it drives the connected ProKN, PubMed, and Paperclip tools. See
`SKILL.md` for the method. Pairs with `prokn-search` (entity set and graph evidence) and
`prokn-explorer` (network view).

```
skills/
├── prokn-literature-review.skill  # prebuilt bundle (built here by build.sh), committed for install
└── prokn-literature-review/
    ├── SKILL.md                   # the skill definition (what an agent reads)
    ├── README.md                  # this file
    ├── build.sh                   # rebuilds the bundle into ../ (the skills/ dir)
    └── references/                # extra detail, loaded on demand
        ├── inference.md           # inference patterns from graph edges, prior confidence
        ├── verification.md        # sources, quoting, linking, tiered reading, evidence tiers
        ├── pubmed-tools.md        # PubMed tools and query building
        ├── paperclip-tools.md     # optional Paperclip source: tools, evidence output, trials/FDA
        └── pitfalls.md            # common mistakes
```

## Status: early (v0.5.0)

- **0.5.0:** Paperclip (GXL) as an optional second source (preprints, trial registries, FDA
  documents, the claim-level `evidence` search, line-numbered full text), merged with PubMed so
  each paper counts once. Each citation links to its quoted sentence with a text-fragment URL,
  which opens the paper with that sentence highlighted.
- **0.4.0:** every cited paper is backed by a sentence copied word for word, and a paper with no
  such sentence doesn't count. Tiered reading: abstracts for every paper, full text for the one or
  two papers per inference that decide its verdict.
- **0.3.0:** inferences come from the graph first, and the literature tests them.

## Requirements

The **ProKN MCP server** (graph evidence) and the **PubMed MCP** (literature check) must be
connected in your client. The `prokn-search` skill helps gather the graph evidence.

**Optional: Paperclip (GXL).** Add a custom connector pointing at `https://paperclip.gxl.ai/mcp`
and sign in with a GXL account (in the Claude apps: Customize → Connectors → Add custom connector;
custom connectors need a paid plan). Setup for other clients is at
[paperclip.gxl.ai/install](https://paperclip.gxl.ai/install). Rate limits are per account, and the
free tier covers this skill's call pattern.

## Packaging it as a .skill bundle

A `.skill` file is a zip of this folder's contents, with `SKILL.md` at the top level. From inside
this folder, run `./build.sh`, or by hand:

```bash
zip -r ../prokn-literature-review.skill SKILL.md references -x '*/.DS_Store'
```

## Installing

- **Cowork:** open the `.skill` file and click "Save skill".
- **Claude Code:** copy the `prokn-literature-review/` folder into `~/.claude/skills/` (personal) or
  `.claude/skills/` in a repo (project-scoped).

## Via the ProKN MCP server

No install needed: the server exposes this skill as MCP resources from the repo's `skills/` folder
(see the root README's Agent Skills section), and as the `prokn-literature-review` MCP prompt:

- `skill://prokn-literature-review/SKILL.md`: the skill definition
- `skill://prokn-literature-review/_manifest`: file listing (path, size, sha256)
- `skill://prokn-literature-review/<path>`: supporting files, e.g. `references/verification.md`

The PubMed search still needs the PubMed MCP connected in the client, and the optional Paperclip
source needs the Paperclip MCP; the ProKN server proxies neither.

## Maintainer rules

- **`description` stays on a single line** in `SKILL.md` frontmatter (single-quoted YAML).
  FastMCP's parser can't read `description: >-` folds and would expose `>-` as the description.
- **Bump `metadata.version`** in `SKILL.md` when the skill changes.
- **Keep the reproducibility guidance (section 9) in sync with `prokn-search`.** PubMed and
  Paperclip calls aren't in ProKN's query log, so queries, Paperclip result IDs, and cited papers
  go in the `literature` argument of `create_reproducibility_record`.
- **Paperclip tool names** in `references/paperclip-tools.md` are the MCP server's own (`evidence`,
  `search`, `lookup`, `ls`, `cat`, `grep`, `results`, `merge`). If GXL renames them, update that
  file.
- **Rebuild the bundle.** The committed `prokn-literature-review.skill` is built from this folder,
  so run `./build.sh` and re-commit it whenever `SKILL.md` or `references/` change.
