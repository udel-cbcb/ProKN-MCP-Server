# Pitfalls

Skim before finalizing. Each is the flip side of a rule in `SKILL.md`.

- **Searching before inferring.** Write every inference, with its basis and prior, before the first
  literature search. New ideas from the papers go in the literature leads line.
- **Inferences without edges.** An inference that names no ProKN edges is background knowledge,
  not a graph inference.
- **Counting the edge's own PMID as support.** It's part of the basis.
- **Searching only for support,** or one broad query for several inferences. Run a support and a
  counter query for each inference on its own.
- **Dropping inferences that didn't hold up,** or treating "No literature found" as a refutation.
  Both stay in the table; untested means untested.
- **Spurious bridges.** B must be the same node in both edges, not just a shared symbol or a drug
  class.
- **Citing from titles,** or citing a paper with no sentence that states the finding. No quotable
  sentence, no support.
- **Bad quotes:** rewording, tidying, or joining sentences, or quoting the background instead of
  the result. A reworded quote misquotes the paper and breaks its link.
- **Broken links:** an unencoded comma, hyphen, or ampersand; Greek letters, superscripts, or
  citation numbers at START or END; or an abstract page for a full-text quote (or the reverse).
- **Deciding from the abstract when the full text was open,** or reading every paper in full.
  Full text is for the one or two deciding papers per inference.
- **Hiding how deep the check went.** Mark deciding papers "abstract only" when the full text
  couldn't be read, and say in the summary which were read in full.
- **Review-stacking and single studies.** Reviews of one result count once, and one mouse study or
  preprint can't make an inference high confidence.
- **Taking Paperclip's `evidence` labels at face value.** An Introduction sentence citing another
  paper is background; follow it to the primary paper. A "refutes" passage may be about a
  different effect ("independent of EGFR" doesn't refute EGFR inhibition). The design label
  describes the paper, not the passage.
- **Counting a trial registration as evidence.** Only posted results, or FDA label and review text,
  count.
- **Citing retracted papers.** Leave them out and mention in the summary that one came up.
- **Counting one paper twice** across PubMed and Paperclip, or citing a preprint that has since
  been published.
- **Running Paperclip's `map` or `reduce`.** They use up the account's daily allowance. Stick to
  `evidence`, `search`, `lookup`, `grep`, and `cat`.
- **An unretraceable check.** Pass every query, every Paperclip call, and every cited paper with
  its quote in the `literature` argument of `create_reproducibility_record`.
- **Invented or merged citations.** The PMIDs in the reference examples are placeholders.
- **Wrong skill.** Networks are `prokn-explorer`; graph facts without conclusions are
  `prokn-search`.
