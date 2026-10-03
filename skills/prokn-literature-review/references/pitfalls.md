# Pitfalls and fixes

Skim before finalizing a literature review. Each item is the flip side of an operating rule.

- **Loose-word queries.** Searching the user's phrasing instead of resolved entities and aliases.
  Turn the set into gene symbols (plus aliases), generic drug names, and specific terms first;
  a vague query gives a vague review.

- **Citing from titles.** A title is a lead, not evidence. Read the abstract with
  `get_article_metadata` before you cite; only reach for full text when the abstract isn't enough
  and `get_copyright_status` allows it.

- **Ignoring the graph's PMIDs.** Reporting papers without lining them up against the evidence ProKN
  already carries. Always reconcile (agree / graph-only / literature-only / conflicting) so the user
  sees what's corroborated and what's new.

- **Treating one study as settled.** A single mouse experiment or a preprint is not consensus. Label
  the tier; don't state weak evidence as fact.

- **Review-stacking.** Listing several reviews that all trace to the same primary result to make the
  support look deeper than it is. Cite the primary paper.

- **One broad query for several claims.** Makes citations unattributable. One targeted search per
  claim or entity pair.

- **Silent gaps.** Not saying a claim had no literature, or hiding a date/language/branch filter.
  Report empty results and name what you skipped.

- **Invented or merged citations.** No fabricated PMIDs, and don't fuse separate papers into one
  citation. If you can't cite it, don't assert it.

- **Unretraceable review.** Forgetting to list the exact queries and PMIDs. PubMed calls aren't in
  ProKN's query log (different server), so pass them in the `literature` argument of
  `create_reproducibility_record` (it has a field for exactly this) when there was a graph step.

- **Over-claiming inferences.** An inference is not a fact. Label every one, ground it in the PMIDs
  it rests on, grade its confidence, and phrase bridging/gap inferences as testable hypotheses.
  Don't state a single-study or preprint inference as settled, and don't call a literature-only
  inference "in ProKN". (Full rules in `inference.md`.)

- **Spurious ABC bridges.** A bridging hypothesis is only valid if the shared B is the *same* entity
  in both halves. If B is one word meaning two things (a symbol mapping to two genes, a drug class vs
  a specific drug), the A-C link is an artifact. Resolve B before proposing the bridge.

- **Lit review vs graph vs network.** This skill reviews the literature and (optionally) infers over
  it. Reading graph facts is the ProKN data tools; rendering a network is `prokn-explorer`. Don't
  answer a "show me" with a review or a "what does the literature say" with a bare edge.
