#!/usr/bin/env python3
"""Send a list of gene symbols to ProKN and print an Explorer link for the network.

ProKN's /api/knowledge_graph endpoint takes the genes, builds a subnetwork of the
pathways/complexes/GO terms they share, caches it, and gives back a network_id.
Putting that id in the Explorer URL shows the network.
"""
import argparse
import json
import sys
import urllib.error
import urllib.parse
import urllib.request

DEFAULT_BASE_URL = "https://research.bioinformatics.udel.edu/ProKNTest/"


class EgressBlocked(RuntimeError):
    """Raised when the sandbox proxy blocks the request before it reaches ProKN."""


def host_of(base_url):
    return urllib.parse.urlparse(base_url).netloc or base_url


def looks_like_allowlist_block(text):
    # the proxy wording varies, so check for a few things that mean "host not allowed"
    t = (text or "").lower()
    return (
        "allowlist" in t
        or "not in allowlist" in t
        or "tunnel connection failed" in t
        or "forbidden" in t
    )


def allowlist_help(base_url):
    host = host_of(base_url)
    return (
        f"Couldn't reach {host}. The sandbox proxy blocked the request before it left, "
        f"so this is a network setting, not a ProKN problem.\n\n"
        f"To fix it inside a Claude Cowork/Code sandbox, add the host to the allowed domains:\n"
        f"  1. An org Owner opens Organization settings > Capabilities.\n"
        f"  2. Under 'Code execution and file creation', add this domain:\n"
        f"         {host}\n"
        f"     (one entry works for both the Test and production sites)\n"
        f"  3. Start a new conversation -- the setting only applies to new sessions.\n\n"
        f"If you aren't an Owner, ask an admin, or just run the script on your own machine "
        f"where there's no proxy:\n"
        f"     python scripts/prokn_explorer.py GENE1 GENE2 ..."
    )


def build_network(gene_symbols, base_url, timeout=60):
    api_url = base_url.rstrip("/") + "/api/knowledge_graph"
    body = json.dumps({"gene_names": gene_symbols}).encode("utf-8")
    req = urllib.request.Request(
        api_url,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", "replace")[:300]
        if e.code == 403 and looks_like_allowlist_block(detail):
            raise EgressBlocked(allowlist_help(base_url)) from e
        raise RuntimeError(f"ProKN returned HTTP {e.code}: {detail}") from e
    except urllib.error.URLError as e:
        reason = str(getattr(e, "reason", e))
        if looks_like_allowlist_block(reason) or "403" in reason:
            raise EgressBlocked(allowlist_help(base_url)) from e
        raise RuntimeError(f"Couldn't reach ProKN at {host_of(base_url)}: {reason}") from e

    network_id = payload.get("network_id")
    if not network_id:
        raise RuntimeError(f"No network_id came back from ProKN (got: {str(payload)[:200]})")
    return network_id


def explorer_url(network_id, base_url):
    filter_param = urllib.parse.quote(json.dumps({"network_id": network_id}))
    return base_url.rstrip("/") + f"/explorer?filter={filter_param}"


def dedupe(symbols):
    # keep the order the user gave, drop blanks and repeats
    seen = []
    for s in symbols:
        s = s.strip()
        if s and s not in seen:
            seen.append(s)
    return seen


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Show a set of ProKN proteins on the Explorer from their gene symbols."
    )
    parser.add_argument("genes", nargs="+", help="Gene symbols, e.g. PLK3 HIPK3 MAPK11 CDK1 CDK2")
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

    genes = dedupe(args.genes)
    if len(genes) < 2:
        parser.error("need at least two gene symbols -- a network needs a pair to connect")

    try:
        network_id = build_network(genes, args.base_url)
    except EgressBlocked as e:
        print(str(e), file=sys.stderr)
        return 3
    except RuntimeError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    url = explorer_url(network_id, args.base_url)
    print(url)

    if args.open_browser:
        import webbrowser
        webbrowser.open_new(url)
    return 0


if __name__ == "__main__":
    sys.exit(main())
