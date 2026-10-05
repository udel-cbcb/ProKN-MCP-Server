# PubMed tools and query building

Which PubMed MCP tool answers which need, and how to write the support and counter queries for an
inference. Tool names are the server's own; check the connected tool for exact parameters.

## Which tool for which need

- **Find papers on a topic** -> `search_articles`. The main entry point. Give it a focused query
  and read the returned PMIDs and titles.
- **Expand from one good paper** -> `find_related_articles`. Use it when a search is thin but you
  have one solid hit; it pulls papers PubMed considers related.
- **Read a paper** -> `get_article_metadata` for title, abstract, journal, year, authors. This is
  what you cite from. Use `get_full_text_article` only when you need more than the abstract and the
  paper is open (check `get_copyright_status` first).
- **Translate an identifier** -> `convert_article_ids` (PMID <-> PMCID <-> DOI) and
  `lookup_article_by_citation` (find the PMID for a citation string).
- **Check rights before quoting or full text** -> `get_copyright_status`.

## Building the queries for an inference

- **Start from resolved entities.** Use the gene symbol and its common aliases, the drug's generic
  name, the disease term. `(EGFR OR ERBB1) AND gefitinib AND resistance` beats "egfr drug stuff".
- **Pair the entities the inference connects.** For "drug X lowers phosphorylation of P through
  kinase K", query `X AND K AND phosphorylation` and `X AND P AND phosphorylation`, not each
  entity alone.
- **Write a counter query too.** Keep the pair and add terms that surface disagreement:
  `X AND K AND (resistance OR reactivation OR compensatory OR "no effect")`. For a bridge A-B-C,
  also search `A AND C` directly; a paper that tested A-C and found nothing is a contradiction.
- **Widen only when empty.** If a paired query returns nothing, try an alias or drop the weakest
  term before concluding there's no literature. If it returns hundreds, add a specific term (a
  tissue, a mechanism, a year range).
- **Note any filter you apply.** A date cutoff, English only, reviews only: these change what you
  find, so they go in the coverage line of the summary.

## Reading order

1. `search_articles` for the support and counter queries: scan titles, pick the plausible ones.
2. `get_article_metadata`: read abstracts; keep the ones that address the inference, in either
   direction.
3. `find_related_articles`: only to round out a thin result.
4. `get_full_text_article` (after `get_copyright_status`): only when the abstract isn't enough.

Don't cite a paper you only saw as a title in step 1. A title is a lead, not evidence.

Record each query exactly as run. They go in the `literature` argument of the reproducibility
record, grouped by inference.
