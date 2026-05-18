# Contains all Cypher Queries used for MCP server logic, and for LLM to know about
# The LLM needs to know about the queries in case a user wants to know whats happening underneath
# We pass the queries as description to the MCP server (through function docstrings)
# We use doubled braces {{ }} for Cypher property matches so they work with .format()


# Currently used: 
QUERY_PHOSPHOSITES_REGULATED_BY_PERTURBAGEN_TEMPLATE = """
    MATCH (pert:Perturbagen)-[r_usedIn:IS_USED_IN]->(exp:Experiment)
    WHERE toLower(pert.label) = toLower($term) 
       OR toLower(pert.pertIname) = toLower($term)
       OR toString(pert.pubchemCId) = $term
       
    MATCH (exp)-[r_pertEff:PERTURBATION_EFFECT]->(pSite:PTMSite)
    WITH pert, exp, r_pertEff, pSite, toFloat(r_pertEff.log2Ratio) AS pDiff
    WHERE 
        ($direction = 'up' AND pDiff >= $threshold) OR
        ($direction = 'down' AND pDiff <= -$threshold) OR
        ($direction = 'both' AND abs(pDiff) >= $threshold)
        
    RETURN DISTINCT 
        pSite.label AS measured_site_name, 
        pSite.id AS measured_site_id, 
        pDiff AS log2_ratio,
        pert.label AS perturbagen_label,
        pert.pubchemCId AS pubchemCId
    ORDER BY abs(pDiff) DESC
"""

QUERY_GET_PROTEINS_CATALYZING_SITES = """
    MATCH (k:Protein)-[:CATALYZES]->(pSite:PTMSite)
    WHERE pSite.label IN $site_labels
      AND k.ecNumber =~ $ec_filter
    RETURN 
        pSite.label AS site_label,
        k.symbol AS protein_symbol,
        k.geneNames AS protein_name,
        k.ecNumber AS ec_number
"""

# TODO: check if it should be p.label or p.geneNames
QUERY_GET_PHOSPHOSITES_CATALYZED_BY_PROTEINS = """
    MATCH (p:Protein)-[:CATALYZES]->(targetSite:PTMSite)
    WHERE p.label IN $protein_list OR p.geneNames IN $protein_list
    WITH p, collect(DISTINCT targetSite.label) AS all_catalyzed_sites
    RETURN 
        COALESCE(p.label, p.geneNames) AS protein,
        p.ecNumber AS ec_number,
    all_catalyzed_sites
"""

QUERY_GET_CHEMBL_DRUGS_TEMPLATE = """
    MATCH (pert:Perturbagen {{SAB:'LINCS_P100'}})
    WHERE toLower(pert.label) = toLower('{term}')
    MATCH (chembl:Compound {{SAB: 'ChEMBL'}})
    WHERE pert.pubchemCId = chembl.pubchemCids
    RETURN id(chembl) as chemblId, chembl.chemblId as chembl_str_id
"""

QUERY_GET_DRUGS_MECHANISMS = """
    MATCH (d:Drug)
    WHERE toLower(d.label) IN $identifiers 
    OR toLower(d.name) IN $identifiers
    OR toString(d.pubchemCId) IN $identifiers

    MATCH (d)-[r:HAS_MECHANISM|INTERACTS_WITH]->(p:Protein)
    WHERE p.ecNumber =~ '2.7.*' 
    AND (
        ($action_type IS NULL OR $action_type = "") 
        OR 
        (r.actionType = $action_type)
    )

    RETURN DISTINCT
        d.label AS drug_name,
        p.label AS protein_label,
        p.proteinName AS protein_name,
        p.ecNumber AS ec_number,
        type(r) AS relation_type,
        COALESCE(r.actionType, 'N/A') AS action
"""

QUERY_GET_GRAPH_ONTOLOGY = """
    MATCH (n)-[r]->(m)
    WITH DISTINCT labels(n)[0] AS Source, type(r) AS Edge, labels(m)[0] AS Target
    RETURN Source + " --" + Edge + "--> " + Target AS Schema
"""

QUERY_GET_RELATIONSHIP_PROPERTIES = """
    CALL db.schema.relTypeProperties() 
    YIELD relType, propertyName, propertyTypes
    WITH relType, collect(propertyName) AS props
    RETURN relType, props
"""

QUERY_GET_NODE_PROPERTIES = """
    CALL db.schema.nodeTypeProperties() 
    YIELD nodeLabels, propertyName
    WITH nodeLabels[0] AS nodeName, collect(propertyName) AS properties
    RETURN nodeName, properties
"""

QUERY_GET_GENES_REGULATED_BY_DRUGS = """
MATCH (compound)
WHERE (compound:Compound OR compound:Drug)
  AND (
      toLower(compound.label) IN $identifiers OR 
      toLower(compound.name) IN $identifiers OR
      toLower(compound.chemblId) IN $identifiers OR
      toString(compound.pubchem) IN $identifiers OR 
      toString(compound.pubchemCId) IN $identifiers OR
      toString(compound.pubchemCids) IN $identifiers
  )

MATCH (compound)-[reg:POSITIVELY_REGULATES|NEGATIVELY_REGULATES]->(g:Gene)

RETURN DISTINCT
    compound.label AS input_drug,
    g.label AS gene_symbol,             
    type(reg) AS regulation_type,
    COALESCE(reg.log2Ratio, "N/A") AS strength
"""

QUERY_GET_PROTEINS_ENCODED_BY_GENES = """
    MATCH (g:Gene)
    WHERE g.symbol IN $gene_symbols OR g.label IN $gene_symbols

    MATCH (g)-[:IS_PROTEIN|ENCODES]->(p:Protein)

    RETURN DISTINCT
        g.symbol AS gene_symbol,
        p.label AS protein_name,
        p.proteinName AS full_name,
        p.ecNumber AS ec_number
"""

QUERY_FILTER_PROTEINS_BY_EC = """
    MATCH (p:Protein)
    WHERE (p.label IN $proteins OR p.geneNames IN $proteins)
      AND p.ecNumber =~ ($ec_filter + ".*")
    RETURN DISTINCT
        p.label AS protein_name,
        p.proteinName AS full_name,
        p.ecNumber AS ec_number
"""

QUERY_GET_PROTEIN_INTERACTIONS = """
    MATCH (p1:Protein), (p2:Protein)
    WHERE (toLower(p1.label) = toLower($protein1) OR toLower(p1.geneNames) = toLower($protein1) OR toLower(p1.entryName) = toLower($protein1))
      AND (toLower(p2.label) = toLower($protein2) OR toLower(p2.geneNames) = toLower($protein2) OR toLower(p2.entryName) = toLower($protein2))
      AND p1 <> p2
      
    MATCH path = allShortestPaths((p1)-[*1..3]-(p2))
    WHERE all(n IN nodes(path) WHERE n:Protein OR n:Pathway OR n:Complex OR n:GOTerm)
    
    RETURN [n IN nodes(path) | 
        {
            name: COALESCE(n.label, n.geneNames, n.pathwayName, "Unknown"),
            type: labels(n)[0]
        }
    ] AS interaction_path,
    length(path) AS path_length
"""

QUERY_GET_PATHWAYS_BETWEEN_PROTEIN_SETS = """
    MATCH path = (p1:Protein)-[:PARTICIPATES_IN|PATHWAY_EVENT_OF*1..3]-(p2:Protein)
    WHERE (toLower(p1.geneNames) = toLower($source_node) OR toLower(p1.label) = toLower($source_node))
      AND (toLower(p2.geneNames) = toLower($target_node) OR toLower(p2.label) = toLower($target_node))
      AND p1 <> p2
    RETURN DISTINCT 
        COALESCE(p1.geneNames, p1.label) AS protein1, 
        [n IN nodes(path)[1..-1] | COALESCE(n.pathwayName, n.name)] AS connecting_pathways, 
        COALESCE(p2.geneNames, p2.label) AS protein2
"""
