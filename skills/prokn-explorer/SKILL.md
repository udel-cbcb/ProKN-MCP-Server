---
name: prokn-explorer
description: 'Turn a list of gene symbols or other protein IDs (UniProt, RefSeq, Ensembl and more, mapped to gene symbols first) into a ProKN network and a shareable Explorer link. The link carries the gene set itself, so it works on any ProKN instance, and the network can be limited to node types such as pathways or complexes. Use for "show / display / view these genes or proteins in ProKN", "visualize this gene or protein set as a network", "make a subnetwork from this list", "show how these proteins are related in ProKN", or "explore this set of genes in ProKN", "show only the pathways these genes share". NOT for reading facts as text, such as the targets, kinases, pathways or evidence for a protein (use prokn-search or the ProKN data tools).'
compatibility: >-
  Uses the get_explorer_network tool when the ProKN MCP server is connected; otherwise runs the
  bundled script, which needs network access to a ProKN web instance and Python 3 (standard
  library only). Renders a network; to query ProKN data, use prokn-search or the server tools.
metadata:
  author: University of Delaware, Center for Bioinformatics and Computational Biology
  version: "0.3.0"
  repository: https://research.bioinformatics.udel.edu/ProKN/
  base_url: https://research.bioinformatics.udel.edu/ProKN/
  api_endpoint: /api/knowledge_graph
  explorer_page: /explorer
  companion_skills: ../prokn-search/SKILL.md, ../prokn-literature-review/SKILL.md
---

# ProKN Explorer link builder

## 1. What this does and when to use it

Use this skill when someone gives you a set of genes or proteins and wants to see them as a
network on the ProKN Explorer, instead of getting data back as text. It takes a list of gene
symbols and returns a ProKN Explorer URL the user can open to view the subnetwork connecting
those proteins.

If the request is to *read* facts about the proteins (targets, kinases, pathways, neighbors),
use `prokn-search` or the ProKN MCP server tools instead.

There are two ways to run it. Both hit the same ProKN API and give the same link:

- **Primary: the MCP tool.** When the ProKN MCP server is connected, call its
  `get_explorer_network` tool. Use this whenever it's available.
- **Fallback: the bundled script.** When there's no MCP server, run
  `scripts/prokn_explorer.py`.

Use one or the other, not both. Prefer the tool when it's there.

## 2. Preflight (check before doing any work)

Check these first and report right away if one is a problem so it doesn't surface
after all the work is done:

- **Is the `get_explorer_network` MCP tool available?** If the ProKN MCP server is connected, use
  it, and only fall back to the script when there's no server.
- **Are the inputs gene symbols?** If they're accessions, RefSeq, Ensembl, and so on, tell the tool
  the ID type with `from_type` (or the script with `--from`); it maps them to gene symbols first
  (see `references/id-types.md`). Sort this out before calling ProKN, not after an empty result.
- **Are there at least two?** The network comes from what proteins share with each other, so one
  symbol has nothing to connect to. If mapping might collapse several IDs down to one gene, flag
  that now.
- **Reachability.** The call has to reach the ProKN host, and when mapping IDs the PIR ID-mapping
  host too. In a sandbox both need to be allow-listed. The script names whichever host was blocked;
  the tool just falls back to the graph if PIR is unreachable. If you already know a host is down,
  say so before running.

## 3. How it works

The link is self-contained: the gene set travels in the URL and the Explorer builds the network on
page load.

1. **Build the filter:** URL-encode `{"gene_names": ["PLK3", "HIPK3", ...]}` as the `filter` query
   parameter, giving `{base_url}/explorer?filter=...`. To keep only some node categories, add
   `"entity_types": ["Pathway", ...]` to the same object.
2. **Open it:** the Explorer sends the genes to `{base_url}/api/knowledge_graph`, which drops
   duplicates and builds a subnetwork of the pathways, complexes, GO terms, and other entities the
   input proteins share, then renders it.

This replaces the older two-step POST/`network_id` flow, whose id lived in one server process's
in-memory cache and broke when the page-load read hit a different worker or after a restart. A
`gene_names` link needs no shared cache, so it works on any instance.

The subnetwork is what the input entities have in common, so when you hand over the link, say what
it shows (the pathways, complexes, and other nodes connecting the proteins) instead of just pasting
a URL.

## 4. Running it

### Primary path: the `get_explorer_network` MCP tool

When the ProKN MCP server is connected, call the tool with the gene symbols:

```
get_explorer_network(gene_names=["PLK3", "HIPK3", "MAPK11", "CDK1", "CDK2"])
```

It returns `{explorer_url, gene_names}`. Give the `explorer_url` back to the user.

If the inputs aren't gene symbols, pass the ID type with `from_type` and the tool maps them for
you before building the network:

```
get_explorer_network(gene_names=["P00533", "P04637", "P42345"], from_type="ACC")
```

Mapping uses PIR's UniProt ID mapping service (a fixed lookup), and falls back to the graph's own
`search_entities` if PIR is unreachable. When `from_type` is used, the result also includes
`mapping` (which route resolved the IDs) and `unmapped` (any inputs that didn't resolve). The
`from_type` codes are the same as the script's `--from` (see `references/id-types.md`);
`GENENAME` is the default and means the inputs are already gene symbols.

To show only certain kinds of node, pass `entity_types`. For example, to see just the pathways the
proteins share:

```
get_explorer_network(gene_names=["CDK1", "CDK2", "CDK12", "MAPK8"], entity_types=["Pathway"])
```

The known types are `GOTerm`, `Complex`, `Protein`, `SubCellClass`, `Site`, `Domain`, `Pathway`,
`Variant`, `Disease`, `Isoform` and `PTMSite`. Case doesn't matter. A name outside that list is
still sent (the API may have added it), and the result includes a `warning` naming it. Leave
`entity_types` out to include every category. The result echoes the types used in `entity_types`.

### Fallback path: the bundled script

Use this only when there's no MCP server. The script does the same two steps and prints the link:

```bash
python scripts/prokn_explorer.py PLK3 HIPK3 MAPK11 CDK1 CDK2
```

Add `--open` to also open it in a browser, and `--base-url <url>` to point at a different ProKN
deployment:

```bash
python scripts/prokn_explorer.py PLK3 HIPK3 MAPK11 CDK1 CDK2 \
  --base-url https://research.bioinformatics.udel.edu/ProKN/ --open
```

If the inputs aren't gene symbols, pass `--from` with the UniProt ID-type code and the script maps
them to gene symbols before it calls ProKN:

```bash
python scripts/prokn_explorer.py P00533 P04637 P42345 --from ACC
```

`--from` defaults to `GENENAME` (inputs are already gene symbols, no mapping). The common codes and
the full ~110-type list are in `references/id-types.md`.

Add `--entity-types` to keep only some node categories, the same as the tool's `entity_types`:

```bash
python scripts/prokn_explorer.py CDK1 CDK2 CDK12 MAPK8 --entity-types Pathway
```

Either way: give the user the URL and say it opens the network in the ProKN Explorer. Don't open a
browser for them unless they ask.

## 5. Input requirements

- **ProKN needs gene symbols.** The POST body is matched against the protein `geneNames` property.
  Other IDs don't match directly, so pass `--from <code>` to map them first.
- **Mapping is best-effort.** An ID can map to several gene symbols, or to none. Unmapped inputs are
  reported, not dropped quietly.
- **Case matters.** Symbols have to be canonical (`MAPK11`, not `mapk11`). Mapped symbols already
  come back canonical.
- **Two or more symbols** (checked after any mapping).
- **`entity_types` narrows the network.** With a narrow choice (one category), the proteins may
  share nothing of that kind, and the Explorer shows "No results". Say so, and suggest dropping
  the filter or adding categories.

## 6. Example

Input: `PLK3, HIPK3, MAPK11, CDK1, CDK2`

```bash
$ python scripts/prokn_explorer.py PLK3 HIPK3 MAPK11 CDK1 CDK2
https://research.bioinformatics.udel.edu/ProKN/explorer?filter=%7B%22gene_names%22%3A%20%5B%22PLK3%22%2C%20...%5D%7D
```

Give that URL back to the user to view the network.

## 7. What to report (reproducibility)

Make each result easy to reproduce. Don't just paste a bare URL. Report:

- **The exact gene symbols sent to ProKN**, after de-duplication and (if used) mapping. This is the
  real input, and it can differ from what the user typed.
- **Any inputs that didn't map**, when `--from` was used, so the coverage is clear.
- **The skill and version** that produced it (`prokn-explorer v0.3.0`, from this file's
  `metadata.version`) and **which path you used**: the `get_explorer_network` MCP tool or the
  fallback script. When IDs were mapped, note how (PIR or the graph-search fallback). The tool
  returns this in its `mapping` field.

Say plainly if the network came back empty (the Explorer shows "No results") instead of implying the
link is broken.

When the MCP tool path is used, also save a reproducibility record, as the other ProKN skills do:

- If this step closes a `prokn-search` investigation, the `get_explorer_network` call is already in
  that session's query log. It is included when `prokn-search` calls
  `create_reproducibility_record` at the end, so don't reset the log here.
- If this skill runs on its own, call `reset_query_log` first and `create_reproducibility_record` at
  the end (with `skills="prokn-explorer v0.3.0"`). Give the user the saved file path, not the full
  record.

The fallback script doesn't go through the server, so nothing is logged. Report the items above in
the reply instead.

## 8. References (read on demand)

Extra info is in `references/` so this file stays short. Open the one you need:

- `references/id-types.md`: the ID-type codes for `--from` / `from_type` (common set and full
  list), plus the any-species and best-effort mapping caveats.
- `references/pitfalls.md`: the common failure modes and their fixes. Skim before finalizing.