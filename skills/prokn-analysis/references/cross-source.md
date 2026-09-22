# Cross-source integration

ProKN merges many source datasets into one graph. A stronger answer often combines more than one
of them. The rule is the same as within any federation: combine on shared entities, not on
study/experiment accessions.

## Join on shared entities

Integrate on a gene symbol, a UniProt accession, a protein, or a PTM-site label. These are stable
across sources. Do not join two findings on an experiment, assay, or dataset ID; those are local to
one source and won't line up.

Because ProKN is already one graph, most of this happens for you: the same protein node carries
edges from several sources. Your job is to pull from each relevant source and say which one gave
each piece.

## Data layers by source (what each is good for)

- Kinase to substrate: iPTMnet and PhosphoSIGNOR (both back CATALYZES edges).
- Drug to target: ChEMBL (HAS_MECHANISM) and DrugCentral (INTERACTS_WITH).
- Drug to disease / treatment: ChEMBL / DrugCentral indications.
- Transcriptomic response: LINCS L1000 (genes a drug up/downregulates).
- Phosphoproteomic response: LINCS P100 (sites a perturbagen changes).
- Pathways / complexes: Reactome, UniProt.
- Function: GO.
- Protein interactions: IMEx.
- Disease / variant: UniProt (ASSOCIATED_WITH), plus variant sources where present.

## Common cross-source combinations

- **Two-level perturbation response.** Combine the transcriptomic layer
  (`get_genes_regulated_by_drugs`, LINCS L1000) with the phosphoproteomic layer
  (`get_phosphosites_regulated_by_perturbagen` then `get_proteins_catalyzing_sites`, LINCS P100 +
  iPTMnet) to see the kinases a perturbagen affects at both levels.
- **Union of drug targets.** Pull targets from both ChEMBL (`get_drugs_mechanisms`) and DrugCentral,
  then de-duplicate on the protein. Label the evidence layer for each (a curated mechanism vs a
  measured IC50 vs a tox-screen signal).
- **Kinase-substrate from two curators.** iPTMnet and PhosphoSIGNOR both back CATALYZES; take the
  union and keep each edge's provenance.
- **Shared biology of a set.** Turn genes into proteins (`get_proteins_encoded_by_genes`), then find
  what they share with `get_pathways_between_protein_sets` or `get_subgraph`.

## When you combine, keep the provenance separate

Each source keeps its own evidence (see `evidence.md`). When you report a combined finding, say
which source contributed which part, and don't blur a strong (PMID) source together with a weak
(measurement) one. If you left a source out, say why (see the skipped-work rule in SKILL.md).
