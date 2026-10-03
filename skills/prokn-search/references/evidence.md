# Evidence and how to cite it

ProKN stores provenance on relationships. Most relationship tools return an `evidence` object on
each edge. Read it and report it. If an edge has no provenance, say so.

## What the evidence field holds

- **PMIDs** when the source curated a literature reference.
- **Source database** name in `SAB` (and sometimes `dcc`) when there is no PMID.
- **Measurement values** for quantitative edges (for example `log2Ratio` for LINCS, `actValue` /
  IC50 for DrugCentral), plus source-specific IDs (for example `signorId` for PhosphoSIGNOR).

## Provenance by source

| Source | Edge it backs | What to cite |
| --- | --- | --- |
| iPTMnet | kinase CATALYZES site | PMIDs |
| PhosphoSIGNOR | CATALYZES, UP/DOWN_REGULATES | PMIDs + `signorId` |
| ChEMBL | drug HAS_MECHANISM target | mechanism text, action type, `SAB=ChEMBL` |
| DrugCentral | drug INTERACTS_WITH protein | IC50 / `actValue`, action type, source URL |
| Reactome | PARTICIPATES_IN, PATHWAY_EVENT_OF | `SAB=Reactome` |
| LINCS P100 | perturbagen/experiment to site | `log2Ratio` (a measurement, not a citation) |
| LINCS L1000 | drug regulates gene | regulation direction + strength |
| UniProtKB | protein attributes, ASSOCIATED_WITH disease | `SAB=UniProtKB`, PMIDs when present |
| IMEx | protein INTERACTS_WITH protein | PMIDs |
| GO | GO annotations | `SAB=GO` |

## Evidence tiers (label which one a claim rests on)

1. **Curated literature.** A PMID backs the edge. Strongest.
2. **Database assertion.** A curated database asserts it but there's no PMID. Cite the database.
3. **Measurement / computational.** A quantitative signal (LINCS `log2Ratio`, a tox perturbation).
   Report the value and the dataset, and don't state it as a mechanistic fact.

A common mistake is treating tier 3 like tier 1. For example, a LINCS perturbation lowering a site,
or a ChEMBL tox-screen compound-gene link, is a signal, not a proven therapeutic mechanism. Say
which tier you're on.

## How to write a citation

- With PMIDs: `EGFR is inhibited by lapatinib (ChEMBL; PMID: 12345678).`
- Database only: `Protein participates in the pathway (Reactome).`
- Measurement: `Site down after alpelisib (LINCS P100; log2Ratio -3.4).`
- No provenance: `This edge carries no provenance in ProKN.`

Rules: every reported connection carries its source. Don't merge findings from different sources
into one citation, and don't invent PMIDs.
