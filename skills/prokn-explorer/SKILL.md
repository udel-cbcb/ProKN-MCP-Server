---
name: prokn-explorer
description: >-
  Turn a list of gene symbols into a ProKN network and a shareable Explorer link. POSTs the
  genes to the ProKN knowledge_graph API, receives a cached network_id, and builds the
  /explorer?filter=... URL that renders the subnetwork - the pathways, complexes, and GO
  terms shared among the input proteins.
  Triggers: "show these genes/proteins on ProKN", "open a gene list in the ProKN explorer",
  "visualize a protein set as a network", or "get a ProKN Explorer link for a gene list".
compatibility: >-
  Targets a running ProKN web instance (default: the ProKNTest deployment). Requires network
  access and Python 3 (standard library only). This skill renders a network; 
  to query ProKN data itself, use the ProKN MCP server tools.
metadata:
  author: University of Delaware, Center for Bioinformatics and Computational Biology
  version: "0.1.0"
  repository: https://research.bioinformatics.udel.edu/ProKN/
  base_url: https://research.bioinformatics.udel.edu/ProKNTest/
  api_endpoint: /api/knowledge_graph
  explorer_page: /explorer
  homepage: https://research.bioinformatics.udel.edu/ProKN/
---

# ProKN Explorer link builder

## 1. What this does and when to use it

Use this skill when someone hands you a set of genes/proteins and wants to **see them as a
network** on the ProKN Explorer, rather than get data back as text or JSON. It converts a list
of gene symbols into a ProKN Explorer URL that the user can open to view the subnetwork
connecting those proteins.

If the request is instead to *read* facts about the proteins (targets, kinases, pathways,
neighbors) use the ProKN MCP server tools, NOT this skill.

## 2. How it works

Two steps against a running ProKN instance:

1. **POST** the gene symbols to `POST {base_url}/api/knowledge_graph` with body
   `{"gene_names": ["PLK3", "HIPK3", ...]}`. ProKN de-duplicates the list, builds a subnetwork
   of the **pathways, complexes, and GO terms shared among the input proteins**
   (UniProtKB proteins matched on their `geneNames` property), caches it, and returns
   `{"network_id": "<id>"}`.
2. **Build the Explorer link**: URL-encode `{"network_id": "<id>"}` as the `filter` query
   parameter -> `{base_url}/explorer?filter=<encoded>`. Opening it loads the cached network.

The Explorer's GET route resolves the `network_id` from ProKN's in-memory cache, so the link
is only valid while that cache entry lives (see Gotchas).

## 3. Running it

A helper script does both steps and prints the link:

```bash
python scripts/prokn_explorer.py PLK3 HIPK3 MAPK11 CDK1 CDK2
```

It prints the Explorer URL to stdout. Add `--open` to also launch it in a browser, and
`--base-url <url>` to point at a different ProKN deployment:

```bash
python scripts/prokn_explorer.py PLK3 HIPK3 MAPK11 CDK1 CDK2 \
  --base-url https://research.bioinformatics.udel.edu/ProKN/ --open
```

When reporting back, give the user the URL and tell them it opens the network in the ProKN
Explorer. Do not open a browser on the user's behalf without being asked.

## 4. Input requirements

- **Gene symbols only.** ProKN matches the POST body against the protein `geneNames` property.
  UniProt accessions (e.g. `P00533`), protein names, or PubChem IDs will not match. If you were
  handed those, resolve them to gene symbols first (the ProKN MCP server's `search_entities`
  tool can do this) before calling this skill.
- **Case-sensitive.** The match is exact, so pass canonical symbols as written (`MAPK11`, not
  `mapk11`).
- **Two or more symbols.** The network is built from shared nodes *between* proteins, so a
  single gene produces nothing to connect. The script rejects fewer than two.

## 5. Example

Input: `PLK3, HIPK3, MAPK11, CDK1, CDK2`

```bash
$ python scripts/prokn_explorer.py PLK3 HIPK3 MAPK11 CDK1 CDK2
https://research.bioinformatics.udel.edu/ProKNTest/explorer?filter=%7B%22network_id%22%3A%22...%22%7D
```

Hand that URL back to the user to view the network.

## 6. Gotchas

- **Cache-scoped links.** The `network_id` points at a cached network on the ProKN server. If it
  expires, the Explorer returns "Your session on ProKN expired" - just re-run the POST to mint a
  fresh id and link.
- **Empty networks are possible.** If the input proteins share no pathway, complex, or GO term,
  the POST still returns a valid `network_id`, but the Explorer shows "No results". Mention this
  rather than assuming the link is broken.
- **Environment.** The default base URL is the **Test** deployment (`.../ProKNTest/`). Switch to
  production with `--base-url https://research.bioinformatics.udel.edu/ProKN/` once validated.
- **Same graph, different access.** This skill only *renders* a network. To pull the underlying
  nodes/edges as data, use the ProKN MCP server tools (`get_subgraph`, etc.).
