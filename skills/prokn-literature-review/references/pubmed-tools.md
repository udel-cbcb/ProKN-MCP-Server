# PubMed tools and query building

PubMed is the primary literature source; Paperclip, the optional second one, is in
`paperclip-tools.md`. Tool names are the server's own; check the connected tool for exact
parameters.

## Which tool for which need

- **Find papers:** `search_articles` with a focused query. Read the returned PMIDs and titles.
- **Expand from one good hit:** `find_related_articles`, when a search is thin.
- **Read a paper:** `get_article_metadata` (title, abstract, journal, year, authors, PMC ID, DOI).
  This is the first read for every paper.
- **Full text:** `get_full_text_article`, after `get_copyright_status`, only for deciding papers
  that Paperclip doesn't have (see "Tiered reading" in `verification.md`).
- **Translate identifiers:** `convert_article_ids` (PMID, PMCID, DOI), or
  `lookup_article_by_citation` for a citation string.

## Building the queries

- **Use resolved entities, not loose words:** the gene symbol with its common aliases, the drug's
  generic name, the disease term. `(EGFR OR ERBB1) AND gefitinib AND resistance` beats "egfr drug
  stuff".
- **Pair what the inference connects.** For "drug X lowers phosphorylation of P through kinase K",
  query `X AND K AND phosphorylation` and `X AND P AND phosphorylation`.
- **Add a counter query:** the same pair plus
  `(resistance OR reactivation OR compensatory OR "no effect")`. For a bridge A-B-C, also search
  `A AND C`; a paper that tested A-C and found nothing is a contradiction.
- **Widen only when empty.** Try an alias or drop the weakest term before concluding there's no
  literature. When a query returns hundreds, narrow it with a tissue, mechanism, or year range.
- **Note any filter you apply** (a date cutoff, English only, reviews only) in the summary.

## Reading order

1. `search_articles` for both queries. Pick the plausible titles; a title is a lead, not
   evidence.
2. `get_article_metadata`: read the abstracts, keep the papers that address the inference either
   way, and copy each deciding sentence.
3. `find_related_articles`: only to round out a thin result.
4. Full text for the deciding papers only (`verification.md`, "Tiered reading").

Record each query exactly as run, grouped by inference, in the `literature` argument of the
reproducibility record.
