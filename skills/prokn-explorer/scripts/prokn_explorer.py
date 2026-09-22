#!/usr/bin/env python3
"""Print a self-contained ProKN Explorer link for a set of gene symbols.

The link carries the gene set in the URL (filter={"gene_names":[...]}). The Explorer
builds the subnetwork of the pathways/complexes/GO terms they share on page load, so
the link works on any instance without relying on a server-side network_id cache.

ProKN only matches on gene symbols, so if you have other IDs (UniProt accessions,
RefSeq, etc.) pass --from with the ID type and the script maps them to gene symbols
first, using PIR's UniProt ID mapping service.
"""
import argparse
import json
import sys
import urllib.error
import urllib.parse
import urllib.request

DEFAULT_BASE_URL = "https://research.bioinformatics.udel.edu/ProKN"
IDMAPPING_URL = "https://idmappingtest.uniprot.org/cgi-bin/idmapping_http_client3"


class EgressBlocked(RuntimeError):
    """Raised when the sandbox proxy blocks the request before it reaches ProKN."""


def host_of(url):
    return urllib.parse.urlparse(url).netloc or url


def looks_like_allowlist_block(text):
    # the proxy wording varies, so check for a few things that mean "host not allowed"
    t = (text or "").lower()
    return (
        "allowlist" in t
        or "not in allowlist" in t
        or "tunnel connection failed" in t
        or "forbidden" in t
    )


def allowlist_help(url):
    host = host_of(url)
    return (
        f"Couldn't reach {host}. The sandbox proxy blocked the request before it left, "
        f"so this is a network setting, not a server problem.\n\n"
        f"To fix it inside a Claude Cowork/Code sandbox, add the host to the allowed domains:\n"
        f"  1. Open Settings > Capabilities.\n"
        f"  2. Under 'Code execution and file creation', add this domain to the Allowlist:\n"
        f"         {host}\n"
        f"  3. Start a new conversation. The setting only applies to new sessions.\n\n"
        f"If you aren't an organization Owner, you may need to ask an Admin to change this setting."
    )


def read_url(req, ref_url, timeout):
    # preform the request; turn proxy blocks into a clear message
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read()
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", "replace")[:300]
        if e.code == 403 and looks_like_allowlist_block(detail):
            raise EgressBlocked(allowlist_help(ref_url)) from e
        raise RuntimeError(f"HTTP {e.code} from {host_of(ref_url)}: {detail}") from e
    except urllib.error.URLError as e:
        reason = str(getattr(e, "reason", e))
        if looks_like_allowlist_block(reason) or "403" in reason:
            raise EgressBlocked(allowlist_help(ref_url)) from e
        raise RuntimeError(f"Couldn't reach {host_of(ref_url)}: {reason}") from e


def map_ids_to_genes(ids, from_type, timeout=60):
    """Turn IDs into gene symbols with PIR's ID mapping service

    Uses the synchronous mode (async=NO, to=GENENAME), returns (genes, unmapped_ids).
    Response is tab-delimited "sourceID<TAB>geneName" lines, one per mapping
    """
    query = urllib.parse.urlencode({
        "from": from_type,
        "to": "GENENAME",
        "ids": ",".join(ids),
        "async": "NO",
    })
    url = f"{IDMAPPING_URL}?{query}"
    text = read_url(urllib.request.Request(url), url, timeout).decode("utf-8", "replace")

    genes = []
    matched = set()
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        parts = line.split("\t") if "\t" in line else line.split(None, 1)
        if len(parts) < 2:
            continue
        src, gene = parts[0].strip(), parts[1].strip()
        if src.lower() == "from" or gene.lower() in ("to", "genename"):
            continue  # skip a header row if the service sends one
        matched.add(src.lower())
        if gene and gene not in genes:
            genes.append(gene)
    unmapped = [i for i in ids if i.lower() not in matched]
    return genes, unmapped


def explorer_url(gene_symbols, base_url):
    # Self-contained link: the gene set travels in the URL and the Explorer builds the network on
    # page load. No POST and no per-process network_id cache, so the link works on any instance.
    filter_param = urllib.parse.quote(json.dumps({"gene_names": gene_symbols}))
    return base_url.rstrip("/") + f"/explorer?filter={filter_param}"


def dedupe(items):
    # keep the order the user gave, drop blanks and repeats
    seen = []
    for s in items:
        s = s.strip()
        if s and s not in seen:
            seen.append(s)
    return seen


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Show a set of ProKN proteins on the Explorer from gene symbols (or other IDs)."
    )
    parser.add_argument("ids", nargs="+", help="Gene symbols, e.g. PLK3 HIPK3 MAPK11 CDK1 CDK2")
    parser.add_argument(
        "--from",
        dest="from_type",
        default="GENENAME",
        help="ID type of the inputs as a UniProt mapping code. Default GENENAME, meaning the inputs are already gene symbols. "
             "Full list: " + IDMAPPING_URL + "?page=list",
    )
    parser.add_argument(
        "--base-url",
        default=DEFAULT_BASE_URL,
        help=f"ProKN base URL (default: {DEFAULT_BASE_URL})",
    )
    parser.add_argument(
        "--open",
        dest="open_browser",
        action="store_true",
        help="Also open the link in a browser",
    )
    args = parser.parse_args(argv)

    inputs = dedupe(args.ids)
    from_type = args.from_type.upper()

    try:
        if from_type == "GENENAME":
            genes = inputs
        else:
            genes, unmapped = map_ids_to_genes(inputs, from_type)
            print(f"Mapped {len(inputs)} {from_type} id(s) to {len(genes)} gene symbol(s).",
                  file=sys.stderr)
            if unmapped:
                print(f"No gene symbol for: {', '.join(unmapped)}", file=sys.stderr)
            genes = dedupe(genes)

        if len(genes) < 2:
            print("Error: need at least two gene symbols because the network needs a pair to connect.",
                  file=sys.stderr)
            return 1
    except EgressBlocked as e:
        print(str(e), file=sys.stderr)
        return 3
    except RuntimeError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    url = explorer_url(genes, args.base_url)
    print(url)

    if args.open_browser:
        import webbrowser
        webbrowser.open_new(url)
    return 0


if __name__ == "__main__":
    sys.exit(main())
