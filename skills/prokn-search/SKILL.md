---
name: prokn-search
description: 'Investigate a biological question with evidence from the ProKN knowledge graph: resolve entities, pull the relevant relationships, pathways and subgraphs, cite the evidence on each edge, and optionally hand the resulting gene set to prokn-explorer for a network view. Use for "what connects these proteins", "analyze or investigate this gene/drug/disease in ProKN", "search ProKN for ...", "find the kinases/pathways/targets for ...", "how is X related to Y", "which proteins does this drug target", or any question that wants facts and evidence from the graph, including requests that work something out and THEN show it as a network. NOT for only rendering a gene list as a network (use prokn-explorer).'
compatibility: >-
  Requires the ProKN MCP server (its data tools) to be connected. Pairs with the prokn-explorer
  skill for the optional visualization step.
metadata:
  author: University of Delaware, Center for Bioinformatics and Computational Biology
  version: "0.3.0"
  repository: https://research.bioinformatics.udel.edu/ProKN/
  companion_skills: ../prokn-explorer/SKILL.md, ../prokn-literature-review/SKILL.md
---

# ProKN search

A method for answering a biological question *with evidence* from ProKN: turn the user's wording
into real entities, pull the relationships, pathways, and subgraphs that bear on the question,
report the findings with their provenance, and say so when the graph has nothing on the question.

## 1. What this is and when to use it

Use it for questions that want facts from the graph: a drug's targets, a site's kinases, a single
entity's neighbors, a path between two proteins, the pathways a set shares, and so on. If the user
only wants to *see* a set of proteins as a network, that's the `prokn-explorer` skill, not this one.

The skill works through the individual tools and covers how to use them together:
log the run, resolve, retrieve, cross-reference, cite, optionally visualize, and end with a
reproducibility record.

## 2. Operating rules

- **Resolve first.** Turn names and IDs into exact entities with `search_entities` before calling a
  specific tool. If a tool reports it can't find something, resolve the name and retry rather than
  guessing or switching to raw Cypher.
- **Prefer the specific tool.** Each task tool answers one question. Use `execute_read_only_cypher`
  only when no task tool fits.
- **Cite the evidence.** Every reported connection carries edge provenance. List PMIDs if present,
  otherwise name the source database. If an edge has none, say so (see section 6).
- **Log the run and save the record.** Call `reset_query_log` at the start and
  `create_reproducibility_record` at the end (section 5). The run isn't finished until the record
  is saved; listing tool names in the reply doesn't replace it. This applies even when the run ends
  in a visualization, since the record also lists `get_explorer_network`.
- **Declare what you skipped.** If you didn't check a branch (drugs, pathways, a source, a
  literature step), say so with a one-line reason. Otherwise the reader will assume everything was
  covered.
- **Report gaps.** If a connection isn't in the graph, say so. Don't fill gaps from
  background knowledge without labeling it as background.
- **Read-only.** No writes, ever.

## 3. The ProKN tools

Point at the server's own tools; don't re-document them here. Grouped by concern:

- Resolve: `search_entities`
- Proteins / genes: `get_proteins_encoded_by_genes`, `get_protein_interactions`,
  `filter_proteins_by_ec_number`
- Phosphosites / kinases: `get_proteins_catalyzing_sites`,
  `get_phosphosites_catalyzed_by_proteins`, `get_phosphosites_regulated_by_perturbagen`
- Drugs: `get_drugs_mechanisms`, `get_genes_regulated_by_drugs`
- Neighborhood / paths / pathways: `get_relationship_given_entity`, `get_subgraph`,
  `get_pathways_between_protein_sets`
- Schema / introspection: `get_graph_schema`, `get_node_properties`, `get_relationship_properties`
- Reproducibility: `reset_query_log`, `get_query_log`, `create_reproducibility_record`
- Escape hatch: `execute_read_only_cypher`
- Visualize (hand-off): `get_explorer_network` (see section 9)

A map of which tool answers which question, plus the common chains, is in `references/tool-map.md`.

## 4. Search flow

Run only the steps the question needs.

0. **Start.** Call `reset_query_log` so this search is logged on its own.
1. **Frame.** Identify the entity type(s) and what the question is really asking.
2. **Resolve.** `search_entities` for each input; when a name is ambiguous, pick the right node.
3. **Retrieve.** Call the specific tool(s) for the question. For common questions, follow a named
   recipe in `references/search-recipes.md`.
4. **Cross-reference.** When the question spans sources, combine them and say which gave each piece
   (see `references/cross-source.md`).
5. **Cite.** Report each finding with its `evidence` attached (section 6).
6. **Visualize (optional).** If the result is a gene/protein set worth seeing as a network, hand it
   to `prokn-explorer` / `get_explorer_network`.
7. **Report and record.** Summarize the biology, then save the record (section 5).

## 5. Reproducibility record (required)

At the end of every run, call `create_reproducibility_record`, passing:

- `question`: the question.
- `findings`: the findings, each with its evidence (see section 6). Markdown is fine.
- `skipped`: any branch you skipped, one per line with a one-line reason.
- `skills`: the skills used, e.g. `prokn-search v0.3.0, prokn-explorer v0.3.0`.

The tool fills in the tool calls that actually ran (from the query log) and the instance/date, then
writes a `.md` file to disk (also served at `record://session/latest`) and returns its path. Do not
paste the whole record into the reply: give the user the file path and a quick reproducibility
summary: a line or two naming how many tool calls ran and which sources the evidence came from. The
file goes to `PROKN_RECORD_DIR` if set, otherwise a `prokn_records/` folder in the server's working
directory; on a remote server that path is on the server, not your machine.

Call `reset_query_log` at the start, or the record will include earlier calls. The log is per
session and clears when the server restarts. `get_query_log` is there if you want to inspect the raw
calls.

## 6. Evidence and provenance

- Relationship tools return an `evidence` object on each edge. It holds PMIDs when the source
  curated them, otherwise the source database (`SAB` / `dcc`), plus measurement values for
  quantitative edges (LINCS `log2Ratio`, DrugCentral IC50).
- Report PMIDs when present; otherwise name the source database. If an edge has no provenance, say
  so rather than implying certainty.
- Label the evidence tier: curated literature (PMID) > database assertion > measurement /
  computational signal. Don't state a measurement or a tox perturbation as a proven mechanism.
- Don't merge findings from different sources into one citation, and don't invent PMIDs.
- Per-source citation guide and the tiers are in `references/evidence.md`.

## 7. Search recipes (named tool chains)

Short, named tool chains for common questions. Full steps in `references/search-recipes.md`:

- Kinase-substrate mapping (kinase to sites, or site to kinases).
- Perturbagen crosstalk (perturbagen to downregulated sites to kinases).
- Drug repurposing (target to disease to drug).
- Disease to protein to drug.

## 8. Worked example

"Which kinases are downregulated by the perturbagen alpelisib, and show them as a network."

1. `reset_query_log()`.
2. `search_entities("alpelisib")` to confirm it's a perturbagen and get its identifiers.
3. `get_phosphosites_regulated_by_perturbagen(perturbagen="alpelisib", direction="down")` for the
   LINCS P100 sites it lowers.
4. `get_proteins_catalyzing_sites(phosphosites=[...])` for the kinases, keeping the `evidence`.
5. Resolve the kinases to gene symbols and call `get_explorer_network` for the link.
6. `create_reproducibility_record(question=..., findings=..., skills="prokn-search v0.3.0, prokn-explorer v0.3.0")`
   to save the record; end with the saved file path and a quick reproducibility summary, noting any
   sites with no known kinase.

## 9. Visualizing the result

When a search yields a set of genes or proteins, the network view is a good closing step.
Resolve the set to gene symbols and call `get_explorer_network` (or defer to the `prokn-explorer`
skill), then give the user the Explorer link alongside the findings.

## 10. References (read on demand)

Depth lives in `references/` so this file stays short. Open the one you need:

- `references/tool-map.md`: which tool answers which question, and the common chains.
- `references/search-recipes.md`: the named recipes in full.
- `references/cross-source.md`: combining sources and keeping provenance separate.
- `references/evidence.md`: per-source citation guide and evidence tiers.
- `references/pitfalls.md`: recurring cross-tool mistakes and fixes. Skim before finalizing.

## 11. Gotchas

The full list is in `references/pitfalls.md`. The ones you'll hit most: skipping `search_entities`
and guessing a name, reaching for raw Cypher when a task tool already fits, dropping the `evidence`
when you report a connection, and skipping the reproducibility record.
