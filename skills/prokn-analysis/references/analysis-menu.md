# Analysis menu

Named recipes for common ProKN questions. Each is a tool chain to run, not the only way to do it.
Resolve names with `search_entities` first, and keep the `evidence` on every edge you report.

## 1. Kinase-substrate mapping

Goal: the sites a kinase phosphorylates, or the kinases that act on a site.

- Kinase to sites: `get_phosphosites_catalyzed_by_proteins(proteins=[kinase])`.
- Site to kinases: `get_proteins_catalyzing_sites(phosphosites=[site])`.

Report: each site/kinase with its evidence (iPTMnet / PhosphoSIGNOR PMIDs). Note sites with no
known kinase rather than dropping them.

## 2. Perturbagen crosstalk

Goal: the kinases a perturbagen affects, and how they connect.

1. `search_entities(perturbagen)` to confirm it and get its identifiers.
2. `get_phosphosites_regulated_by_perturbagen(perturbagen, direction="down")` for the changed sites
   (LINCS P100; the log2Ratio is the evidence).
3. `get_proteins_catalyzing_sites(phosphosites=[...])` for the kinases behind those sites.
4. Optional: `get_protein_interactions` or `get_pathways_between_protein_sets` to show how the
   kinases connect.
5. Optional: hand the kinase set to `get_explorer_network` for a picture.

Report: the kinases with evidence, and label the LINCS measurement as a signal, not a mechanism.

## 3. Drug repurposing (target to disease to drug)

Goal: from a target, find drugs used for the diseases that target is tied to.

1. `search_entities(target)` (a protein or gene).
2. `get_relationship_given_entity(entity=target, neighbor_type="Disease")` for the target's diseases.
3. For those diseases, find drugs (`get_relationship_given_entity(entity=disease, neighbor_type="Drug")`
   or `get_drugs_mechanisms` from the drug side).
4. Map candidate drugs back onto the target.

Report: candidates with the evidence for each hop, and be clear this is a hypothesis, not a claim
that the drug treats the target's condition.

## 4. Disease to protein to drug

Goal: from a disease, find its proteins and the drugs that act on them.

1. `search_entities(disease)`.
2. `get_relationship_given_entity(entity=disease, neighbor_type="Protein")` for associated proteins.
3. `get_drugs_mechanisms` (or the neighbor lookup) for drugs acting on those proteins.
4. Optional: narrow proteins to kinases with `filter_proteins_by_ec_number` if the question is
   kinase-focused.

Report: the protein and drug hits with evidence; separate approved drugs from weaker links.

## Notes

- These chains cross sources; see `cross-source.md` for how to combine and keep provenance separate.
- If a step returns nothing, resolve the name again or widen a filter before concluding there's
  nothing there. Record which steps you skipped and why (see SKILL.md).
