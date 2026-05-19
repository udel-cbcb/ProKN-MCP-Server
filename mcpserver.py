import os
from fastmcp import FastMCP
import neo4j
from queries import (
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
    QUERY_GET_PATHWAYS_BETWEEN_PROTEIN_SETS
)
import sys
import time

mcp = FastMCP(
    "ProKN-MCP-Server",
    instructions="""
    Protein Knowledge Network (ProKN). MCP Server is connected to the ProKN Knowledge Graph which can be found at: https://research.bioinformatics.udel.edu/ProKN. Point the user to this for more details if needed.

    CRITICAL INSTRUCTIONS:
    1. ENTITY RESOLUTION: Always use 'search_entities' first to find the exact database labels for entities (drugs, proteins, etc.) that a user is referring to. This is because sometimes we might not have an exact node that a user might be spelling out.
    2. EXPLANATION: Before making any tool calls, always provide an explanation of which tool is going to be called and why. 
    3. HOLISTIC APPROACH: When using this MCP server, do not skip any results given by the tools when displaying the data to the user. It is important to show the complete picture.
    4. If there are abbreviations, do not expand them unless metnioned in the response. 

    COMMON USECASES:
    1. To get the Phosphorylation sites that are downregulated by a Drug/Perturbagen, you can make a call to 'get_phosphosites_regulated_by_pertubagen' with the drug name, threshold=1.0, and direction="down" (check with user if they want a different threshold).
    You could also make a call to 'get_proteins_catalyzing_sites' to get the kinases that catalyze these phosphosites. This might help understand how a perturbagen indirectly is linked with a kinase. Direct linkage can also be found via get_drug_mechanisms.

    """
)

NEO4J_URI = os.environ.get("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USERNAME = os.environ.get("NEO4J_USERNAME", "neo4j")
NEO4J_PASSWORD = os.environ.get("NEO4J_PASSWORD", "password")

driver = neo4j.GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USERNAME, NEO4J_PASSWORD))

print(f"Testing connection to Neo4j at {NEO4J_URI}...", file=sys.stderr)
connected = False
for i in range(5):
    try:
        driver.verify_connectivity()
        print("Neo4j connection successful!", file=sys.stderr)
        connected = True
        break
    except Exception as e:
        print(f"Waiting for Neo4j... ({i+1}/5)", file=sys.stderr)
        time.sleep(2)

if not connected:
    print("Failed to connect to Neo4j after 10 seconds. Check NEO4J_URI.", file=sys.stderr)
    sys.exit(1)

# Main helper function to run Cypher queries
def _run(cypher: str, params: dict = {}, limit: int = 500):
    """Execute a read-only Cypher query and return rows as plain dicts."""
    # Ensure there's a LIMIT in the query or use the parameter
    if "LIMIT" not in cypher.upper():
        cypher = f"{cypher} LIMIT {limit}"
    
    with driver.session(default_access_mode=neo4j.READ_ACCESS) as session:
        with session.begin_transaction(timeout=30.0) as tx:
            result = tx.run(cypher, **params)
            return [record.data() for record in result]

# ---------------------------------------------------------------------------
# UTILITIES
# ---------------------------------------------------------------------------

@mcp.tool()
def search_entities(term: str, entity_types: list[str] = [], limit: int = 20):
    """
    Search for nodes in the knowledge graph by name across all major entity
    types. This should be the first tool called for any question involving
    a specific gene, protein, drug, disease, pathway, or perturbagen.
    """
    t = term.lower()
    type_filter = f"AND labels(n)[0] IN {entity_types}" if entity_types else ""

    return _run(f"""
        MATCH (n)
        WHERE labels(n)[0] IN [
            'Protein', 'Gene', 'Drug', 'Compound', 'Disease', 
            'DiseaseOrPhenotype', 'Pathway', 'Perturbagen', 'GOTerm', 'MSigDB'
        ]
        {type_filter}
        AND (
            toLower(n.label) CONTAINS $t OR
            toLower(n.name) CONTAINS $t OR
            toLower(n.id) CONTAINS $t OR
            toLower(n.geneNames) CONTAINS $t OR
            toLower(n.entryName) CONTAINS $t OR
            toLower(n.hgnc) CONTAINS $t OR
            toLower(n.drugName) CONTAINS $t OR
            toLower(n.chemblId) CONTAINS $t OR
            toLower(n.diseaseName) CONTAINS $t OR
            toLower(n.pathwayName) CONTAINS $t OR
            toLower(n.pertIname) CONTAINS $t OR
            toLower(n.msigdb) CONTAINS $t OR
            toString(n.pubchemCId) = $t OR
            toString(n.pubchemCids) = $t OR
            toString(n.pubchem) = $t
        )
        RETURN labels(n)[0] AS node_type, properties(n) AS properties
        LIMIT $limit
    """, {"t": t, "limit": limit}, limit=limit)

# ---------------------------------------------------------------------------
# GRANULAR TOOLS (Individual Queries)
# ---------------------------------------------------------------------------
# ---------------------------------------------------------------------------
@mcp.tool()
def get_phosphosites_regulated_by_pertubagen(term: str, threshold: float = 1.0, direction: str = "both"):
    """
    Retrieve phosphorylation sites that are regulated (up/down) by the input perturbagen based on LINCS P100 phosphoproteomics data.
    
    Args:
        term: The name, label, LINCS pertIname (standardized LINCS name), or PubChem CID of the perturbagen.
        threshold: The magnitude of the minimum log2Ratio change required. Defaults to 1.0. 
        direction: The type of regulation to filter by. Options: "up" (increased phosphorylation), "down" (decreased phosphorylation), "both" (any significant change).
    """
    abs_threshold = abs(threshold)
    if direction not in ["up", "down", "both"]:
        return "Error: direction must be exactly 'up', 'down', or 'both'."
        
    return _run(QUERY_PHOSPHOSITES_REGULATED_BY_PERTURBAGEN_TEMPLATE, params={
        "term": term,
        "threshold": abs_threshold,
        "direction": direction
    })

@mcp.tool()
def get_proteins_catalyzing_sites(phosphosites: list[str], ecNumber="2.7.*"):
    """
    Retrieve proteins that catalyze the phosphorylation of the input phosphosites.
    To get kinases, use ecNumber="2.7.*"
    """
    return _run(QUERY_GET_PROTEINS_CATALYZING_SITES, params={"site_labels": phosphosites, "ec_filter": ecNumber})

@mcp.tool()
def get_phosphosites_catalyzed_by_proteins(proteins: list[str]):  
    """
    Retrieve phosphorylation sites that are catalyzed by the input proteins or kinases.
    """
    return _run(QUERY_GET_PHOSPHOSITES_CATALYZED_BY_PROTEINS, params={"protein_list": proteins})

@mcp.tool()
def get_drugs_mechanisms(drug_identifiers: list[str], actionType:str = ""):
    """
    Retrieves pharmacological mechanisms for a list of drugs. Accepts drug names / identifiers (e.g., 'Lapatinib') or PubChem CIDs (e.g., '208908'). If the drug is known by a code name, trade name, or alias (e.g., a clinical trial code like 'BYL719'), call search_entities first to resolve the correct identifier before calling this tool.
    Use this to get the kinases inhibited by the drug - by using the actionType "INHIBITOR". Use an empty actionType (default) to get all mechanisms.
    """
    return _run(QUERY_GET_DRUGS_MECHANISMS, params={"identifiers": drug_identifiers, "action_type": actionType})

@mcp.tool()
def get_genes_regulated_by_drugs(drug_identifiers: list[str]):
    """
    Retrieve genes that are regulated positively or negatively by the input drugs.
    Accepts drug names / identifiers (e.g., 'Lapatinib') or PubChem CIDs (e.g., '208908').
    """
    return _run(QUERY_GET_GENES_REGULATED_BY_DRUGS, params={"identifiers": drug_identifiers})

@mcp.tool()
def get_proteins_encoded_by_genes(gene_symbols: list[str]):
    """
    Retrieve proteins encoded by the input genes through the IS_PROTEIN or ENCODES relationships.
    """
    return _run(QUERY_GET_PROTEINS_ENCODED_BY_GENES, params={"gene_symbols": gene_symbols})

@mcp.tool()
def filter_proteins_by_ec_number(proteins: list[str], ec_filter: str = "2.7.*"):
    """
    Filter a list of proteins to identify which ones belong to a specific enzyme class based on their EC Number.
    To identify kinases from a list of proteins, use ec_filter="2.7.*".
    """
    return _run(QUERY_FILTER_PROTEINS_BY_EC, params={"proteins": proteins, "ec_filter": ec_filter})

@mcp.tool()
def get_protein_interactions(protein1: str, protein2: str):
    """
    Find how two proteins (or kinases) interact with each other.
    This finds the shortest path between them, traversing through intermediate Proteins, Pathways, Complexes, or GoTerms.
    """
    return _run(QUERY_GET_PROTEIN_INTERACTIONS, params={"protein1": protein1, "protein2": protein2})

@mcp.tool()
def get_pathways_between_protein_sets(proteins1: list[str], proteins2: list[str]):
    """
    Find pathways that act as a bridge between two sets of proteins.
    Returns the pathways that have direct connections to at least one protein in both sets.
    """
    all_results = []
    
    # Programmatically iterate and permute combinations in Python
    for s_node in proteins1:
        for t_node in proteins2:
            if s_node == t_node:
                continue
                
            res = _run(QUERY_GET_PATHWAYS_BETWEEN_PROTEIN_SETS, params={
                "source_node": s_node, 
                "target_node": t_node
            })
            
            if res:
                all_results.extend(res)
                
    return all_results

# ---------------------------------------------------------------------------
@mcp.tool()
def execute_read_only_cypher(query: str, defer_loading=False):
    """
    Execute a custom Cypher query for advanced exploration.

    Use this ONLY WHEN the other tools do not cover your specific query — for example,
    multi-hop traversals, custom aggregations, subgraph extraction, or joining
    data across datasets in a way not provided by the structured tools.

    ONLY MATCH/RETURN statements are permitted. Any query containing CREATE,
    MERGE, SET, DELETE, REMOVE, or DROP will be rejected.

    Results are capped at 200 rows. For very large result sets, add LIMIT to
    your query.

    CRITICAL INSTRUCTIONS FOR SUMMARIZING RESULTS:
    When you return information about relationships (edges) to the user, you MUST look at the edge properties to explain the evidence for that connection. 
    Always look for evidence on the relationship (edge) itself, not the nodes. Also return the query you used to the user using Reproducibilitiy: "<query>".
    
    1. LITERATURE EVIDENCE: Check if the relationship contains `pmid`, `pmids`, or a `dbReference` key containing "PMID:". If any of these exist, you must explicitly tell the user: "Evidence for this connection can be found in these PMIDs: [list the PMIDs]".
    2. DATABASE SOURCE: If no PMID information is present on the edge, check for database provenance keys such as `SAB` (Source Abbreviation) or `dcc` (Data Coordinating Center). If present, you must tell the user: "The source for this information is the [SAB/dcc value] database."
    3. MISSING EVIDENCE: If neither PMIDs nor source keys are on the edge, state that no source evidence was provided in the graph for the connection.

    Parameters
    ----------
    query : a valid read-only Cypher MATCH/RETURN query

    Returns a list of result records as dicts.
    """
    forbidden = ["CREATE", "MERGE", "SET", "DELETE", "REMOVE", "DROP"]
    if any(kw in query.upper() for kw in forbidden):
        return "Error: This tool only supports read-only operations (MATCH/RETURN)."
    try:
        with driver.session(default_access_mode=neo4j.READ_ACCESS) as session:
            with session.begin_transaction(timeout=30.0) as tx:
                result = tx.run(query)
                return [record.data() for record in result][:200]
    except Exception as e:
        return f"Cypher Execution Error: {str(e)}"

@mcp.tool()
def get_graph_schema():
    """
    Return the schema of the Neo4j database. This can be used to understand the structure of the graph and the relationships between nodes.
    """
    return _run(QUERY_GET_GRAPH_ONTOLOGY)

@mcp.tool()
def get_relationship_properties():
    """
    Returns the properties of the relationships in the Neo4j database. 
    This can be used to understand the data stored in the relationships.
    """
    return _run(QUERY_GET_RELATIONSHIP_PROPERTIES)

@mcp.tool()
def get_node_properties():
    """
    Returns the properties of the nodes in the Neo4j database. 
    This can be used to understand the data stored in the nodes.
    """
    return _run(QUERY_GET_NODE_PROPERTIES)

@mcp.tool()
def get_queries(name_of_tool: str):
    """
    Returns the underlying queries that are run when a tool is called. 
    Use this if a user wants to know whats happening under the hood.
    """
    
    # dict: tool_name -> query_template
    tool_queries = {
        "get_phosphosites_regulated_by_pertubagen": QUERY_PHOSPHOSITES_REGULATED_BY_PERTURBAGEN_TEMPLATE,
        "get_proteins_catalyzing_sites": QUERY_GET_PROTEINS_CATALYZING_SITES,
        "get_phosphosites_catalyzed_by_proteins": QUERY_GET_PHOSPHOSITES_CATALYZED_BY_PROTEINS,
        "get_relationship_properties": QUERY_GET_RELATIONSHIP_PROPERTIES,
        "get_node_properties": QUERY_GET_NODE_PROPERTIES,
        "get_graph_ontology": QUERY_GET_GRAPH_ONTOLOGY,
        "get_drug_mechanisms": QUERY_GET_DRUGS_MECHANISMS,
        "get_genes_regulated_by_drugs": QUERY_GET_GENES_REGULATED_BY_DRUGS,
        "get_proteins_encoded_by_genes": QUERY_GET_PROTEINS_ENCODED_BY_GENES,
        "filter_proteins_by_ec_number": QUERY_FILTER_PROTEINS_BY_EC,
        "get_protein_interactions": QUERY_GET_PROTEIN_INTERACTIONS,
        "get_pathways_between_protein_sets": QUERY_GET_PATHWAYS_BETWEEN_PROTEIN_SETS
    }
    if name_of_tool in tool_queries:
        return tool_queries[name_of_tool]
    return f"Tool '{name_of_tool}' not found. Available tools: {', '.join(tool_queries.keys())}"


if __name__ == "__main__":
    import sys
    # Default to stdio mode, but allow streamable-http, sse, or http to trigger network mode
    transport_arg = sys.argv[1] if len(sys.argv) > 1 else "stdio"
    
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