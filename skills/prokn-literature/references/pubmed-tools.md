# PubMed tools and query building

Which PubMed MCP tool answers which need, and how to write a query that returns useful papers.
Tool names are the server's own; check the connected tool for exact parameters.

## Which tool for which need

- **Find papers on a topic** -> `search_articles`. The main entry point. Give it a focused query
  (see below) and read the returned PMIDs and titles.
- **Expand from one good paper** -> `find_related_articles`. Use it when a search is thin but you
  have one solid hit; it pulls papers PubMed considers related.
- **Read a paper** -> `get_article_metadata` for title, abstract, journal, year, authors. This is
  what you cite from. Use `get_full_text_article` only when you need more than the abstract and the
  paper is open (check `get_copyright_status` first).
- **Translate an identifier** -> `convert_article_ids` (PMID <-> PMCID <-> DOI) and
  `lookup_article_by_citation` (find the PMID for a citation string or a ProKN edge's PMID).
- **Check rights before quoting/full text** -> `get_copyright_status`.

## Building a query that works

- **Start from resolved entities, not the user's phrasing.** Use the gene symbol, its common
  aliases, the drug's generic name, the disease term. `search_articles("EGFR OR ERBB1 AND
  gefitinib resistance")` beats "egfr drug stuff".
- **One claim per query.** If the user wants three connections backed, run three searches, not one
  broad one. It keeps the citations attributable.
- **Pair terms for a connection.** For "does drug X hit kinase Y", query both together
  (`X AND Y`), not each alone. For a mechanism, add the mechanism word (phosphorylation,
  inhibition, expression).
- **Widen only when empty.** If a paired query returns nothing, drop the weakest term or try an
  alias before concluding there's no literature. If it returns hundreds, add a specific term
  (a tissue, a mechanism, a year range).
- **Note any filter you apply.** A date cutoff, English-only, review-only: these change what you
  find, so they go in the "declare what you skipped" line.

## Reading order

1. `search_articles` -> scan titles/PMIDs, pick the plausible ones.
2. `get_article_metadata` -> read abstracts; keep the ones that actually address the claim.
3. `find_related_articles` -> only if you need to round out a thin set.
4. `get_full_text_article` (+ `get_copyright_status`) -> only when the abstract isn't enough.

Don't cite a paper you only saw as a title in step 1. A title is a lead, not evidence.
