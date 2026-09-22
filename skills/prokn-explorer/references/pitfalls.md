# Pitfalls and fixes

Skim this before reporting a result. Each item is the flip side of an input rule or a step in the
main workflow.

- **Links are self-contained now.** The link carries the gene set in the URL
  (`filter={"gene_names":[...]}`) and the Explorer builds the network on page load, so there's no
  `network_id` cache to expire and no "Your session on ProKN expired" (that was the old flow, which
  broke across server workers/restarts). If a link doesn't render, check the genes and the host, not
  a cache.

- **Empty networks are valid, not broken.** If the input proteins share no pathway, complex, or GO
  term, the Explorer shows "No results". Say so plainly instead of implying the link is broken or
  the proteins don't exist.

- **Gene symbols only.** ProKN matches the protein `geneNames` property. Accessions, RefSeq,
  Ensembl, PubChem CIDs, and protein names won't match directly, so map them with `--from` first
  (see `id-types.md`). Symbols are case-sensitive; use the canonical form.

- **Mapping is best-effort and any-species.** An ID can map to several gene symbols or to none;
  unmapped inputs are reported, not dropped quietly. Since no taxon filter is applied, an ID shared
  across organisms can map to symbols from more than one species. Results are de-duplicated but not
  sorted by organism.

- **Two or more symbols, checked after mapping.** The network needs a pair to connect. If three
  accessions all map to the same gene, you're left with one symbol and the request is rejected.
  Report the collapse instead of a bare error.

- **ID mapping uses a second host.** With `--from`, the script calls `idmappingtest.uniprot.org`,
  not ProKN. In a sandbox that host has to be allow-listed too; the script's error names whichever
  host was blocked. It uses the service's synchronous mode and reads tab-delimited
  `source<TAB>gene` lines. If the mapping output ever looks wrong, re-check that format against a
  live response.

- **Render vs query.** This skill only renders a network. If the user actually wants the data
  (neighbors, paths, evidence), that's the ProKN MCP server tools, not this skill.
