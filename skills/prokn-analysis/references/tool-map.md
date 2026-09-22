# Tool map: which tool for which question

Resolve names first with `search_entities`, then pick the specific tool below. Use
`execute_read_only_cypher` only when nothing here fits.

## One-step questions

| The question | Tool |
| --- | --- |
| What is X connected to? (one entity's neighbors) | `get_relationship_given_entity` |
| What's around X within a few hops? | `get_subgraph` |
| How are two proteins connected? (shortest path) | `get_protein_interactions` |
| What pathways do two protein sets share? | `get_pathways_between_protein_sets` |
| What protein does gene X encode? | `get_proteins_encoded_by_genes` |
| Which of these proteins are kinases (or another EC class)? | `filter_proteins_by_ec_number` |
| What does drug X target / inhibit? | `get_drugs_mechanisms` |
| What genes does drug X up/downregulate? | `get_genes_regulated_by_drugs` |
| Which kinase phosphorylates site S? | `get_proteins_catalyzing_sites` |
| Which sites does kinase K phosphorylate? | `get_phosphosites_catalyzed_by_proteins` |
| What phosphosites does perturbagen P change? | `get_phosphosites_regulated_by_perturbagen` |
| What node/relationship types exist? | `get_graph_schema` |
| What properties do nodes/edges carry? | `get_node_properties`, `get_relationship_properties` |
| None of the above | `execute_read_only_cypher` (last resort) |
| Show a resulting gene set as a network | `get_explorer_network` (hand-off) |

## Common multi-tool chains

- **Resolve then query.** `search_entities` -> the specific tool. Do this whenever the input is a
  name/ID rather than a confirmed entity, or when a tool says it can't find something.
- **Perturbagen to kinases.** `get_phosphosites_regulated_by_perturbagen` (get the changed sites)
  -> `get_proteins_catalyzing_sites` (the kinases that act on them). Carry the evidence through.
- **Drug to kinase targets.** `get_drugs_mechanisms(action_type="INHIBITOR")` for the inhibited
  targets; drop or widen `ec_filter` to move between "kinase targets only" and all targets.
- **Gene set to shared biology.** `get_proteins_encoded_by_genes` (gene -> protein) then
  `get_pathways_between_protein_sets` or `get_subgraph` to see what they share.
- **Narrow a protein list to kinases.** any protein list -> `filter_proteins_by_ec_number`
  (`2.7.*`).
- **Analysis to picture.** once you have a gene/protein set, resolve to gene symbols and call
  `get_explorer_network` for an Explorer link.

## Picking between the neighborhood tools

- `get_relationship_given_entity`: one hop, one entity, cheapest. Start here for "what is X
  connected to".
- `get_subgraph`: a bounded multi-hop neighborhood. Keep `max_hops` small (1-2) for well-connected
  hubs or it gets slow.
- `get_protein_interactions`: a path *between two* named proteins, not a neighborhood.
