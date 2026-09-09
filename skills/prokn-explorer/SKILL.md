---
name: prokn-explorer
description: >-
  Turn a list of gene symbols (or other protein IDs) into a ProKN network and a shareable
  Explorer link. POSTs the genes to the ProKN knowledge_graph API, receives a cached
  network_id, and builds the URL that renders the subnetwork. Non-gene IDs (UniProt
  accessions, RefSeq, ...) are mapped to gene symbols first.
  Triggers: "show / display / view these genes or proteins in ProKN", "visualize a 
  gene or protein set as a network or graph", "network view of these genes", 
  "make a network / subnetwork from this list", "map or show the relationships between
  these proteins as a network", "visualize how these genes are related in ProKN",
  "explore this set of genes or proteins in ProKN". Also accepts UniProt accessions, RefSeq, Ensembl 
  and other IDs (mapped to gene symbols first). NOT for reading facts as text (a protein's targets, kinases,
  pathways, evidence, or a single entity's relationships). That belongs to the ProKN MCP data tools.
compatibility: >-
  Targets a running ProKN web instance. Requires network
  access and Python 3 (standard library only). This skill renders a network;
  to query ProKN data itself, use the ProKN MCP server tools.
metadata:
  author: University of Delaware, Center for Bioinformatics and Computational Biology
  version: "0.2.0"
  repository: https://research.bioinformatics.udel.edu/ProKN/
  base_url: https://research.bioinformatics.udel.edu/ProKN/
  api_endpoint: /api/knowledge_graph
  explorer_page: /explorer
  homepage: https://research.bioinformatics.udel.edu/ProKN/
---

# ProKN Explorer link builder

## 1. What this does and when to use it

Use this skill when someone gives you a set of genes or proteins and wants to see them as a
network on the ProKN Explorer, instead of getting data back as text. It takes a list of gene
symbols and returns a ProKN Explorer URL the user can open to view the subnetwork connecting
those proteins.

If the request is to *read* facts about the proteins (targets, kinases, pathways, neighbors),
use the ProKN MCP server tools, NOT this skill.

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

Two steps against a running ProKN instance:

1. **POST** the gene symbols to `POST {base_url}/api/knowledge_graph` with body
   `{"gene_names": ["PLK3", "HIPK3", ...]}`. ProKN drops duplicates, builds a subnetwork of the
   pathways, complexes, GO terms, and other entities the input proteins share, caches it, and returns
   `{"network_id": "..."}`.
2. **Build the Explorer link:** URL-encode `{"network_id": "..."}` as the `filter` query parameter,
   giving `{base_url}/explorer?filter=...`. Opening it loads the cached network.

The subnetwork is what the input entities have in common, so when you hand over the link, say what
it shows (the pathways, complexes, and other nodes connecting the proteins) instead of just pasting
a URL.

## 4. Running it

### Primary path: the `get_explorer_network` MCP tool

When the ProKN MCP server is connected, call the tool with the gene symbols:

```
get_explorer_network(gene_names=["PLK3", "HIPK3", "MAPK11", "CDK1", "CDK2"])
```

It returns `{network_id, explorer_url, gene_names}`. Give the `explorer_url` back to the user.

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

## 6. Example

Input: `PLK3, HIPK3, MAPK11, CDK1, CDK2`

```bash
$ python scripts/prokn_explorer.py PLK3 HIPK3 MAPK11 CDK1 CDK2
https://research.bioinformatics.udel.edu/ProKN/explorer?filter=%7B%22network_id%22%3A%22...%22%7D
```

Give that URL back to the user to view the network.

## 7. What to report (reproducibility)

Make each result easy to reproduce. Don't just paste a bare URL. Report:

- **The exact gene symbols sent to ProKN**, after de-duplication and (if used) mapping. This is the
  real input, and it can differ from what the user typed.
- **Any inputs that didn't map**, when `--from` was used, so the coverage is clear.
- **The skill and version** that produced it (`prokn-explorer v0.2.0`, from this file's
  `metadata.version`) and **which path you used**: the `get_explorer_network` MCP tool or the
  fallback script. When IDs were mapped, note how (PIR or the graph-search fallback). The tool
  returns this in its `mapping` field.

Say plainly if the network came back empty (a valid `network_id` with "No results") instead of
implying the link is broken.

## 8. References (read on demand)

Extra info is in `references/` so this file stays short. Open the one you need:

- **`references/id-types.md`**: the ID-type codes for `--from` / `from_type` (common set and full
  list), plus the any-species and best-effort mapping caveats.
- **`references/pitfalls.md`**: the common failure modes and their fixes. Skim before finalizing.