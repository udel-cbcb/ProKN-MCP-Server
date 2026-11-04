# Inferring from the graph

How to turn ProKN edges into inferences before any literature search. Every inference here rests on
named graph edges, is written as one testable sentence, and gets a prior confidence from the graph
evidence alone. If you can't do all three, don't make the inference.

## The kinds, with the graph patterns behind them

### 1. Edge strength

Take one connection and say how well its own provenance backs it.

- Pattern: a single edge (drug-target, kinase-site, protein-pathway) and its `evidence` object.
- Prior: curated PMID > database assertion (source database only) > measurement or tox signal
  (LINCS `log2Ratio`, a ChEMBL tox-screen link).
- Example: "Lapatinib inhibits ERBB2 (DrugCentral edge with an IC50 value)."

### 2. Mechanism

A path suggests how one entity affects another.

- Pattern: a chain of edges, e.g. drug -> target kinase -> site -> protein -> pathway, from
  `get_drugs_mechanisms`, `get_phosphosites_catalyzed_by_proteins`,
  `get_pathways_between_protein_sets` or `get_subgraph`.
- Prior: no higher than the weakest edge in the chain, and one step lower for each step that is
  only a measurement.
- Example: "Drug X may reduce phosphorylation of protein P, since it inhibits kinase K, which
  catalyzes a site on P."

### 3. Bridge (A-B-C)

The graph has A-B and B-C but no direct A-C.

- Pattern: two edges sharing a node, with no edge between the ends (check with
  `get_relationship_given_entity` or `get_protein_interactions`).
- Prior: speculative or low.
- Check that B is the same node in both edges: same node ID, not just the same label. A symbol that
  maps to two genes, or a drug class standing in for one drug, makes the bridge invalid.

### 4. Shared context

Input proteins share pathways, complexes, or GO terms.

- Pattern: the shared nodes from `get_pathways_between_protein_sets` or a subgraph of the set.
- Prior: moderate when several specific pathways or a complex are shared; low when the only shared
  nodes are broad GO terms.
- Example: "CDK1 and CDK2 act together in G2/M regulation (both participate in three Reactome
  cell-cycle pathways)."

### 5. Gap

A connection you'd expect from the rest of the graph is missing.

- Pattern: most members of a set share an edge that one member lacks, or a kinase's close family
  members all reach a site it doesn't.
- Prior: speculative. A missing edge often means missing curation, not missing biology.

## Prior-confidence rubric (graph only)

- **High:** a direct edge with a curated PMID, or several independent curated edges agreeing.
- **Moderate:** a database assertion, or a short path of curated edges.
- **Low:** rests on a measurement or tox signal, or on a longer path.
- **Speculative:** a bridge or a gap.

Write the prior down with the inference. The literature check can raise or lower it later
(`SKILL.md`, section 7), but the prior records what the graph alone supports.

## Writing the inference

- One sentence, testable, in plain terms: who does what to whom.
- Name the edges it rests on, with their provenance, in the ProKN basis column.
- Say "may" or "suggests" for anything below high; never state a bridge or gap as fact.
- Prefer the few inferences the question needs over a long list. Each one costs at least two
  PubMed searches.
