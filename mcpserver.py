import os
from fastmcp import FastMCP
from arg_normalization import AliasNormalizationMiddleware
import neo4j
from queries import (

    QUERY_SEARCH_ENTITIES,

    QUERY_GET_GRAPH_ONTOLOGY,
    QUERY_GET_NODE_PROPERTIES,
    QUERY_GET_RELATIONSHIP_PROPERTIES,
    
    QUERY_GET_PROTEINS_CATALYZING_SITES,
    QUERY_GET_PHOSPHOSITES_CATALYZED_BY_PROTEINS,
    QUERY_GET_DRUGS_MECHANISMS,
    QUERY_PHOSPHOSITES_REGULATED_BY_PERTURBAGEN_TEMPLATE,

    QUERY_GET_GENES_REGULATED_BY_DRUGS,
    QUERY_GET_PROTEINS_ENCODED_BY_GENES,
    QUERY_FILTER_PROTEINS_BY_EC,
    QUERY_GET_PROTEIN_INTERACTIONS,
    QUERY_GET_PATHWAYS_BETWEEN_PROTEIN_SETS,
    QUERY_GET_RELATIONSHIP_GIVEN_ENTITY,
    QUERY_RESOLVE_ENTITY_COUNT,

    QUERY_GET_SUBGRAPH_TEMPLATE,
)
import sys
import time
import re
import json
import urllib.request
import urllib.parse
import urllib.error
from typing import Annotated
from pydantic import Field

mcp = FastMCP(
    "ProKN-MCP-Server",
    instructions="""
    A read-only MCP Server for the ProKN (Protein Knowledge Network) Knowledge Graph,
    https://research.bioinformatics.udel.edu/ProKN (point users there for detail).

    CRITICAL INSTRUCTIONS:
        1. Prefer specific task tools: Each answers one biological question (e.g. a drug's
            targets, a site's kinase, an entity's neighbors, paths between proteins). Use the
            raw query tool (execute_read_only_cypher) only when no task tool can express the
            question. It is a last resort, not a shortcut.
        2. Entities resolve automatically: The tools accept entities such as common names, gene 
            symbols, accessions and IDs and match them for you. If a tool reports it could not 
            find an entity, follow the guidance it returns to resolve the name and retry. Do not 
            switch to a raw query.
        3. Cite evidence: ProKN stores provenance on relationships. When you report a
            connection, cite the evidence from the edge: list PMIDs if present, otherwise name
            the source database (SAB / dcc). If an edge carries no provenance, say so.
        4. Present complete, honest results: Report all biologically relevant findings; for
            large result sets, summarize and surface the most significant rows rather than
            silently dropping data. Keep domain abbreviations as written.
        5. Briefly explain your approach in biological terms before acting.
    """
)

mcp.add_middleware(AliasNormalizationMiddleware())

NEO4J_URI = os.environ.get("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USERNAME = os.environ.get("NEO4J_USERNAME", "neo4j")
NEO4J_PASSWORD = os.environ.get("NEO4J_PASSWORD", "password")

# URLs used only by get_explorer_network: the ProKN web app for buidling Explorer links,
#  and PIR's UniProt ID mapping service it uses to
# turn non-gene IDs into gene symbols.
PROKN_WEB_BASE_URL = os.environ.get(
    "PROKN_WEB_BASE_URL", "https://research.bioinformatics.udel.edu/ProKN/"
)
PROKN_IDMAPPING_URL = os.environ.get(
    "PROKN_IDMAPPING_URL",
    "https://idmappingtest.uniprot.org/cgi-bin/idmapping_http_client3",
)

driver = neo4j.GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USERNAME, NEO4J_PASSWORD))

def verify_neo4j_connection(retries: int = 5, delay: float = 2.0) -> bool:
    """Block until Neo4j is reachable, or give up after `retries` attempts.

    Called at server startup (in __main__), NOT at import time, so the module can
    be imported for unit testing without a running database.
    """
    print(f"Testing connection to Neo4j at {NEO4J_URI}...", file=sys.stderr)
    for i in range(retries):
        try:
            driver.verify_connectivity()
            print("Neo4j connection successful!", file=sys.stderr)
            return True
        except Exception:
            print(f"Waiting for Neo4j... ({i + 1}/{retries})", file=sys.stderr)
            time.sleep(delay)
    print(f"Failed to connect to Neo4j at {NEO4J_URI}. Check NEO4J_URI.", file=sys.stderr)
    return False

# Main helper function to run Cypher queries
def _run(cypher: str, params: dict = {}, limit: int = 500, timeout: float = 60.0):
    """Execute a read-only Cypher query and return rows as plain dicts."""
    # Ensure there's a LIMIT in the query or use the parameter
    if "LIMIT" not in cypher.upper():
        cypher = f"{cypher} LIMIT {limit}"

    with driver.session(default_access_mode=neo4j.READ_ACCESS) as session:
        with session.begin_transaction(timeout=timeout) as tx:
            result = tx.run(cypher, **params)
            return [record.data() for record in result]


def _run_introspection(cypher: str, what: str, timeout: float = 30.0):
    """Run a schema-introspection query, returning a guidance message instead of
    raising if it times out or errors. The db.schema.* procedures scan the entire
    store and can exceed the timeout on a large graph like ProKN."""
    try:
        return _run(cypher, timeout=timeout)
    except Exception as e:
        return (f"Could not retrieve {what}: the schema procedure timed out or errored "
                f"on this graph (it scans the entire store). Use get_graph_schema() for the "
                f"node/relationship-type overview instead. ({type(e).__name__})")

# Cypher keywords that mutate the graph. Matched as whole words
# so a read query mentioning a property like `createdAt` or a
# label like `:Dropoff` is not falsely rejected the way a naive substring check was
_WRITE_RE = re.compile(
    r"(?<![\w.])(?:CREATE|MERGE|SET|DELETE|REMOVE|DROP)\b", re.IGNORECASE
)

def _is_write_query(query: str) -> bool:
    """True if the Cypher contains a graph-mutating keyword as a whole word."""
    return bool(_WRITE_RE.search(query or ""))

# Procedures/clauses that are technically read-only but can still touch the file
# system, network, or DBMS. Rejected on this public read-only endpoint.
_FORBIDDEN_PROC_RE = re.compile(
    r"(?:\bLOAD\s+CSV\b"
    r"|\bapoc\.(?:load|export|import|trigger|periodic|refactor|create|merge|cypher\.run)"
    r"|\bdbms\.)",
    re.IGNORECASE,
)

def _is_forbidden_query(query: str) -> bool:
    """True if the query writes OR invokes a forbidden procedure (file/network/DBMS
    access, e.g. LOAD CSV, apoc.load/export, dbms.*)."""
    return _is_write_query(query) or bool(_FORBIDDEN_PROC_RE.search(query or ""))

# ---------------------------------------------------------------------------
# UTILITIES
# ---------------------------------------------------------------------------

@mcp.tool()
def search_entities(
    term: Annotated[str, Field(description="Name, gene symbol, drug name, accession, disease, pathway, or PubChem CID to resolve. Case-insensitive substring, e.g. 'EGFR', 'alpelisib', 'P00533'.")],
    entity_types: Annotated[list[str], Field(description="Optional node labels to restrict to (e.g. ['Protein'], ['Drug','Compound']). Empty searches all types; do not pre-filter unless the user clearly wants one type.")] = [],
    limit: Annotated[int, Field(description="Max results, 1-50 (default 20), best matches first.")] = 20,
) -> list[dict] | str:
    """Resolve a name, symbol, ID, or accession to the matching ProKN node(s).

    USE THIS TOOL to turn a user's wording into an exact entity, or whenever another
    tool reports it could not find one. Searches all types and properties, ranked
    exact > prefix > substring.

    Returns rows of {node_type, name, identifiers, match_rank}; `identifiers` is a
    compact map of usable IDs to feed the next tool. Returns a guidance message if
    nothing matches.
    """
    t = (term or "").strip().lower()
    if len(t) < 2:
        return "Error: 'term' must be at least 2 characters. Provide a name, symbol, ID, or accession."
 
    try:
        limit = max(1, min(int(limit), 50))
    except (TypeError, ValueError):
        limit = 20
    types = [s.strip().lower() for s in (entity_types or []) if s and s.strip()]
    rows = _run(QUERY_SEARCH_ENTITIES, params={
        "t": t,
        "entity_types": types,
        "limit": limit,
    })
    if rows:
        return rows
 
    hint = f"No entities found matching '{term}'."
    if types:
        hint += (f" Note you restricted to {entity_types}; retry with entity_types=[] "
                 f"to search all types.")
    else:
        hint += " Try a shorter or alternative term (e.g. a gene symbol or accession)."
    return hint

# ---------------------------------------------------------------------------
# GRANULAR TOOLS (Individual Queries)
# ---------------------------------------------------------------------------
# ---------------------------------------------------------------------------
@mcp.tool()
def get_phosphosites_regulated_by_perturbagen(
    perturbagen: Annotated[str, Field(description="Perturbagen name, LINCS pertIname, or PubChem CID.")],
    threshold: Annotated[float, Field(description="Minimum |log2Ratio| change (default 1.0); lower to widen.")] = 1.0,
    direction: Annotated[str, Field(description="'up', 'down', or 'both' (default 'both').")] = "both",
) -> list[dict] | str:
    """Phosphosites a perturbagen up/downregulates, from LINCS P100.

    USE THIS TOOL for "what phosphosites does <drug/perturbagen> change?". Chain the
    returned site labels into get_proteins_catalyzing_sites to find the kinases.

    Returns rows of {measured_site_name, measured_site_id, log2_ratio,
    perturbagen_label, pubchemCId}, or a guidance message if nothing matches.
    """
    pert = (perturbagen or "").strip()
    if not pert:
        return "Error: 'perturbagen' is required (a name, LINCS pertIname, or PubChem CID)."
    direction = (direction or "both").strip().lower()
    if direction not in ("up", "down", "both"):
        return "Error: direction must be exactly 'up', 'down', or 'both'."
    try:
        threshold = abs(float(threshold))
    except (TypeError, ValueError):
        threshold = 1.0
    rows = _run(QUERY_PHOSPHOSITES_REGULATED_BY_PERTURBAGEN_TEMPLATE, params={
        "perturbagen": pert, "threshold": threshold, "direction": direction})
    if rows:
        return rows
    return (f"No {direction if direction != 'both' else ''} phosphosite changes "
            f"(|log2Ratio| >= {threshold}) found for '{pert}'. Confirm it's a LINCS "
            f"P100 perturbagen via search_entities, or lower the threshold.")

@mcp.tool()
def get_proteins_catalyzing_sites(
    phosphosites: Annotated[list[str], Field(description="PTM-site labels (e.g. ['AKT1_S473']), as returned by other tools.")],
    ec_filter: Annotated[str, Field(description="EC-number regex for the catalyzing protein. Default '2.7.*' = kinases; pass '.*' for any enzyme.")] = "2.7.*",
) -> list[dict] | str:
    """Kinases/enzymes that catalyze the given phosphosites (iPTMnet CATALYZES edges).

    USE THIS TOOL for "which kinase phosphorylates <site>?". The inverse (sites a
    kinase catalyzes) is get_phosphosites_catalyzed_by_proteins.

    Returns rows of {site_label, protein_symbol, protein_name, ec_number, evidence},
    or a guidance message if nothing matches.
    """
    sites = [str(s).strip() for s in phosphosites if str(s).strip()]
    if not sites:
        return "Error: 'phosphosites' is required (a list of PTM-site labels)."
    rows = _run(QUERY_GET_PROTEINS_CATALYZING_SITES,
                params={"site_labels": sites, "ec_filter": (ec_filter or ".*").strip()})
    if rows:
        return rows
    return (f"No catalyzing proteins found for {sites} (ec_filter='{ec_filter}'). "
            f"Confirm the exact site labels, or widen ec_filter to '.*'.")

@mcp.tool()
def get_phosphosites_catalyzed_by_proteins(
    proteins: Annotated[list[str], Field(description="Kinase/protein names or symbols, e.g. ['CDK1','MAPK1']. A single string is accepted.")],
) -> list[dict] | str:
    """Phosphosites catalyzed by the given kinase(s)/protein(s), from iPTMnet.

    USE THIS TOOL for "which sites does <kinase> phosphorylate?". The inverse (kinases
    for a given site) is get_proteins_catalyzing_sites.

    Returns rows of {protein, ec_number, all_catalyzed_sites}, or a guidance message
    if nothing matches.
    """
    ids = [str(s).strip().lower() for s in proteins if str(s).strip()]
    if not ids:
        return "Error: 'proteins' is required, e.g. [\"CDK1\"]."
    rows = _run(QUERY_GET_PHOSPHOSITES_CATALYZED_BY_PROTEINS, params={"protein_list": ids})
    if rows:
        return rows
    return (f"No catalyzed phosphosites found for {ids}. Confirm the kinase "
            f"name/symbol with search_entities (this uses iPTMnet CATALYZES edges).")

@mcp.tool()
def get_drugs_mechanisms(
    drug_identifiers: Annotated[list[str], Field(description="Drug names or PubChem CIDs, e.g. ['lapatinib'] or ['208908']. A single string is accepted.")],
    action_type: Annotated[str, Field(description="Filter by mechanism action, e.g. 'INHIBITOR'. Empty = all actions.")] = "",
    ec_filter: Annotated[str, Field(description="EC-number regex for targets. Default '2.7.*' = kinase targets only; pass '' for all targets.")] = "2.7.*",
) -> list[dict] | str:
    """Pharmacological mechanisms (protein targets) of the given drug(s).

    USE THIS TOOL for "what does <drug> target/inhibit?"; set action_type='INHIBITOR'
    for inhibited kinases. For genes a drug regulates, use get_genes_regulated_by_drugs.

    Returns rows of {drug_name, protein_label, protein_name, ec_number, relation_type,
    action, evidence}, where `evidence` holds the edge provenance (PMIDs / SAB / dcc).
    Returns a guidance message if nothing matches.
    """
    ids = [str(s).strip().lower() for s in drug_identifiers if str(s).strip()]
    if not ids:
        return "Error: 'drug_identifiers' is required, e.g. [\"lapatinib\"] or a PubChem CID."
    rows = _run(QUERY_GET_DRUGS_MECHANISMS, params={
        "drug_identifiers": ids,
        "action_type": (action_type or "").strip(),
        "ec_filter": (ec_filter or "").strip(),
    })
    if rows:
        return rows
 
    msg = f"No {'kinase ' if (ec_filter or '').strip() else ''}mechanisms found for {ids}"
    if action_type:
        msg += f" with action_type='{action_type}'"
    msg += (". Confirm the drug name/CID with search_entities, or widen the search: "
            "ec_filter='' for non-kinase targets, action_type='' for all actions.")
    return msg

@mcp.tool()
def get_genes_regulated_by_drugs(
    drug_identifiers: Annotated[list[str], Field(description="Drug names or PubChem CIDs, e.g. ['cc-401']. A single string is accepted.")],
) -> list[dict] | str:
    """Genes positively or negatively regulated by the given drug(s) (transcriptomics).

    USE THIS TOOL for "what genes does <drug> up/downregulate?". Returns ALL regulated
    genes; to narrow to kinases, feed the symbols to get_proteins_encoded_by_genes then
    filter_proteins_by_ec_number.

    Returns rows of {input_drug, gene_symbol, regulation_type, strength, evidence}, or
    a guidance message if nothing matches.
    """
    ids = [str(s).strip().lower() for s in drug_identifiers if str(s).strip()]
    if not ids:
        return "Error: 'drug_identifiers' is required, e.g. [\"cc-401\"] or a PubChem CID."
    rows = _run(QUERY_GET_GENES_REGULATED_BY_DRUGS, params={"drug_identifiers": ids})
    if rows:
        return rows
    return (f"No gene-regulation records found for {ids}. Confirm the drug name/CID "
            f"with search_entities (this data comes from transcriptomics profiling, "
            f"so not every drug is covered).")

@mcp.tool()
def get_proteins_encoded_by_genes(
    gene_symbols: Annotated[list[str], Field(description="Gene symbols or names, e.g. ['EGFR','TP53'].")],
) -> list[dict] | str:
    """Proteins encoded by the given genes (IS_PROTEIN / ENCODES edges).

    USE THIS TOOL for "what protein does gene <X> encode?".

    Returns rows of {gene_symbol, protein_name, full_name, ec_number}, or a guidance
    message if nothing matches.
    """
    genes = [str(s).strip() for s in gene_symbols if str(s).strip()]
    if not genes:
        return "Error: 'gene_symbols' is required, e.g. [\"EGFR\"]."
    rows = _run(QUERY_GET_PROTEINS_ENCODED_BY_GENES, params={"gene_symbols": genes})
    if rows:
        return rows
    return f"No proteins found for genes {genes}. Confirm the symbols with search_entities."

@mcp.tool()
def filter_proteins_by_ec_number(
    proteins: Annotated[list[str], Field(description="Protein names/symbols to filter, e.g. ['EGFR','GAPDH'].")],
    ec_filter: Annotated[str, Field(description="EC-number regex. Default '2.7.*' keeps kinases only.")] = "2.7.*",
) -> list[dict] | str:
    """Keep only the proteins in a given enzyme class (EC-number regex).

    USE THIS TOOL to narrow a protein list to an enzyme class, e.g. kinases (2.7.*).

    Returns the matching subset as {protein_name, full_name, ec_number}, or a guidance
    message if none match.
    """
    ids = [str(s).strip() for s in proteins if str(s).strip()]
    if not ids:
        return "Error: 'proteins' is required (a list of protein names/symbols)."
    rows = _run(QUERY_FILTER_PROTEINS_BY_EC,
                params={"proteins": ids, "ec_filter": (ec_filter or "2.7.*").strip()})
    if rows:
        return rows
    return f"None of {ids} matched EC filter '{ec_filter}'." 


@mcp.tool()
def get_protein_interactions(
    protein1: Annotated[str, Field(description="First protein name/symbol.")],
    protein2: Annotated[str, Field(description="Second protein name/symbol.")],
) -> list[dict] | str:
    """Shortest path connecting TWO proteins (max 3 hops, via proteins/pathways/
    complexes/GO terms).

    USE THIS TOOL for "how are <A> and <B> connected?". Needs exactly two proteins;
    for a single protein's neighbors use get_relationship_given_entity.

    Returns rows of {interaction_path, path_length}, or a guidance message if no path
    is found within 3 hops.
    """
    p1, p2 = (protein1 or "").strip(), (protein2 or "").strip()
    if not p1 or not p2:
        return ("Error: get_protein_interactions needs TWO proteins (protein1 and "
                "protein2). For a single protein's interactors, use "
                "get_relationship_given_entity(entity=...).")
    rows = _run(QUERY_GET_PROTEIN_INTERACTIONS, params={"protein1": p1, "protein2": p2})
    if rows:
        return rows
    return (f"No path (within 3 hops) found between '{p1}' and '{p2}'. Confirm both "
            f"names with search_entities; longer paths need execute_read_only_cypher.")

@mcp.tool()
def get_pathways_between_protein_sets(
    proteins1: Annotated[list[str], Field(description="First set of protein names/symbols.")],
    proteins2: Annotated[list[str], Field(description="Second set of protein names/symbols.")],
) -> list[dict] | str:
    """Pathways bridging two protein sets (via PARTICIPATES_IN / PATHWAY_EVENT_OF, up to 3 hops).

    USE THIS TOOL for "what pathways connect set A and set B?".

    Returns rows of {protein1, connecting_pathways, protein2}, or a guidance message if
    the sets share no pathways within 3 hops.
    """
    s1 = [str(s).strip() for s in proteins1 if str(s).strip()]
    s2 = [str(s).strip() for s in proteins2 if str(s).strip()]
    if not s1 or not s2:
        return "Error: both 'proteins1' and 'proteins2' are required (lists of proteins)."
    rows = _run(QUERY_GET_PATHWAYS_BETWEEN_PROTEIN_SETS, params={"proteins1": s1, "proteins2": s2})
    if rows:
        return rows
    return (f"No bridging pathways found between {s1} and {s2}. Confirm names with "
            f"search_entities; the sets may not share pathways within 3 hops.")

# ---------------------------------------------------------------------------
@mcp.tool()
def execute_read_only_cypher(
    query: Annotated[str, Field(description="A read-only Cypher MATCH/RETURN query. Write keywords and file/network/DBMS procedures are rejected.")],
) -> list[dict] | str:
    """LAST RESORT: run a custom read-only Cypher MATCH/RETURN query when NO task tool fits.

    USE THIS TOOL only when no purpose-built tool covers the question; the specialists are
    more reliable and need no Cypher. Write keywords and file/network/DBMS procedures
    (LOAD CSV, apoc.load/export, dbms.*) are rejected. Cite edge evidence and include the
    query you ran when reporting results.

    Returns up to 200 result records as dicts, or an Error/execution message.
    """
    if _is_forbidden_query(query):
        return ("Error: only read-only MATCH/RETURN Cypher is allowed. Write keywords and "
                "file/network/DBMS procedures (LOAD CSV, apoc.load/export, dbms.*) are rejected.")
    try:
        with driver.session(default_access_mode=neo4j.READ_ACCESS) as session:
            with session.begin_transaction(timeout=30.0) as tx:
                result = tx.run(query)
                return [record.data() for record in result][:200]
    except Exception as e:
        return f"Cypher Execution Error: {str(e)}"

@mcp.tool()
def get_graph_schema() -> list[dict] | str:
    """Node -> relationship -> node schema of the ProKN graph.

    USE THIS TOOL first to learn valid node labels and relationship types before other
    tools or a raw Cypher query.

    Returns rows of {Schema}, one per distinct node-relationship-node pattern.
    """
    return _run(QUERY_GET_GRAPH_ONTOLOGY)

@mcp.tool()
def get_relationship_properties() -> list[dict] | str:
    """Property names carried by each relationship type.

    USE THIS TOOL to learn what edge properties exist. May return a guidance message
    if the schema procedure times out on this large graph.

    Returns rows of {relType, props}.
    """
    return _run_introspection(QUERY_GET_RELATIONSHIP_PROPERTIES, "relationship properties")

@mcp.tool()
def get_node_properties() -> list[dict] | str:
    """Property names carried by each node label.

    USE THIS TOOL to learn what node properties exist. May return a guidance message
    if the schema procedure times out on this large graph.

    Returns rows of {nodeName, properties}.
    """
    return _run_introspection(QUERY_GET_NODE_PROPERTIES, "node properties")

@mcp.tool()
def get_queries(
    name_of_tool: Annotated[str, Field(description="Exact tool name whose underlying Cypher to return, e.g. 'get_subgraph'.")],
) -> str:
    """Return the underlying Cypher a given tool runs (for transparency).

    USE THIS TOOL when a user asks what a tool does under the hood. Pass an exact tool
    name; an unknown name returns the list of valid tool names.

    Returns the query string, or a message listing available tools.
    """
    
    # dict: tool_name -> query_template
    tool_queries = {
        "search_entities": QUERY_SEARCH_ENTITIES,
        "get_phosphosites_regulated_by_perturbagen": QUERY_PHOSPHOSITES_REGULATED_BY_PERTURBAGEN_TEMPLATE,
        "get_proteins_catalyzing_sites": QUERY_GET_PROTEINS_CATALYZING_SITES,
        "get_phosphosites_catalyzed_by_proteins": QUERY_GET_PHOSPHOSITES_CATALYZED_BY_PROTEINS,
        "get_relationship_properties": QUERY_GET_RELATIONSHIP_PROPERTIES,
        "get_node_properties": QUERY_GET_NODE_PROPERTIES,
        "get_graph_schema": QUERY_GET_GRAPH_ONTOLOGY,
        "get_drugs_mechanisms": QUERY_GET_DRUGS_MECHANISMS,
        "get_genes_regulated_by_drugs": QUERY_GET_GENES_REGULATED_BY_DRUGS,
        "get_proteins_encoded_by_genes": QUERY_GET_PROTEINS_ENCODED_BY_GENES,
        "filter_proteins_by_ec_number": QUERY_FILTER_PROTEINS_BY_EC,
        "get_protein_interactions": QUERY_GET_PROTEIN_INTERACTIONS,
        "get_pathways_between_protein_sets": QUERY_GET_PATHWAYS_BETWEEN_PROTEIN_SETS,
        "get_relationship_given_entity": QUERY_GET_RELATIONSHIP_GIVEN_ENTITY,
        "get_subgraph": QUERY_GET_SUBGRAPH_TEMPLATE
    }
    key = (name_of_tool or "").strip()
    match = tool_queries.get(key) or tool_queries.get(
        {k.lower(): k for k in tool_queries}.get(key.lower(), ""))
    if match:
        return match
    return (f"Tool '{name_of_tool}' has no static query on file. "
            f"Available: {', '.join(sorted(tool_queries))}.")

@mcp.tool()
def get_relationship_given_entity(
    entity: Annotated[str, Field(description="Name, label, gene symbol, accession, or nodeId of the entity. Case-insensitive, e.g. 'EGFR', 'P00533'.")],
    neighbor_type: Annotated[str, Field(description="Optional: keep only neighbors of this node label (e.g. 'Drug', 'Pathway'). Empty = all.")] = "",
    rel_type: Annotated[str, Field(description="Optional: keep only this relationship type (e.g. 'HAS_MECHANISM'). Empty = all.")] = "",
    limit: Annotated[int, Field(description="Max neighbors, 1-500 (default 50).")] = 50,
) -> list[dict] | str:
    """A single entity's immediate neighbors, with direction and edge evidence.

    USE THIS TOOL for one-hop neighborhood questions about ONE entity (e.g. "what drugs
    target EGFR?", "what is TP53 connected to?"). For a path between two proteins use
    get_protein_interactions; for a bounded multi-hop neighborhood use get_subgraph.
    When several nodes share a name, it picks the best-matched, most-connected one.

    Returns rows of {source_type, source_name, direction, relationship_type,
    neighbor_type, neighbor_name, evidence}. If the entity is not found, returns a
    message telling you to resolve it with search_entities first.
    """
    entity = (entity or "").strip()
    if not entity:
        return "Error: 'entity' is required. Provide a name, gene symbol, accession, or nodeId."
 
    # Clamp the limit to a sane range so the agent can't request a huge dump
    try:
        limit = max(1, min(int(limit), 500))
    except (TypeError, ValueError):
        limit = 50
 
    rows = _run(QUERY_GET_RELATIONSHIP_GIVEN_ENTITY, params={
        "entity": entity,
        "neighbor_type": (neighbor_type or "").strip(),
        "rel_type": (rel_type or "").strip(),
        "limit": limit,
    })
    if rows:
        return rows
 
    # Empty result: diagnose WHY, and tell the agent what to do next.
    check = _run(QUERY_RESOLVE_ENTITY_COUNT, params={"entity": entity})
    total = check[0]["total"] if check else 0
    if total == 0:
        return (f"No entity found matching '{entity}'. Resolve the exact name with "
                f"search_entities('{entity}'), then retry with the matched label.")
 
    msg = f"Entity '{entity}' was found, but it has no neighbors"
    filters = []
    if neighbor_type:
        filters.append(f"neighbor_type='{neighbor_type}'")
    if rel_type:
        filters.append(f"rel_type='{rel_type}'")
    if filters:
        msg += (f" matching {', '.join(filters)}. Remove the filter(s) or call "
                f"get_graph_schema() to confirm valid relationship/neighbor types.")
    else:
        msg += " in the graph."
    return msg

@mcp.tool()
def get_subgraph(
    entity: Annotated[str, Field(description="Name, label, symbol, accession, or nodeId of the start entity. Case-insensitive.")],
    max_hops: Annotated[int, Field(description="Traversal depth, integer 1-4 (default 1); keep small for hubs.")] = 1,
    max_nodes: Annotated[int, Field(description="Max neighbors returned, 1-200 (default 50), nearest first.")] = 50,
    node_type_filter: Annotated[list[str], Field(description="Optional end-node labels to keep (e.g. ['Protein','Gene']). Case-sensitive; empty = all.")] = [],
    relationship_type_filter: Annotated[list[str], Field(description="Optional relationship types to traverse (e.g. ['CATALYZES']). Empty = all.")] = [],
) -> str:
    """Fetch a bounded neighborhood radiating from ONE start entity.
 
    Use this for "what's around X within a few hops?" For a single hop with simple
    filters, prefer get_relationship_given_entity (cheaper). For a path BETWEEN two
    specific proteins, use get_protein_interactions.
 
    Keep max_hops small (1-2) for densely-connected hubs to avoid slow queries.
 
    Arguments:
        entity: Name, label, symbol, accession, or nodeId of the start entity.
                Case-insensitive; the best-matched, most-connected node is used.
        max_hops: Traversal depth, integer 1-4 (default 1).
        max_nodes: Max neighbors returned, 1-200 (default 50), nearest first.
        node_type_filter: Optional list of neighbor labels to keep
                          (e.g. ["Protein", "Gene"]). Case-insensitive. Filters the
                          END node only, not intermediates. Empty = all.
        relationship_type_filter: Optional list of relationship types to traverse
                          (e.g. ["CATALYZES", "INTERACTS_WITH"]). Case-insensitive.
                          Call get_graph_schema() for valid types. Empty = all.
 
    Returns:
        A JSON string describing the subgraph: {start, node_count,
        relationship_count, nodes:[{id, labels, name, properties}],
        relationships:[{type, start, end, properties}]}. Returns a plain
        guidance message if the entity isn't found or has no neighbors.
    """
    entity = (entity or "").strip()
    if not entity:
        return "Error: 'entity' is required (name, symbol, accession, or nodeId)."
    if not isinstance(max_hops, int) or not (1 <= max_hops <= 4):
        return "Error: max_hops must be an integer between 1 and 4."
    try:
        max_nodes = max(1, min(int(max_nodes), 200))
    except (TypeError, ValueError):
        max_nodes = 50
 
    rel_list = [s.strip() for s in (relationship_type_filter or []) if s and s.strip()]
    node_list = [s.strip() for s in (node_type_filter or []) if s and s.strip()]

    rel_filter = "|".join(sorted({r.upper() for r in rel_list})) or None
    label_filter = "|".join(sorted({">" + n for n in node_list})) or None

    rows = _run(QUERY_GET_SUBGRAPH_TEMPLATE, params={
        "entity": entity,
        "max_hops": int(max_hops),
        "max_nodes": max_nodes,
        "rel_filter": rel_filter,
        "label_filter": label_filter,
    })
    subgraph = rows[0]["subgraph"] if rows else None
    if subgraph and subgraph.get("nodes"):
        return json.dumps(subgraph, indent=2, default=str)
 
    check = _run(QUERY_RESOLVE_ENTITY_COUNT, params={"entity": entity})
    total = check[0]["total"] if check else 0
    if total == 0:
        return (f"No entity found matching '{entity}'. Resolve the exact name with "
                f"search_entities('{entity}') first.")
    msg = f"Entity '{entity}' found, but no neighbors within {max_hops} hop(s)"
    flt = []
    if node_type_filter:
        flt.append(f"node_type_filter={node_type_filter}")
    if relationship_type_filter:
        flt.append(f"relationship_type_filter={relationship_type_filter}")
    msg += (f" matching {', '.join(flt)}. Remove the filter(s), raise max_hops, or "
            f"call get_graph_schema() for valid types." if flt else ".")
    return msg

# ---------------------------------------------------------------------------
# ProKN Explorer Skill functionality
# ---------------------------------------------------------------------------

_GENE_TOKEN_RE = re.compile(r"[;,\s]+")

def _map_ids_via_pir(ids, from_type, timeout=60):
    """Map IDs to gene symbols with PIR's UniProt ID mapping service 

    Synchronous mode (async=NO, to=GENENAME); the response is tab-delimited
    "sourceID<TAB>gene" lines. Returns (genes, unmapped).
    """
    query = urllib.parse.urlencode({
        "from": from_type, "to": "GENENAME", "ids": ",".join(ids), "async": "NO"})
    url = f"{PROKN_IDMAPPING_URL}?{query}"
    with urllib.request.urlopen(urllib.request.Request(url), timeout=timeout) as resp:
        text = resp.read().decode("utf-8", "replace")
    genes, matched = [], set()
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        parts = line.split("\t") if "\t" in line else line.split(None, 1)
        if len(parts) < 2:
            continue
        src, gene = parts[0].strip(), parts[1].strip()
        if src.lower() == "from" or gene.lower() in ("to", "genename"):
            continue  # skip header row if applicable
        matched.add(src.lower())
        if gene and gene not in genes:
            genes.append(gene)
    unmapped = [i for i in ids if i.lower() not in matched]
    return genes, unmapped


def _symbol_from_search_row(row):
    """Pull a gene symbol out of a search_entities row: a Protein keeps it in geneNames,
    and a Gene's own name is the symbol."""
    idmap = row.get("identifiers") or {}
    gn = idmap.get("geneNames")
    if gn:
        toks = [t for t in _GENE_TOKEN_RE.split(str(gn)) if t]
        if toks:
            return toks[0]
    if (row.get("node_type") or "").lower() == "gene":
        return idmap.get("symbol") or idmap.get("label") or row.get("name")
    return idmap.get("symbol")


def _map_ids_via_graph(ids):
    """Fallback used when PIR is unreachable: turn each ID into a gene symbol with the graph's
    own search (QUERY_SEARCH_ENTITIES). Returns (genes, unmapped)."""
    genes, unmapped = [], []
    for raw in ids:
        term = str(raw).strip().lower()
        rows = _run(QUERY_SEARCH_ENTITIES, params={
            "t": term, "entity_types": ["protein", "gene"], "limit": 5}) if term else []
        sym = None
        for r in (rows or []):
            sym = _symbol_from_search_row(r)
            if sym:
                break
        if sym:
            if sym not in genes:
                genes.append(sym)
        else:
            unmapped.append(raw)
    return genes, unmapped


@mcp.tool()
def get_explorer_network(
    gene_names: Annotated[list[str], Field(description="Two or more gene symbols, e.g. ['PLK3','HIPK3','CDK1'], OR IDs of the type named by from_type; those get mapped to symbols first.")],
    from_type: Annotated[str, Field(description="UniProt ID-type code of the inputs, e.g. 'ACC', 'P_REFSEQ_AC', 'ENSEMBL_ID'. Default 'GENENAME' means the inputs are already gene symbols and no mapping happens.")] = "GENENAME",
) -> dict | str:
    """Build a ProKN network from gene symbols (or other IDs) and return a shareable Explorer link.

    Pass gene symbols directly, or IDs of another type with from_type; the server maps those to
    gene symbols with PIR's UniProt ID mapping, and falls back to the graph's own search
    (search_entities) if PIR is unreachable. Needs two or more symbols after mapping. Returns
    {network_id, explorer_url, gene_names} (plus mapping/unmapped when from_type is used), or a
    guidance message on failure. Read-only; calls the ProKN web app (see PROKN_WEB_BASE_URL).
    """
    inputs = []
    for g in (gene_names or []):
        g = str(g).strip()
        if g and g not in inputs:
            inputs.append(g)
    if not inputs:
        return "Error: provide at least two entities to visualize the network."

    from_type = (from_type or "GENENAME").strip().upper()
    mapping = None
    unmapped = []
    if from_type == "GENENAME":
        genes = inputs
    else:
        try:
            genes, unmapped = _map_ids_via_pir(inputs, from_type)
            mapping = f"{len(inputs)} {from_type} id(s) mapped to gene symbols via PIR ID mapping"
        except Exception:
            genes, unmapped = _map_ids_via_graph(inputs)
            mapping = f"PIR ID mapping unavailable; {from_type} id(s) resolved to gene symbols via graph search"
        deduped = []
        for g in genes:
            if g not in deduped:
                deduped.append(g)
        genes = deduped

    if len(genes) < 2:
        msg = "Error: provide at least two entities to visualize the network."
        if from_type != "GENENAME":
            msg += f" (got {genes or 'none'} after mapping; unmapped {unmapped or 'none'})"
        return msg + "."

    base = PROKN_WEB_BASE_URL.rstrip("/")
    api_url = f"{base}/api/knowledge_graph"
    body = json.dumps({"gene_names": genes}).encode("utf-8")
    req = urllib.request.Request(
        api_url, data=body, headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        return f"Error: the ProKN web API returned HTTP {e.code} at {api_url}."
    except TimeoutError:
        return (f"Error: the ProKN web API at {api_url} did not respond in time. "
                f"Building the network can be slow for large or hub gene sets; try fewer genes, "
                f"or confirm the endpoint is up and PROKN_WEB_BASE_URL points at the right instance.")
    except OSError as e:
        # URLError and other socket errors (connection refused, DNS, TLS) land here
        reason = getattr(e, "reason", e)
        return (f"Error: could not reach the ProKN web API at {api_url} ({reason}). "
                f"Set PROKN_WEB_BASE_URL if the web app is hosted elsewhere.")

    network_id = payload.get("network_id") if isinstance(payload, dict) else None
    if not network_id:
        return f"Error: the ProKN web API did not return a network_id (got: {str(payload)[:200]})."

    filt = urllib.parse.quote(json.dumps({"network_id": network_id}))
    result = {
        "network_id": network_id,
        "explorer_url": f"{base}/explorer?filter={filt}",
        "gene_names": genes,
    }
    if from_type != "GENENAME":
        result["mapping"] = mapping
        result["unmapped"] = unmapped
    return result

if __name__ == "__main__":
    import sys
    # Default to stdio mode, but allow streamable-http, sse, or http to trigger network mode
    transport_arg = sys.argv[1] if len(sys.argv) > 1 else "stdio"

    if not verify_neo4j_connection():
        sys.exit(1)

    if transport_arg in ["http", "sse", "streamable-http"]:
        print(f"Starting ProKN MCP Server on Streamable HTTP (port 8000, path /mcp)")
        
        mcp.run(
            transport="streamable-http", 
            host="0.0.0.0", 
            port=8000, 
            path="/mcp"
        )
    else:
        # Standard stdio mode
        mcp.run(transport='stdio', show_banner=False)