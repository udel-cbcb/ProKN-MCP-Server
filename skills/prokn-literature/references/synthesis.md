# Turning hits into a review

How to go from a pile of PMIDs to a short, cited, honest write-up that lines up with the graph.

## Group by claim, not by paper

Organize the review around the connections the user asked about (kinase A phosphorylates site B;
drug X inhibits target Y), not around one-paper-per-paragraph. Under each claim, put the evidence
for and against, each point cited. A reader should be able to scan the claims and see how well each
one holds.

## Cite and tier every point

- Every sentence that makes a factual claim carries its PMID(s).
- Label the strength:
  - **Curated primary experiment** (a direct experimental result; ProKN edge PMIDs are usually
    here) - strongest.
  - **Review or meta-analysis** - good for consensus, but it's secondary; cite the primary paper
    when the claim is specific.
  - **Preprint or computational prediction** - weakest; say so plainly and don't state it as
    settled.
- One good primary paper beats three reviews that all cite it. Don't inflate a count by listing
  reviews of the same result.

## Reconcile with the graph (the ProKN-specific part)

For each connection, state which bucket it falls in and cite accordingly:

- **Agree:** graph edge + a paper (the edge's own PMID, or a new one your search found). Say both.
- **Graph-only:** the edge has a curated PMID your search didn't independently surface. Keep it as
  valid curated evidence; note the search didn't expand it.
- **Literature-only:** papers support something the graph lacks. Mark it new/extending.
- **Conflicting:** a paper disputes the edge. Report both sides; never drop one quietly.

Keep the two PMID sources labeled so curated edge evidence stays distinguishable from search hits.

## Be honest about coverage

- If a claim has no literature, say "no PubMed support found for X" rather than omitting it.
- Name what you didn't search (a branch, a direction, a date range, non-English work) in one line.
- Don't let a thin result masquerade as a thorough review. Length is not evidence.

## Shape of the output

A short prose review grouped by claim, each point cited and tiered, then a one-line coverage note
(what was and wasn't searched), then the reproducibility pointer (the queries and PMIDs, plus the
ProKN record path if there was a graph step). Skip the padding.
