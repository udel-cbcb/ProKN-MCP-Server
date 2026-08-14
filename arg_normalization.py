# =============================================================================
# Global argument normalization for ProKN tools
#
# WHY: the model keeps making up argument names (query, protein_ids, protein_name,
# perturbagen_name, identifiers, and so on) and passing strings where we want lists.
# FastMCP throws out unexpected kwargs BEFORE the tool body ever runs, so we can't
# patch this inside each tool. This middleware rewrites the arguments dict before
# validation happens: it renames known aliases to the real parameter, sends a stray
# value to the tool's primary parameter, wraps a lone string into a list, and drops
# any leftover unknown kwargs so the call goes through instead of blowing up.
#
# Two parts:
#   normalize_args(name, args): function (unit tested below and offline)
#   AliasNormalizationMiddleware: FastMCP middleware that calls it
# =============================================================================

from __future__ import annotations

# The spec for each tool:
#   valid   : the tool's real parameter names
#   primary : where to send a value we don't recognize, if primary isn't set yet
#             (None for tools with no single primary, like the two protein path)
#   lists   : params that have to be a list (a lone string gets wrapped)
#   aliases : an explicit map from alias to the real name
TOOL_ARG_SPECS: dict[str, dict] = {
    "search_entities": {
        "valid": ["term", "entity_types", "limit"],
        "primary": "term", "lists": ["entity_types"],
        "aliases": {"query": "term", "q": "term", "search": "term", "text": "term",
                    "name": "term", "entity": "term", "keyword": "term"},
    },
    "get_relationship_given_entity": {
        "valid": ["entity", "neighbor_type", "rel_type", "limit"],
        "primary": "entity", "lists": [],
        "aliases": {"entity_name": "entity", "name": "entity", "node": "entity",
                    "query": "entity", "protein": "entity", "protein_name": "entity",
                    "drug": "entity", "drug_name": "entity",
                    "relationship_type": "rel_type", "neighbor_label": "neighbor_type"},
    },
    "get_subgraph": {
        "valid": ["entity", "max_hops", "max_nodes", "node_type_filter",
                  "relationship_type_filter"],
        "primary": "entity", "lists": ["node_type_filter", "relationship_type_filter"],
        "aliases": {"entity_name": "entity", "name": "entity", "query": "entity",
                    "hops": "max_hops", "depth": "max_hops",
                    "node_types": "node_type_filter",
                    "relationship_types": "relationship_type_filter",
                    "rel_types": "relationship_type_filter"},
    },
    "get_drugs_mechanisms": {
        "valid": ["drug_identifiers", "action_type", "ec_filter"],
        "primary": "drug_identifiers", "lists": ["drug_identifiers"],
        "aliases": {"identifiers": "drug_identifiers", "drugs": "drug_identifiers",
                    "drug": "drug_identifiers", "drug_ids": "drug_identifiers",
                    "drug_name": "drug_identifiers", "actionType": "action_type",
                    "action": "action_type"},
    },
    "get_genes_regulated_by_drugs": {
        "valid": ["drug_identifiers"],
        "primary": "drug_identifiers", "lists": ["drug_identifiers"],
        "aliases": {"identifiers": "drug_identifiers", "drugs": "drug_identifiers",
                    "drug": "drug_identifiers", "drug_name": "drug_identifiers",
                    "compound": "drug_identifiers"},
    },
    "get_protein_interactions": {
        # the model's variants (protein_name, protein_ids, proteins=[a,b], and so on)
        # all get funneled into these by the dedicated two protein handler in normalize_args().
        "valid": ["protein1", "protein2"],
        "primary": None, "lists": [],
        "aliases": {},
        "two_proteins": True,
    },
    "get_phosphosites_catalyzed_by_proteins": {
        "valid": ["proteins"],
        "primary": "proteins", "lists": ["proteins"],
        "aliases": {"protein_name": "proteins", "protein": "proteins",
                    "protein_ids": "proteins", "protein_list": "proteins",
                    "kinases": "proteins", "kinase": "proteins"},
    },
    "get_pathways_between_protein_sets": {
        "valid": ["proteins1", "proteins2"],
        "primary": None, "lists": ["proteins1", "proteins2"],
        "aliases": {"set1": "proteins1", "set2": "proteins2",
                    "proteins_1": "proteins1", "proteins_2": "proteins2",
                    "source_proteins": "proteins1", "target_proteins": "proteins2",
                    "protein_set_1": "proteins1", "protein_set_2": "proteins2"},
    },
    "get_proteins_catalyzing_sites": {
        "valid": ["phosphosites", "ec_filter"],
        "primary": "phosphosites", "lists": ["phosphosites"],
        "aliases": {"sites": "phosphosites", "site": "phosphosites",
                    "phosphosite": "phosphosites", "site_ids": "phosphosites",
                    "site_labels": "phosphosites",
                    "ecNumber": "ec_filter", "ec_number": "ec_filter", "ec": "ec_filter"},
    },
    "get_phosphosites_regulated_by_perturbagen": {
        "valid": ["perturbagen", "threshold", "direction"],
        "primary": "perturbagen", "lists": [],
        "aliases": {"perturbagen_name": "perturbagen", "term": "perturbagen",
                    "name": "perturbagen", "drug": "perturbagen",
                    "compound": "perturbagen", "dir": "direction"},
    },
    "get_proteins_encoded_by_genes": {
        "valid": ["gene_symbols"],
        "primary": "gene_symbols", "lists": ["gene_symbols"],
        "aliases": {"genes": "gene_symbols", "gene": "gene_symbols",
                    "gene_names": "gene_symbols", "symbols": "gene_symbols"},
    },
    "filter_proteins_by_ec_number": {
        "valid": ["proteins", "ec_filter"],
        "primary": "proteins", "lists": ["proteins"],
        "aliases": {"protein_list": "proteins", "protein_name": "proteins",
                    "ec_number": "ec_filter", "ec": "ec_filter"},
    },
    "execute_read_only_cypher": {
        "valid": ["query"],
        "primary": "query", "lists": [],
        "aliases": {"cypher": "query", "q": "query", "statement": "query"},
    },
    "get_queries": {
        "valid": ["name_of_tool"],
        "primary": "name_of_tool", "lists": [],
        "aliases": {"tool": "name_of_tool", "tool_name": "name_of_tool",
                    "name": "name_of_tool"},
    },
    
}

# Any key the model has used (or might plausibly use) to pass proteins to the
# two protein path tool. All of these funnel into protein1 and protein2.
_TWO_PROTEIN_KEYS = ["protein1", "protein2", "proteins", "protein_ids",
                     "protein_list", "proteins_list", "protein_name", "protein"]


def _funnel_two_proteins(args: dict) -> dict:
    """Collect protein values from any key/shape into protein1 + protein2."""
    vals = []
    for k in _TWO_PROTEIN_KEYS:
        v = args.get(k)
        if isinstance(v, str) and v.strip():
            vals.append(v.strip())
        elif isinstance(v, (list, tuple)):
            vals.extend(str(x).strip() for x in v if str(x).strip())
    seen, uniq = set(), []
    for x in vals:
        if x.lower() not in seen:
            seen.add(x.lower())
            uniq.append(x)
    out = {}
    if len(uniq) >= 1:
        out["protein1"] = uniq[0]
    if len(uniq) >= 2:
        out["protein2"] = uniq[1]
    return out

def normalize_args(name: str, args: dict, specs: dict = TOOL_ARG_SPECS) -> dict:
    """Rewrite an arguments dict so a mis-named/over-specified call still validates.

    Order: keep valid params -> rename known aliases -> route one leftover value to
    the primary param (if still unset) -> coerce list params -> drop the rest.
    Unknown tools pass through unchanged.
    """
    spec = specs.get(name)
    if not spec or not isinstance(args, dict):
        return dict(args) if isinstance(args, dict) else args

    # Special case: the two protein path tool needs its values funneled into
    # protein1 and protein2 no matter what key or shape they arrived in.
    if spec.get("two_proteins"):
        return _funnel_two_proteins(args)

    valid = set(spec["valid"])
    aliases = spec.get("aliases", {})
    primary = spec.get("primary")
    lists = set(spec.get("lists", []))

    out: dict = {}
    leftovers: dict = {}
    for k, v in args.items():
        if k in valid:
            out[k] = v
        elif k in aliases:
            out.setdefault(aliases[k], v)
        else:
            leftovers[k] = v

    # Send a single stray value over to the primary param if it's still unset
    if primary and primary not in out:
        for k, v in leftovers.items():
            if v not in (None, "", [], {}):
                out[primary] = v
                break

    # Coerce the list params: a lone string or number becomes a one item list
    for lp in lists:
        if lp in out and not isinstance(out[lp], (list, tuple)):
            out[lp] = [out[lp]]

    return out

def normalize_call(name: str, args: dict, specs: dict = TOOL_ARG_SPECS) -> tuple[str, dict]:
    """Normalize args AND, when needed, redirect to a better-fitting tool.

    Returns (tool_name, args). Most calls keep their name unchanged. The
    two-protein interaction tool, when given only ONE protein, is redirected to
    get_relationship_given_entity (a single-entity neighbor lookup) instead of
    raising a 'protein2 missing' validation error
    """
    new_args = normalize_args(name, args, specs)
    if name == "get_protein_interactions" and "protein2" not in new_args:
        entity = new_args.get("protein1")
        if entity:
            return "get_relationship_given_entity", {"entity": entity}
    return name, new_args

# FastMCP middleware wrapper: on_call_tool fires before the tool handler validates args
try:
    from fastmcp.server.middleware import Middleware  # type: ignore

    class AliasNormalizationMiddleware(Middleware):
        """Normalizes tool-call arguments before FastMCP validates them."""

        def __init__(self, specs: dict = TOOL_ARG_SPECS):
            self.specs = specs
        async def on_call_tool(self, context, call_next):
            msg = getattr(context, "message", None)
            args = getattr(msg, "arguments", None)
            if msg is not None and isinstance(args, dict):
                try:
                    new_name, new_args = normalize_call(msg.name, dict(args), self.specs)
                    msg.name = new_name
                    msg.arguments = new_args
                except Exception:  # never let normalization break a call
                    pass
            return await call_next(context)
except Exception: 
    AliasNormalizationMiddleware = None  
