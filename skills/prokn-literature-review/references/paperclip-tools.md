# Paperclip tools (optional second source)

Paperclip (GXL, `https://paperclip.gxl.ai/mcp`) is a second literature source next to PubMed. It
adds bioRxiv and medRxiv preprints, trial registries, FDA (plus EU and Japan) regulatory
documents, line-numbered full text split by section, and `evidence`, a claim-level search. It
doesn't add peer-reviewed full text: its PMC coverage is the open-access set, about what PubMed's
`get_full_text_article` can open. Tool names are the server's own; check the connected tool for
exact parameters.

## Which tool for which need

- **Claim-level search:** `evidence` with the inference as `claim` (`per_side` 3 to 5). It returns
  passages judged for and against, each with the exact quote (in «…»), a judge confidence, a
  study-design label, the paper (PMC ID or PMID), and its section. Re-judge every passage (below).
- **Topic search:** `search` with `query` and a required `source`. Use `pmc,biorxiv,medrxiv` for
  papers and preprints (avoid `papers`, which adds arXiv), and `trials` or `fda` only for drug
  inferences. Keep `limit` near 10. Each hit gives a document ID, the matched section, and its
  lines; each search returns a result ID (e.g. `s_467e0914`) to record.
- **A paper you already have from PubMed:** `lookup` with `field` `pmc` or `doi`. "No documents
  found" means it isn't in Paperclip's corpus (often an author manuscript or a paywalled paper),
  so use PubMed for it.
- **Reading:** `ls /papers/<ID>/sections/` lists the section files, and `cat` reads one, e.g.
  `cat /papers/PMC3203921/sections/Results and Discussion.lines`. To find the deciding paragraph,
  `grep` `/papers/<ID>/content.lines` with `ignore_case` and `show_line_numbers`. Lines are
  paragraphs (`L8`); record the line with the quote.
- **Saved results:** `results` re-opens one; `merge` and `intersect` combine them.

Don't use `map`, `reduce`, `filter`, `refine`, or the repo tools (`git_*`) unless the user asks.
`map` runs an AI reader over every document, and the free tier allows about 100 documents a day
per account.

## Reading `evidence` output

The judge is a first pass. Before using a passage:

- **Check the section.** Count Abstract, Results, and figure-legend passages. An Introduction or
  Discussion sentence citing another paper ("as shown in [18]") is background: follow the citation
  to the primary paper.
- **Re-judge the direction** against the inference itself. "Independent of EGFR" doesn't refute
  that a drug inhibits EGFR; it's about a different effect.
- **Use your own tier.** The design label describes the paper, not the passage: "RCT" on an
  introduction sentence isn't trial evidence.
- **Drop retracted papers** (marked [RETRACTED]), and mention in the summary that one came up.
- **Ignore the judge's score.** Final confidence comes from the rubric in `SKILL.md`.
- **Keep the quote exact.** The text in «…» is the quote; record its section and line.

## Preprints, trials, and FDA documents

- **Preprints** are the weakest tier. If one has since been published (search PubMed by its title,
  or `lookup` its DOI), cite the published version.
- **Trials and FDA documents** are only for drug inferences. A registration whose match is in the
  eligibility criteria, background, or references only shows the drug was tested: record it as
  partly addressing at most. Posted results are primary clinical evidence. FDA label or review text
  stating the mechanism counts like a database assertion. Cite trials by NCT number and FDA
  documents by path.

## Call budget

Limits are per account (free tier: about 25 searches a minute). Per inference, plan on one
`evidence` call; one `search` on `pmc,biorxiv,medrxiv` if `evidence` returns little; one `trials`
(and maybe `fda`) search for a drug inference; and `lookup`, `cat`, and `grep` on at most two
deciding papers.

## What to record

In the `literature` argument of `create_reproducibility_record`, for each inference: every
Paperclip call (tool, claim or query, `source`, result ID), and for each cited Paperclip document
its identifier, the section and line of the quote, and which source found it.
