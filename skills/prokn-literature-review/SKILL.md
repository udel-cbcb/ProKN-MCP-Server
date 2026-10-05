---
name: prokn-literature-review
description: 'Draw inferences from ProKN graph evidence, then test each one against PubMed: pull the relevant edges for a gene, protein, drug or disease set (often from prokn-search), state cited, confidence-graded inferences (mechanisms, bridging hypotheses, edge strength), and search PubMed for papers that support or contradict each, ending in a verdict table. Use for "what can we infer from ProKN about X, and does the literature back it", "hypothesize a connection and check the papers", "back these ProKN findings with references", "is this inferred link reported in the literature", or a request that works something out in ProKN and THEN checks it against the literature. NOT for rendering a network (prokn-explorer) or reading graph facts alone (prokn-search).'
compatibility: >-
  Needs the ProKN MCP server for the graph evidence and the PubMed MCP for the literature check.
  Pairs with prokn-search, which can supply the entity set and edges. Read-only.
metadata:
  author: University of Delaware, Center for Bioinformatics and Computational Biology
  version: "0.3.0"
  repository: https://research.bioinformatics.udel.edu/ProKN/
  companion_skills: ../prokn-search/SKILL.md, ../prokn-explorer/SKILL.md
---

# ProKN literature review

Start from what the ProKN graph shows, reason from it to inferences, and then use PubMed to test
those inferences. The graph supplies the connections and their provenance; the inferences say what
those connections imply; the literature check says whether published work supports, disputes, or
is silent on each implication.

The order matters. Inferences are written down from the graph evidence before any PubMed search,
so the papers test them instead of shaping them.

## 1. What this is and when to use it

Use it when the user wants conclusions drawn from ProKN and checked against the literature: what a
set of kinase-site edges implies about a drug, whether a path between two proteins suggests a
mechanism, whether a ProKN edge holds up, or which hypotheses from the graph are worth testing.

Do not use it to render a network (that's `prokn-explorer`) or to report graph facts without
drawing conclusions (that's `prokn-search`). If the user only wants papers on a topic with no ProKN
step, say that this skill reasons from the graph first, and offer to pull the graph evidence.

## 2. The pipeline

1. **Graph evidence.** Resolve the entities and pull the edges that bear on the question, with
   their provenance (section 4). `prokn-search` can do this and hand over the set.
2. **Inferences.** From the graph evidence alone, state what it implies, each inference tied to
   the edges it rests on and given a prior confidence (section 5).
3. **Literature check.** For each inference, search PubMed for supporting and contradicting work,
   read the abstracts, and give a verdict and a final confidence (sections 6 and 7).
4. **Output.** A verdict table and a short summary (section 8), then the reproducibility record
   (section 9).

## 3. Operating rules

- **Infer from the graph first.** Write every inference, with its ProKN basis and prior
  confidence, before the first PubMed search. Don't reshape an inference to fit the papers
  afterwards. If the papers suggest something new, list it separately as a literature lead.
- **Ground every inference in edges.** Each one names the ProKN edges it comes from and their
  provenance (PMID, or source database such as `SAB` / `dcc`). Without a graph basis, it isn't an
  inference for this skill.
- **Search both directions.** For each inference, look for papers that dispute it as well as
  papers that support it (section 6). Looking only for support makes every inference look good.
- **Don't count the inference's own source as support.** A PMID already on an edge the inference
  was built from is part of the graph basis, not independent confirmation.
- **Read at least the abstract before citing.** Cite from what the article says, not its title.
  Use full text only when the tool provides it and copyright allows.
- **Rank the evidence.** Primary experimental study > review or meta-analysis > preprint or
  computational prediction. A single mouse study or preprint doesn't settle anything.
- **Keep every inference in the output.** Contradicted inferences and those with no literature
  stay in the table with their verdicts; don't drop the ones that didn't hold up.
- **No literature is not a refutation.** If nothing addresses an inference, the verdict is "No
  literature found" and it stays a hypothesis.
- **Declare what you skipped.** Name any entity, branch, direction, or date range you didn't
  check, in one line.
- **Never invent a PMID or a finding.** No fabricated identifiers, no merging several papers into
  one citation, no claims the papers don't make.
- **Read-only.** Searching and reading only. No writes anywhere.

## 4. Step 1: gather the graph evidence

Resolve the entities with `search_entities`, then pull the edges the question needs (drug targets,
kinase-site edges, paths between proteins, shared pathways or complexes). If `prokn-search` already
ran, reuse its entities and edges instead of querying again. Keep, for each edge:

- the two entities and the relationship,
- its provenance: PMIDs if present, otherwise the source database, plus any measurement value
  (LINCS `log2Ratio`, DrugCentral IC50).

Call `reset_query_log` before the first ProKN call so the record covers only this run.

## 5. Step 2: infer from the graph

State what the edges imply. The common kinds:

- **Edge strength.** How well a single connection is backed by its own provenance. A curated PMID
  is stronger than a database assertion, which is stronger than a measurement or tox signal.
- **Mechanism.** A path in the graph suggests how one entity affects another (a drug inhibits a
  kinase that phosphorylates a site on a protein in a pathway).
- **Bridge (A-B-C).** The graph has A-B and B-C but no A-C, which suggests A may relate to C
  through B. Check that B is the same node in both edges.
- **Shared context.** Input proteins share pathways, complexes, or GO terms, which suggests a
  functional link between them.
- **Gap.** A connection you'd expect from the rest of the graph is missing.

For each inference, write one testable sentence, its kind, the edges it rests on (with
provenance), and a prior confidence from the graph alone: high, moderate, low, or speculative.
Bridges and gaps start at speculative or low. Patterns, the prior-confidence rubric, and the
spurious-bridge check are in `references/inference.md`.

## 6. Step 3: check each inference in PubMed

For each inference, in order:

1. **Support query.** Pair the key entities with the mechanism word, using symbols and aliases,
   e.g. `alpelisib AND AKT1 AND phosphorylation`.
2. **Counter query.** Look for work that disputes it, e.g. the same pair with terms like
   resistance, reactivation, no effect, or not required. Also read the support results for
   findings that go the other way.
3. **Read and sort.** Pull abstracts with `get_article_metadata`. For each relevant paper, note
   whether it supports, contradicts, or only partly addresses the inference, and its tier.
4. **Check the edge's own PMIDs.** Confirm they say what the edge claims, but keep them in the
   graph basis, not in the support column.

Query building, the counter-evidence patterns, and the reading order are in
`references/pubmed-tools.md`. The full verification method is in `references/verification.md`.

## 7. Verdicts and confidence

Give each inference one verdict:

- **Supported:** at least one primary study directly supports it, and nothing serious disputes it.
- **Mixed:** both supporting and contradicting primary evidence.
- **Contradicted:** primary evidence disputes it, and nothing comparable supports it.
- **No literature found:** nothing addresses it. It stays a hypothesis.

Then set a final confidence (high, moderate, low, speculative) from the prior and the verdict. A
supported inference with independent primary studies can rise; a contradicted one falls; one with
no literature keeps its prior. Say in one clause what would change the grade. The rubric for
combining them is in `references/verification.md`.

## 8. Output

A Markdown table, one row per inference, then a short summary.

| # | Inference | Kind | ProKN basis | Supporting PMIDs | Contradicting PMIDs | Verdict | Confidence | To test or strengthen |
|---|-----------|------|-------------|------------------|---------------------|---------|------------|-----------------------|

- **ProKN basis:** the edges, with their PMIDs or source database.
- **Supporting / Contradicting PMIDs:** papers from the search, with the tier noted (primary,
  review, preprint). Leave a cell as "none found" rather than blank.

The summary is three to five sentences: which inferences held up, which were contradicted, which
remain untested hypotheses, and anything the search couldn't cover. Literature leads (ideas the
papers raised that weren't among the inferences) go in one line after the summary, marked as
untested.

## 9. Reproducibility

PubMed calls run on a different MCP server, so they are not in ProKN's query log. At the end, call
`create_reproducibility_record` with:

- `findings`: the inferences, each with its ProKN basis, verdict, and final confidence.
- `literature`: for each inference, the exact support and counter queries you ran and the PMIDs
  you cited.
- `skills`: e.g. `"prokn-search v0.3.0, prokn-literature-review v0.3.0"`.

Give the user the saved file path plus a one- or two-line summary.

## 10. Worked example

"What does ProKN suggest about how alpelisib affects kinase signaling, and does the literature back
it?"

1. `reset_query_log()`, then `search_entities("alpelisib")` and
   `get_phosphosites_regulated_by_perturbagen(perturbagen="alpelisib", direction="down")` for the
   LINCS P100 sites it lowers, then `get_proteins_catalyzing_sites` for their kinases.
2. Inferences from the graph, before any search. For example: "Alpelisib reduces signaling through
   kinase K, since it lowers several sites K catalyzes" (mechanism; basis: the LINCS edges and the
   kinase-site edges with their PMIDs; prior: low, because LINCS edges are measurements). Write one
   such row per kinase worth testing.
3. For each inference, run the support query (`alpelisib AND <kinase> AND phosphorylation`) and a
   counter query (`alpelisib AND <kinase> AND (resistance OR reactivation)`), and read the
   abstracts.
4. Fill in the verdicts and final confidence, keeping contradicted and untested rows in the table.
5. `create_reproducibility_record(question=..., findings=<inferences and verdicts>,
   literature=<queries per inference and cited PMIDs>,
   skills="prokn-search v0.3.0, prokn-literature-review v0.3.0")`; give the user the saved path.

## 11. References (read on demand)

- `references/inference.md`: inference patterns from graph edges, the prior-confidence rubric, and
  the spurious-bridge check. Read before step 2.
- `references/verification.md`: testing an inference in PubMed, the circularity rule, verdicts,
  combining prior and verdict into final confidence, and the output table.
- `references/pubmed-tools.md`: which PubMed tool answers which need, and building support and
  counter queries.
- `references/pitfalls.md`: recurring mistakes. Skim before finalizing.

## 12. Gotchas

The full list is in `references/pitfalls.md`. The ones you'll hit most: searching PubMed before the
inferences are written down, counting an edge's own PMID as independent support, searching only
for support, dropping inferences that didn't hold up, and treating "no literature found" as a
refutation.
