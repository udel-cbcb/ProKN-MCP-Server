---
name: prokn-literature-review
description: 'Draw inferences from ProKN graph evidence, then test each one against PubMed: pull the relevant edges for a gene, protein, drug or disease set (often from prokn-search), state cited, confidence-graded inferences (mechanisms, bridging hypotheses, edge strength), and search PubMed (plus Paperclip, when connected, for preprints, trials and FDA documents) for papers that support or contradict each, ending in a verdict table. Use for "what can we infer from ProKN about X, and does the literature back it", "hypothesize a connection and check the papers", "back these ProKN findings with references", "is this inferred link reported in the literature", or a request that works something out in ProKN and THEN checks it against the literature. NOT for rendering a network (prokn-explorer) or reading graph facts alone (prokn-search).'
compatibility: >-
  Needs the ProKN MCP server for the graph evidence and the PubMed MCP for the literature check.
  The Paperclip MCP (GXL) is optional: a second source for preprints, trials, FDA documents, and
  line-numbered full text. Pairs with prokn-search, which can supply the entity set and edges.
  Read-only.
metadata:
  author: University of Delaware, Center for Bioinformatics and Computational Biology
  version: "0.5.0"
  repository: https://research.bioinformatics.udel.edu/ProKN/
  companion_skills: ../prokn-search/SKILL.md, ../prokn-explorer/SKILL.md
---

# ProKN literature review

Draw inferences from what the ProKN graph shows, then test them against the literature: PubMed,
plus Paperclip when it's connected. Write the inferences before any literature search, so the
papers test them instead of shaping them.

## 1. When to use it

Use it when the user wants conclusions drawn from ProKN and checked against published work: what a
set of kinase-site edges implies about a drug, whether a path between two proteins suggests a
mechanism, whether a ProKN edge holds up, or which graph hypotheses are worth testing.

Not for rendering a network (`prokn-explorer`) or reporting graph facts without conclusions
(`prokn-search`). If the user only wants papers on a topic, say this skill reasons from the graph
first, and offer to pull the graph evidence.

## 2. The pipeline

1. **Graph evidence:** resolve the entities and pull the edges, with provenance (section 4).
2. **Inferences:** from the graph alone, each with its edges and a prior confidence (section 5).
3. **Literature check:** for each inference, search for and against it, quote and link the
   deciding sentences, and give a verdict and final confidence (sections 6 and 7).
4. **Output:** a verdict table and a short summary (section 8), then the reproducibility record
   (section 9).

## 3. Operating rules

- **Infer first.** Write every inference, with its ProKN basis and prior, before the first
  literature search. Don't reshape it to fit the papers; new ideas go in a "literature leads" line.
- **Ground every inference in edges** and their provenance (PMID, or source database such as
  `SAB` / `dcc`). No graph basis, no inference.
- **Search both directions.** Look for papers that dispute each inference, not only support it.
- **Don't count an edge's own PMID as support.** It's part of the graph basis.
- **Link every citation to its sentence.** Each supporting or contradicting paper is backed by a
  sentence copied word for word, and its identifier links straight to that sentence. No such
  sentence, no support.
- **Read abstracts first, then the full text of the papers that decide a verdict,** at most two
  per inference. Say when a deciding paper had no full text.
- **Rank the evidence:** primary study > review or meta-analysis > preprint or computational
  prediction. One mouse study or preprint settles nothing.
- **Re-judge Paperclip's output.** Its `evidence` labels are a first pass. Drop retracted papers,
  and don't count a trial registration as evidence a drug works. Without Paperclip, run on PubMed
  alone and say so.
- **Keep every inference in the table,** including contradicted ones and those with no
  literature. "No literature found" is not a refutation.
- **Declare what you skipped** (an entity, branch, direction, or date range) in one line.
- **Never invent a PMID or a finding,** or merge several papers into one citation.
- **Read-only.** With Paperclip, use only its search, `evidence`, lookup, and reading tools, not
  its repo, clipboard, upload, or sharing tools.

## 4. Step 1: gather the graph evidence

If `prokn-search` is available, follow its search flow from "Start" through "Cite" (steps 0 to 5
of its section 4) and skip its "Visualize" and "Report and record" steps: this skill saves one
record covering both halves. If it already ran in this conversation, reuse its entities and edges.

Otherwise, call `reset_query_log`, resolve the entities with `search_entities`, and pull the edges
the question needs (drug targets, kinase-site edges, paths, shared pathways or complexes).

For each edge, keep the two entities, the relationship, and its provenance: PMIDs if present,
otherwise the source database, plus any measurement (LINCS `log2Ratio`, DrugCentral IC50).

## 5. Step 2: infer from the graph

The kinds: **edge strength** (how well one edge's provenance backs it), **mechanism** (a path
suggests how one entity affects another), **bridge** (A-B and B-C but no A-C; B must be the same
node), **shared context** (shared pathways, complexes, or GO terms), and **gap** (an expected edge
is missing).

For each inference, write one testable sentence, its kind, its edges with provenance, and a prior
confidence from the graph alone: high, moderate, low, or speculative. Patterns and the prior
rubric are in `references/inference.md`.

## 6. Step 3: check each inference in the literature

One inference at a time, each with its own searches and its own list of papers:

1. **PubMed support query:** the paired entities plus the mechanism word, e.g.
   `alpelisib AND AKT1 AND phosphorylation`.
2. **PubMed counter query:** the same pair with terms like resistance, reactivation, no effect,
   or not required.
3. **Paperclip, if connected:** `evidence` with the inference as the claim (both sides at once).
   For a drug inference, also `search` the `trials` and `fda` sources.
4. **Merge:** match papers found by both sources by PMC ID, then DOI, then title, and count each
   once.
5. **Read and sort:** PubMed abstracts from `get_article_metadata`, Paperclip passages as
   returned. Sort each paper by what it says (supports, contradicts, partly addresses), note its
   tier, and copy the deciding sentence word for word.
6. **Full text for the deciding papers:** the one or two primary studies the verdict rests on,
   both sides of a Mixed verdict, or an abstract that leaves out direction or conditions. Try
   Paperclip first, then PubMed's `get_full_text_article`. Re-sort and re-quote from the Results.
7. **Check the edge's own PMIDs** say what the edge claims. They stay in the ProKN basis.

The details of each step (sources, quoting, linking, tiered reading, evidence tiers) are in
`references/verification.md`.

## 7. Verdicts and confidence

- **Supported:** at least one primary study supports it, and no primary study disputes it.
- **Mixed:** primary studies on both sides. Say what differs (cell type, dose, species, time
  point), from the full text of the papers on each side.
- **Contradicted:** primary evidence disputes it, and nothing comparable supports it.
- **No literature found:** nothing beyond the graph addresses it. It stays a hypothesis.

The final confidence starts from the prior. Supported by two or more independent primary studies:
up one level, to at most high. Supported by one: unchanged, though speculative may rise to low.
Mixed: down one level. Contradicted: down to low or speculative. No literature found: unchanged.
Say in one clause what would change the grade.

## 8. Output

One row per inference, in the order written:

| # | Inference | Kind | ProKN basis | Supporting | Contradicting | Verdict | Confidence | To test or strengthen |
|---|-----------|------|-------------|------------|---------------|---------|------------|-----------------------|
| 1 | Lapatinib inhibits EGFR | edge strength | lapatinib-EGFR (DrugCentral, Kd) | [PMID 22178589](https://pubmed.ncbi.nlm.nih.gov/22178589/#:~:text=Lapatinib%2C%20an%20inhibitor%20of%20HER2,lines%20than%20trastuzumab) (primary, [DOI](https://doi.org/10.1053/j.gastro.2011.12.005)) | none found | Supported | moderate | an independent primary study |

- **Each cited paper:** its identifier, linked to its quoted sentence, then the tier and a DOI
  link. Add "full text" if the quote came from the full text, or "abstract only" for a deciding
  paper whose full text couldn't be read.
- **Papers without a PMID:** by DOI (preprints), NCT number (trials), or plain path (FDA
  documents).
- Separate several papers with semicolons, and write "none found" rather than leaving a cell blank.
- How to build the links is in `references/verification.md`. Quotes aren't listed under the
  table; the record keeps them.

Then a summary of three to five sentences: which inferences held up, were contradicted, or remain
hypotheses; which deciding papers were read in full; which sources were searched; any retracted
papers that came up; and what wasn't covered. Then one line of literature leads, marked untested.

## 9. Reproducibility record

PubMed and Paperclip calls aren't in ProKN's query log. At the end, call
`create_reproducibility_record` with:

- `findings`: each inference with its ProKN basis, verdict, and final confidence.
- `literature`: for each inference, the exact PubMed queries; each Paperclip call (claim or query,
  `source`, and result ID such as `s_467e0914`); and every cited paper with its identifier, which
  source found it, its quote word for word, the section and line if the quote is from the full
  text, and its reading depth. Include papers that only partly addressed an inference, since they
  aren't in the table.
- `skills`: e.g. `"prokn-search v0.3.0, prokn-literature-review v0.5.0"`.

Give the user the saved path and a one- or two-line summary.

## 10. Worked example

"What does ProKN suggest about how alpelisib affects kinase signaling, and does the literature back
it?"

1. Follow `prokn-search` through "Cite": `reset_query_log()`, `search_entities("alpelisib")`,
   `get_phosphosites_regulated_by_perturbagen(perturbagen="alpelisib", direction="down")`, then
   `get_proteins_catalyzing_sites` for the kinases.
2. Infer before searching, e.g. "Alpelisib may reduce signaling through kinase K, since it lowers
   several sites K catalyzes" (mechanism; basis: the LINCS and kinase-site edges; prior: low,
   since LINCS edges are measurements).
3. For each inference, query PubMed with `alpelisib AND <kinase> AND phosphorylation` and
   `alpelisib AND <kinase> AND (resistance OR reactivation)`. If Paperclip is connected, call
   `evidence` on the inference and `search` `trials` for alpelisib. Merge, read, and quote, then
   read the Results of the one or two deciding papers.
4. Fill in the table with linked citations, write the summary, and call
   `create_reproducibility_record`.

## 11. References (read on demand)

- `references/inference.md`: inference patterns, the prior-confidence rubric, and the
  spurious-bridge check. Read before step 2.
- `references/verification.md`: the details of step 3: sources and merging, quoting, linking each
  paper to its quote, tiered reading, the circularity rule, and evidence tiers.
- `references/pubmed-tools.md`: the PubMed tools and building support and counter queries.
- `references/paperclip-tools.md`: the Paperclip tools, re-judging `evidence` output, preprints,
  trials and FDA documents, and the call budget.
- `references/pitfalls.md`: common mistakes. Skim before finalizing.
