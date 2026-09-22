# Pitfalls and fixes

Skim before finalizing an analysis. Each item is the flip side of an operating rule or a step in
the flow.

- **Querying before resolving.** Guessing a name or ID instead of running `search_entities` first.
  If a tool returns a "not found" guidance message, resolve the name and retry; don't jump to raw
  Cypher.

- **Raw Cypher when a tool exists.** `execute_read_only_cypher` is a last resort. If a task tool
  answers the question, use it; the specific tools are more reliable and already shaped for the job.

- **Dropping the evidence.** Reporting a connection without its provenance. List PMIDs when present,
  otherwise name the source database, and say so explicitly when an edge has none. Don't merge
  sources into one citation or invent PMIDs.

- **Over-claiming a missing connection.** If the graph has no edge, report the absence. Don't fill
  the gap from background knowledge without labeling it as background.

- **Ambiguous names.** A term can match more than one node (a Gene and a Protein both labeled
  `EGFR`). Use the identifiers `search_entities` returns to pick the right one, and pass a specific
  id when a tool supports it.

- **Phosphosite label format.** Site labels from one tool must match what the next tool expects.
  Feed the labels a tool returns (for example the `PHOSPHORYLATION_<acc>_<site>` form) straight into
  `get_proteins_catalyzing_sites`; don't hand-build them.

- **`ec_filter` hides non-kinase targets.** Several tools default `ec_filter` to `2.7.*`, i.e.
  kinases only. If you want all targets (for a drug, a catalyzing enzyme, etc.), pass `".*"` or the
  empty string as the tool's docstring notes.

- **Perturbagen by name vs PubChem.** A perturbagen/drug may resolve by name, LINCS pertIname, or
  PubChem CID. If a lookup by one comes back empty, confirm with `search_entities` and try another
  identifier before concluding there's nothing.

- **Big hubs are slow.** `get_subgraph` on a densely connected node can time out. Keep `max_hops`
  small (1-2) and lean on `get_relationship_given_entity` for a single hop.

- **Render vs query.** If the user only wants a picture of a set, that's `prokn-explorer` /
  `get_explorer_network`, not a data pull. Conversely, don't answer a facts question with just a
  link.

- **Forgetting the record.** Call `reset_query_log` at the start and `create_reproducibility_record`
  at the end. The record is built from the log (what actually ran), not from memory, and it writes a
  `.md` file (returning its path) instead of cluttering the chat. Give the user the path plus a
  quick reproducibility summary; don't paste the whole record. The log is per session and clears on
  server restart.
