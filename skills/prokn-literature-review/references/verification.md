# Checking inferences against the literature

How to test each graph inference in PubMed, decide a verdict, and set the final confidence. The
inferences are already written down (`inference.md`); this step tests them and doesn't rewrite
them.

## One inference at a time

For each inference, run its own searches and keep its own list of papers. Searching several
inferences in one broad query makes it unclear which paper bears on which claim.

1. **Support query:** the key entities paired, plus the mechanism word (see `pubmed-tools.md`).
2. **Counter query:** the same pair with terms that would surface disagreement: resistance,
   reactivation, compensation, no effect, not required, independent of.
3. **Read the abstracts** of the plausible hits from both queries with `get_article_metadata`.
4. **Sort each relevant paper** into supports, contradicts, or partly addresses (a related
   finding in another cell type, species, or direction), and note its tier.

A paper found by the support query can still contradict the inference, and the other way round.
Sort by what the abstract says, not by which query found it.

## The circularity rule

The PMIDs on the edges an inference was built from are part of its ProKN basis. Check that they
say what the edge claims, but don't list them as supporting PMIDs. Only papers that add something
beyond the graph count as independent support. If the search finds nothing but the edge's own
PMID, the verdict is "No literature found" beyond the graph.

## Evidence tiers

- **Primary experimental study** (a direct experimental result): strongest.
- **Review or meta-analysis:** useful for consensus, but secondary. When a review supports an
  inference, look for the primary paper it cites and cite that.
- **Preprint or computational prediction:** weakest. Note it, but it can't make a verdict
  "Supported" on its own.

Don't count several reviews of the same primary result as several sources.

## Verdicts

- **Supported:** at least one primary study directly supports the inference, and no primary study
  disputes it.
- **Mixed:** primary studies on both sides. Say what differs between them (cell type, dose,
  species, time point) if the abstracts show it.
- **Contradicted:** primary evidence disputes the inference, and nothing comparable supports it.
- **No literature found:** nothing beyond the graph addresses the inference. This is not a
  refutation; the inference stays a hypothesis.

Papers that only partly address an inference can move it from "No literature found" to a weak
"Supported" or "Mixed" only when the abstract makes the connection explicit.

## Final confidence

Start from the prior (graph only) and adjust:

- **Supported** by two or more independent primary studies: raise one level, to at most high.
- **Supported** by one primary study: keep the prior, or raise speculative to low.
- **Mixed:** lower one level, and say what the disagreement is about.
- **Contradicted:** lower to low or speculative, whatever the prior.
- **No literature found:** keep the prior.

In the last column, say in one clause what would change the grade: a direct assay, an independent
replication, a study in the relevant cell type.

## The output

The table, one row per inference, in the order they were written:

| # | Inference | Kind | ProKN basis | Supporting PMIDs | Contradicting PMIDs | Verdict | Confidence | To test or strengthen |
|---|-----------|------|-------------|------------------|---------------------|---------|------------|-----------------------|
| 1 | Drug X may reduce phosphorylation of P via kinase K | mechanism | X-K (DrugCentral, IC50); K-P site (PMID 11111111) | 22222222 (primary) | none found | Supported | moderate | assay of P phosphorylation after X in the same cell line |
| 2 | A may relate to C through B | bridge | A-B (PMID 33333333); B-C (Reactome) | none found | none found | No literature found | speculative | direct A-C assay |

The PMIDs above are placeholders that show the format. Write "none found" rather than leaving a
cell blank. Keep contradicted and untested rows in the table.

After the table, a summary of three to five sentences: which inferences held up, which were
contradicted, which remain hypotheses, and what wasn't searched (a branch, a direction, a date
range, non-English work). Then, if the papers raised ideas that weren't among the inferences, one
line of literature leads, marked as untested.
