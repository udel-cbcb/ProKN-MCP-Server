# Input ID types (`--from`)

ProKN itself only matches gene symbols. When the inputs are something else, the script maps them
to gene symbols first (`--from <code>`), then sends the resulting symbols to ProKN. The target is
always `GENENAME`; `--from` names the source.

The default is `GENENAME`, which means the inputs are already gene symbols and no mapping happens.

## Common codes

| Input | `--from` code |
| --- | --- |
| Gene symbol (default, no mapping) | `GENENAME` |
| UniProt accession (e.g. `P00533`) | `ACC` |
| UniProt entry name (e.g. `EGFR_HUMAN`) | `ID` |
| UniProt/SwissProt accession | `SWISSPROT` |
| RefSeq protein | `P_REFSEQ_AC` |
| Ensembl gene | `ENSEMBL_ID` |
| Ensembl protein | `ENSEMBL_PRO_ID` |
| Entrez / NCBI GeneID | `P_ENTREZGENEID` |
| HGNC | `HGNC_ID` |
| PDB | `PDB_ID` |
| ChEMBL | `CHEMBL_ID` |
| DrugBank | `DRUGBANK_ID` |
| KEGG | `KEGG_ID` |
| STRING | `STRING_ID` |

## Full list

The service supports about 110 identifier types. The current, authoritative list is served by the
mapping host itself:

`https://idmappingtest.uniprot.org/cgi-bin/idmapping_http_client3?page=list`

It returns lines like `Human name => CODE`. Pass the CODE to `--from`.

## Notes

- **Any species.** The script does not send a taxon filter, so an ID that exists in several
  organisms (RefSeq, Ensembl, EMBL) can map to gene symbols from more than one species. Results are
  de-duplicated but not sorted by organism.
- **Best-effort.** An ID can map to several gene symbols or to none. Unmapped inputs are reported on
  stderr, not dropped quietly.
- **Not validated.** A wrong or misspelled `--from` code just returns no matches (everything
  unmapped) instead of an error, so check the code against the list above if nothing resolves.
