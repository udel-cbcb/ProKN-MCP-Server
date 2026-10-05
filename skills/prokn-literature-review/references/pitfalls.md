# Pitfalls and fixes

Skim before finalizing. Each item is the flip side of an operating rule.

- **Searching before inferring.** Running PubMed first and then writing inferences that match the
  papers. Write every inference, with its ProKN basis and prior confidence, before the first
  search. New ideas from the papers go in the literature leads line, not in the table.

- **Inferences without a graph basis.** An inference that names no ProKN edges is background
  knowledge, not a graph inference. Either find the edges that support it or leave it out.

- **Counting the edge's own PMID as support.** A PMID already on an edge the inference came from
  is part of the basis. Listing it as supporting literature double-counts it.

- **Searching only for support.** Every inference looks good if you only look for agreement. Run a
  counter query for each one, and sort papers by what the abstract says, not by which query found
  them.

- **Dropping inferences that didn't hold up.** Contradicted and untested inferences stay in the
  table with their verdicts. Removing them hides what the check found.

- **Treating no literature as a refutation.** "No literature found" means untested. The inference
  keeps its prior and stays a hypothesis.

- **Spurious bridges.** An A-B-C bridge is only valid if B is the same node in both edges. A symbol
  that maps to two genes, or a drug class standing in for one drug, makes the A-C link an artifact.

- **Citing from titles.** Read the abstract with `get_article_metadata` before citing; reach for
  full text only when the abstract isn't enough and `get_copyright_status` allows it.

- **One broad query for several inferences.** Makes it unclear which paper bears on which claim.
  Search each inference on its own.

- **Review-stacking.** Several reviews that trace to the same primary result count once. Cite the
  primary paper.

- **Treating one study as settled.** A single mouse experiment or a preprint can't make an
  inference high confidence on its own.

- **Unretraceable check.** PubMed calls aren't in ProKN's query log. Pass the exact queries, grouped
  by inference, and the PMIDs cited in the `literature` argument of
  `create_reproducibility_record`.

- **Invented or merged citations.** No fabricated PMIDs, and don't fuse separate papers into one
  citation. The PMIDs in the reference examples are placeholders.

- **Wrong skill for the request.** Rendering a network is `prokn-explorer`; reporting graph facts
  without conclusions is `prokn-search`.
