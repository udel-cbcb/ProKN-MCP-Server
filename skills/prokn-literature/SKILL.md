---
name: prokn-literature
description: >-
  Literature and inference layer for ProKN: take a gene/protein/drug/disease set (often the output
  of prokn-analysis) or a biological question, search PubMed through the PubMed MCP, write an
  evidence-backed review that reconciles the papers with the PMIDs ProKN already carries, and
  optionally draw cited, confidence-graded inferences from that evidence. Triggers: "literature
  review of these genes/proteins", "what does the literature say about X", "find papers supporting
  this connection", "back these ProKN findings with references", "is this interaction reported in
  the literature", "infer or hypothesize a connection from the papers", or a two-part request that
  first works something out in ProKN and THEN reviews or reasons over the literature on it. Pairs
  with
  prokn-analysis (which supplies the entity set and the graph's own evidence) and needs the PubMed
  MCP connected. NOT for rendering a network (that is prokn-explorer) and NOT for reading graph facts
  alone (that is the ProKN data tools).
compatibility: >-
  Needs the PubMed MCP connected for the literature search, and pairs with prokn-analysis and the
  ProKN MCP server for the entity set and graph evidence. Read-only.
metadata:
  author: University of Delaware, Center for Bioinformatics and Computational Biology
  version: "0.2.1"
  repository: https://research.bioinformatics.udel.edu/ProKN/
  companion_skills: ../prokn-analysis/SKILL.md, ../prokn-explorer/SKILL.md
---

# ProKN literature review

The literature step of the ProKN pipeline. Take a set of entities (genes, proteins, drugs,
diseases, sites) or a biological question, search PubMed, and write a short evidence-backed review
that says what the literature actually supports, cites it by PMID, and lines it up against the
evidence ProKN already stores on its edges.

The point is the pairing: the graph tells you *that* two things are connected and gives a curated
PMID or a source database; the literature tells you *how strong* that is, whether it still holds,
and what the graph is missing. This skill does the second half.

## 1. What this is and when to use it

Use it when the user wants the literature behind a result: papers supporting a connection, a review
of what's known about a gene or drug, or a check on whether a ProKN edge is backed by more than one
report. It is the natural closing step after `prokn-analysis` produces a gene/entity set.

Do not use it to render a network (that's `prokn-explorer`) or to read graph facts on their own
(that's the ProKN data tools). If the user only wants raw graph relationships, stay in
`prokn-analysis`.

## 2. The pipeline (who does what)

1. **`prokn-analysis`** resolves the question into real entities, pulls the relationships, and hands
   over a gene/entity set plus the graph's own evidence (PMIDs and source databases on each edge).
2. **This skill** turns that set into targeted PubMed searches, retrieves and reads the relevant
   papers, and writes the review.
3. **Reconciliation** is the ProKN-specific part: compare what the literature says to the PMIDs the
   graph already carries (section 6), so the user sees agreement, new support, and gaps.

If the user comes straight here with a plain question and no prior analysis, resolve the entities
first (a quick `search_entities` in ProKN, or accept the user's terms) before searching PubMed.

## 3. Operating rules (non-negotiable)

- **Search on real entities, not loose words.** Turn the set into specific query terms: gene
  symbols and their aliases, drug names, disease terms. A vague query returns a vague review.
- **Cite every claim with PMIDs.** Each statement in the review points to the article(s) it came
  from. If you can't cite it, don't assert it.
- **Reconcile with the graph.** For a connection ProKN already reports, say whether the literature
  agrees, adds new support, or conflicts (section 6). Don't present the graph edge and the papers as
  if they were unrelated.
- **Read at least the abstract before citing.** Cite from what the article says, not from its title.
  Use full text only when the tool provides it and copyright allows (section 7).
- **Rank the evidence.** Primary experimental report > review/meta-analysis > preprint or
  computational prediction. Say which tier a claim rests on; don't state a single mouse study as
  settled fact.
- **Declare what you skipped.** If you only searched one branch (one gene, one direction, English
  only, a date cutoff), say so in one line. A silent omission reads as "covered everything."
- **Be honest about gaps.** If the search returns little or nothing, report that plainly instead of
  padding the review or implying the connection is proven.
- **Never invent a PMID or a finding.** No fabricated identifiers, no merging several papers into
  one citation, no claims the papers don't make.
- **Label inferences, don't smuggle them.** Anything you conclude beyond what a paper states is an
  inference: mark it as one, ground it in the PMIDs it rests on, and grade its confidence
  (section 8). Never present an inference as established fact.
- **Read-only.** Searching and reading only. No writes anywhere.

## 4. The PubMed tools (reference, don't restate)

Point at the PubMed MCP's own tools; don't re-document their parameters here. By concern:

- Find papers: `search_articles` (the main entry), `find_related_articles` (expand from a good hit).
- Read a paper: `get_article_metadata` (title, abstract, journal, year, authors), `get_full_text_article` (when available).
- Identifiers: `lookup_article_by_citation`, `convert_article_ids` (PMID / PMCID / DOI).
- Rights: `get_copyright_status` before quoting or pulling full text.

A map of which tool answers which need, and how to build good queries, is in
`references/pubmed-tools.md`.

## 5. Workflow (run the steps the question needs)

1. **Frame.** Identify the entities and the exact claim(s) the user wants backed. If it came from a
   `prokn-analysis` run, carry over the entity set and the edge PMIDs.
2. **Build queries.** One targeted `search_articles` per claim or entity pair, using symbols plus
   aliases and specific terms. Widen or narrow based on what comes back (`references/pubmed-tools.md`).
3. **Retrieve and read.** Pull `get_article_metadata` for the top hits; read abstracts; use
   `find_related_articles` to round out a thin result and `get_full_text_article` where it's allowed
   and needed.
4. **Reconcile.** Line the papers up against the graph's PMIDs and source databases (section 6).
5. **Synthesize.** Write the review grouped by claim or entity, each point cited, each tier labeled
   (`references/synthesis.md`).
6. **Infer (optional).** If the user wants more than a summary, draw cited, confidence-graded
   inferences on top of the evidence (section 8): calibrate confidence, propose a mechanism, or
   offer a bridging hypothesis. Skip it for a plain "what do the papers say".
7. **Report and record.** Give the review (and any inferences) with citations, then record the run
   (section 9), listing the exact queries and the PMIDs used so someone else can rerun it.

## 6. Reconciling graph evidence with the literature

ProKN edges already carry provenance: a curated PMID, or a source database (`SAB` / `dcc`), plus
measurement values on quantitative edges. Put that next to the literature and sort each connection
into one of:

- **Graph and literature agree.** The edge's PMID (or a new paper) supports it. Strongest case; say
  so and cite both.
- **Graph-only.** ProKN has the edge with a PMID, but your PubMed search didn't surface it. Still
  valid evidence; note that it rests on the curated edge and the search didn't independently expand
  it.
- **Literature-only.** Papers support a connection the graph doesn't have. Flag it as new or
  extending, not as already in ProKN.
- **Conflicting.** The literature disputes or fails to replicate what the edge asserts. Report the
  conflict with both citations; don't quietly drop either side.

Keep the graph's PMIDs and the search's PMIDs distinguishable in the write-up so the reader can tell
curated evidence from what you found.

## 7. Evidence, citations, and full text

- Label the tier of each claim: curated primary experiment > review/meta-analysis > preprint or
  computational prediction. ProKN edge PMIDs are usually curated primary evidence; treat a
  perturbation signal or a prediction as weaker.
- Prefer abstracts for synthesis. Pull full text only when `get_full_text_article` provides it and
  `get_copyright_status` allows; quote sparingly and attribute.
- Report PMIDs (and DOIs when handy). Don't merge separate papers into one citation, and don't
  invent identifiers.
- When the literature is thin, one honest sentence beats a padded paragraph.

## 8. Inference (optional): hypotheses from the evidence

Retrieval and reconciliation say what the papers report. This step draws conclusions *on top of*
that evidence, which is where the pipeline earns the name. It is optional: use it when the user wants
more than a summary (a confidence call, a mechanism, a new hypothesis). Everything here is grounded
in PMIDs, labeled as inference, and confidence-graded. Full method in `references/inference.md`.

Kinds of inference, weakest to strongest in what they add:

- **Confidence calibration.** Judge how well-established a connection is from the evidence behind it:
  how many studies, how independent, what tier. "One preprint" and "three independent primary
  studies" are different claims. This is the natural upgrade to reconciliation: a ChEMBL-only edge
  with strong primary literature becomes high-confidence; a LINCS-only signal with no paper stays
  low.
- **Mechanistic inference.** From several papers, infer *why* a connection holds (the pathway or
  binding mode) when no single edge or paper states it outright. Synthesis across sources, cited.
- **Bridging hypotheses (ABC / literature-based discovery).** When the evidence has A-B and B-C but
  no A-C, propose A-C as a *testable hypothesis*, showing both halves of the chain. This can surface
  links ProKN doesn't have. It is a hypothesis, never a fact.
- **Gap and contradiction inference.** Infer where the graph is missing something the literature
  supports, or weigh conflicting papers into a current-consensus call and say how firm it is.

Rules (non-negotiable):

- **Label every inference as an inference.** The reader must never confuse "the graph says" / "the
  papers show" / "this suggests". Mark each one (e.g. start it with "Inference:").
- **Show the evidence chain.** Every inference names the PMIDs it rests on; a bridging hypothesis
  shows the A-B and B-C citations. No cited chain, no inference.
- **Grade the confidence** (high / moderate / low / speculative) from tier and independence, and say
  what would raise it. Single-study, single-species, or preprint-only stays low.
- **Anchor to what the abstracts say**, not to titles or a paper's mere existence. If the abstract
  doesn't support the step, drop it.
- **Hypotheses stay hypotheses.** Bridging and gap inferences are testable proposals, phrased as
  such, never presented as established or as already in ProKN.
- **Thin evidence yields no inference.** "Insufficient evidence to infer" is a valid, preferred
  output over a confident guess.

Present the inferences as a **table** (one row each: inference, kind, confidence, basis PMIDs, and
what would raise confidence or test it), kept separate from the cited review above it. The ABC model,
the confidence rubric, the table columns, and worked patterns are in `references/inference.md`.

## 9. Reproducibility

PubMed calls run on a different MCP server than ProKN, so they are NOT in ProKN's query log. The
record tool has a `literature` field for exactly this:

- Keep the ProKN reproducibility record for the graph half: call `reset_query_log` before the
  analysis and `create_reproducibility_record` at the end. Pass the exact PubMed queries you ran and
  the PMIDs you cited in the `literature` argument (it becomes a "Literature (PubMed)" section in the
  record); the graph findings go in `findings` as usual.
- If there was no ProKN step (a plain literature question), still list the queries and the returned
  PMIDs in the reply so the review can be rerun.

The queries and PMIDs are the reproducible core; a review nobody can retrace isn't much use.

## 10. Worked example

"Which kinases downregulated by alpelisib have literature support, and how does it line up with
ProKN?"

1. `prokn-analysis` resolves alpelisib, pulls the LINCS-downregulated sites and their kinases, and
   hands over the kinase set with the edge evidence.
2. For each kinase, `search_articles("alpelisib AND <kinase> AND phosphorylation")` (plus aliases);
   read the top abstracts with `get_article_metadata`.
3. Reconcile: kinases whose edges carry a curated PMID that the search corroborates (agree),
   LINCS-only signals with no paper yet (graph-only / weak tier), and any kinase with papers but no
   ProKN edge (literature-only).
4. Write the review grouped by kinase, each point cited and tiered, noting sites with no literature.
5. (Optional) Inference: calibrate confidence per kinase (strong primary support vs LINCS-only), and
   if the papers give A-B and B-C without A-C, offer one bridging hypothesis, labeled and cited
   (section 8). Lay the inferences out in a table.
6. `create_reproducibility_record(question=..., findings=<graph findings>, literature=<the PubMed
   queries and cited PMIDs>, skills="prokn-analysis v0.3.0, prokn-literature v0.2.1")`; give the user
   the saved path plus a short summary.

## 11. References (read on demand)

- **`references/pubmed-tools.md`**: which PubMed tool answers which need, and how to build queries.
- **`references/synthesis.md`**: turning hits into a cited, tiered review, and grouping by claim.
- **`references/inference.md`**: the ABC / literature-based-discovery model, the confidence rubric,
  and worked inference patterns. Read before drawing any inference.
- **`references/pitfalls.md`**: recurring mistakes (bad queries, title-only citing, ignoring the
  graph's PMIDs, over-claiming inferences). Skim before finalizing.

## 12. Gotchas

The full list is in `references/pitfalls.md`. The ones you'll hit most: searching loose words
instead of resolved entities, citing from titles without reading the abstract, treating a single
study or a preprint as settled, presenting an inference as fact, and reporting the papers without
lining them up against the PMIDs ProKN already carries.
