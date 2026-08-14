# Contains all Cypher Queries used for MCP server logic, and for LLM to know about
# The LLM needs to know about the queries in case a user wants to know whats happening underneath
# We pass the queries as description to the MCP server (through function docstrings)
# We use doubled braces {{ }} for Cypher property matches so they work with .format()

QUERY_SEARCH_ENTITIES = """
    MATCH (n)
    WHERE ($entity_types = [] OR any(l IN labels(n) WHERE toLower(l) IN $entity_types))
      AND (
          // name + id fields: case-insensitive substring (type-safe via toString)
          any(v IN [n.label, n.name, n.symbol, n.geneNames, n.entryName, n.hgnc,
                    n.proteinName, n.drugName, n.chemblId, n.diseaseName,
                    n.pathwayName, n.pertIname, n.msigdb, n.id, n.nodeId]
              WHERE toLower(toString(coalesce(v, ''))) CONTAINS $t)
          // pubchem ids: exact match
          OR any(v IN [n.pubchemCId, n.pubchemCids, n.pubchem]
                 WHERE toString(coalesce(v, '')) = $t)
      )
    WITH n, toLower(coalesce(n.label, n.name, n.symbol, '')) AS primary
    WITH n, primary,
         CASE
             WHEN primary = $t           THEN 0   // exact name match
             WHEN primary STARTS WITH $t THEN 1   // prefix match
             ELSE 2                                // substring match somewhere
         END AS match_rank
    RETURN
        labels(n)[0] AS node_type,
        coalesce(n.label, n.name, n.symbol, n.drugName, n.diseaseName,
                 n.pathwayName, toString(n.nodeId)) AS name,
        // native map projection (no apoc) -> compact identifier map for the next
        // tool. Missing keys come back as null; that's fine.
        n {.label, .nodeId, .name, .symbol, .geneNames, .entryName, .hgnc,
           .drugName, .chemblId, .pubchemCId, .pubchemCids, .pertIname, .id}
            AS identifiers,
        match_rank
    ORDER BY match_rank, name
    LIMIT toInteger($limit)
"""

QUERY_PHOSPHOSITES_REGULATED_BY_PERTURBAGEN_TEMPLATE = """
    MATCH (pert:Perturbagen)-[r_usedIn:IS_USED_IN]->(exp:Experiment)
    WHERE toLower(pert.label) = toLower($perturbagen)
       OR toLower(coalesce(pert.pertIname,'')) = toLower($perturbagen)
       OR toString(coalesce(pert.pubchemCId,'')) = $perturbagen
 
    MATCH (exp)-[r_pertEff:PERTURBATION_EFFECT]->(pSite:PTMSite)
    WITH pert, pSite, toFloat(r_pertEff.log2Ratio) AS pDiff
    WHERE ($direction = 'up'   AND pDiff >=  $threshold)
       OR ($direction = 'down' AND pDiff <= -$threshold)
       OR ($direction = 'both' AND abs(pDiff) >= $threshold)
 
    RETURN DISTINCT
        pSite.label AS measured_site_name,
        pSite.id    AS measured_site_id,
        pDiff       AS log2_ratio,
        pert.label  AS perturbagen_label,
        pert.pubchemCId AS pubchemCId
    ORDER BY abs(pDiff) DESC
"""

QUERY_GET_PROTEINS_CATALYZING_SITES = """
    MATCH (k:Protein)-[cat:CATALYZES]->(pSite:PTMSite)
    WHERE any(s IN $site_labels WHERE toLower(pSite.label) = toLower(s))
      AND any(ec IN split(coalesce(k.ecNumber, ''), ';') WHERE trim(ec) =~ $ec_filter)
    RETURN
        pSite.label AS site_label,
        coalesce(k.label, k.geneNames) AS protein_symbol,
        k.proteinName AS protein_name,
        k.ecNumber AS ec_number,
        properties(cat) AS evidence
"""

# TODO: double check whether this should be p.label or p.geneNames
QUERY_GET_PHOSPHOSITES_CATALYZED_BY_PROTEINS = """
    MATCH (p:Protein)-[:CATALYZES]->(targetSite:PTMSite)
    WHERE any(x IN $protein_list
              WHERE toLower(p.label) = toLower(x)
                 OR toLower(coalesce(p.geneNames, '')) = toLower(x))
    WITH p, collect(DISTINCT targetSite.label) AS all_catalyzed_sites
    RETURN
        coalesce(p.label, p.geneNames) AS protein,
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
    WHERE toLower(d.label) IN $drug_identifiers
       OR toLower(coalesce(d.name, '')) IN $drug_identifiers
       OR toString(coalesce(d.pubchemCId, '')) IN $drug_identifiers

    MATCH (d)-[r:HAS_MECHANISM|INTERACTS_WITH]->(p:Protein)
    WHERE ($ec_filter = "" OR any(ec IN split(coalesce(p.ecNumber, ''), ';') WHERE trim(ec) =~ $ec_filter))
      AND ($action_type = "" OR r.actionType = $action_type)

    RETURN DISTINCT
        d.label        AS drug_name,
        p.label        AS protein_label,
        p.proteinName  AS protein_name,
        p.ecNumber     AS ec_number,
        type(r)        AS relation_type,
        coalesce(r.actionType, 'N/A') AS action,
        properties(r)  AS evidence
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
          toLower(coalesce(compound.label, ''))    IN $drug_identifiers OR
          toLower(coalesce(compound.name, ''))     IN $drug_identifiers OR
          toLower(coalesce(compound.chemblId, '')) IN $drug_identifiers OR
          toString(coalesce(compound.pubchem, ''))     IN $drug_identifiers OR
          toString(coalesce(compound.pubchemCId, ''))  IN $drug_identifiers OR
          toString(coalesce(compound.pubchemCids, '')) IN $drug_identifiers
      )

    MATCH (compound)-[reg:POSITIVELY_REGULATES|NEGATIVELY_REGULATES]->(g:Gene)

    RETURN DISTINCT
        compound.label AS input_drug,
        g.label        AS gene_symbol,
        type(reg)      AS regulation_type,
        coalesce(reg.log2Ratio, "N/A") AS strength,
        properties(reg) AS evidence
"""

QUERY_GET_PROTEINS_ENCODED_BY_GENES = """
    MATCH (g:Gene)
    WHERE any(x IN $gene_symbols
              WHERE toLower(g.label) = toLower(x)
                 OR toLower(coalesce(g.geneNames, '')) = toLower(x))
    MATCH (g)-[:IS_PROTEIN|ENCODES]->(p:Protein)
    RETURN DISTINCT
        coalesce(g.label, g.geneNames) AS gene_symbol,
        p.label       AS protein_name,
        p.proteinName AS full_name,
        p.ecNumber    AS ec_number
"""

QUERY_FILTER_PROTEINS_BY_EC = """
    MATCH (p:Protein)
    WHERE any(x IN $proteins
              WHERE toLower(p.label) = toLower(x)
                 OR toLower(coalesce(p.geneNames, '')) = toLower(x))
      AND any(ec IN split(coalesce(p.ecNumber, ''), ';') WHERE trim(ec) =~ $ec_filter)
    RETURN DISTINCT
        p.label       AS protein_name,
        p.proteinName AS full_name,
        p.ecNumber    AS ec_number
"""

QUERY_GET_PROTEIN_INTERACTIONS = """
    MATCH (p1:Protein), (p2:Protein)
    WHERE (toLower(p1.label) = toLower($protein1) OR toLower(coalesce(p1.geneNames,'')) = toLower($protein1) OR toLower(coalesce(p1.entryName,'')) = toLower($protein1))
      AND (toLower(p2.label) = toLower($protein2) OR toLower(coalesce(p2.geneNames,'')) = toLower($protein2) OR toLower(coalesce(p2.entryName,'')) = toLower($protein2))
      AND p1 <> p2
    MATCH path = allShortestPaths((p1)-[*1..3]-(p2))
    WHERE all(n IN nodes(path) WHERE n:Protein OR n:Pathway OR n:Complex OR n:GOTerm)
    RETURN [n IN nodes(path) |
        {name: coalesce(n.label, n.geneNames, n.pathwayName, "Unknown"), type: labels(n)[0]}
    ] AS interaction_path,
    length(path) AS path_length
    ORDER BY path_length ASC
"""

QUERY_GET_PATHWAYS_BETWEEN_PROTEIN_SETS = """
    MATCH path = (p1:Protein)-[:PARTICIPATES_IN|PATHWAY_EVENT_OF*1..3]-(p2:Protein)
    WHERE any(a IN $proteins1
              WHERE toLower(p1.label) = toLower(a)
                 OR toLower(coalesce(p1.geneNames, '')) = toLower(a))
      AND any(b IN $proteins2
              WHERE toLower(p2.label) = toLower(b)
                 OR toLower(coalesce(p2.geneNames, '')) = toLower(b))
      AND p1 <> p2
    RETURN DISTINCT
        coalesce(p1.geneNames, p1.label) AS protein1,
        [n IN nodes(path)[1..-1] | coalesce(n.pathwayName, n.name)] AS connecting_pathways,
        coalesce(p2.geneNames, p2.label) AS protein2
"""

QUERY_GET_RELATIONSHIP_GIVEN_ENTITY = """
    // find the entity by name (any of a few common fields), then pick one
    MATCH (n)
    WHERE toLower(coalesce(n.label, ''))     = toLower($entity)
       OR toLower(coalesce(n.name, ''))      = toLower($entity)
       OR toLower(toString(coalesce(n.nodeId, ''))) = toLower($entity)
       OR toLower(coalesce(n.symbol, ''))    = toLower($entity)
       OR toLower(coalesce(n.entryName, '')) = toLower($entity)
       OR toLower(coalesce(n.hgnc, ''))      = toLower($entity)
       OR toLower(coalesce(n.geneNames, '')) = toLower($entity)
    // if several nodes share the name, keep the most-connected one
    WITH n ORDER BY COUNT { (n)--() } DESC LIMIT 1

    // its neighbours (optional filters on neighbour label / relationship type)
    MATCH (n)-[r]-(neighbor)
    WHERE n <> neighbor
      AND ($neighbor_type = "" OR
           any(lbl IN labels(neighbor) WHERE toLower(lbl) = toLower($neighbor_type)))
      AND ($rel_type = "" OR toLower(type(r)) = toLower($rel_type))
 
    // keep the direction of each relationship
    WITH n, r, neighbor,
         CASE WHEN startNode(r) = n THEN 'outgoing' ELSE 'incoming' END AS direction
    RETURN
        labels(n)[0] AS source_type,
        coalesce(n.label, n.name, toString(n.nodeId)) AS source_name,
        direction,
        type(r) AS relationship_type,
        labels(neighbor)[0] AS neighbor_type,
        coalesce(neighbor.label, neighbor.name, toString(neighbor.nodeId)) AS neighbor_name,
        properties(r) AS evidence          // edge props: pmids, SAB, dcc, log2Ratio, ...
    ORDER BY relationship_type, neighbor_type, neighbor_name
    LIMIT toInteger($limit)
"""

QUERY_RESOLVE_ENTITY_COUNT = """
    MATCH (n)
    WHERE toLower(coalesce(n.label, ''))     = toLower($entity)
       OR toLower(coalesce(n.name, ''))      = toLower($entity)
       OR toLower(toString(coalesce(n.nodeId, ''))) = toLower($entity)
       OR toLower(coalesce(n.symbol, ''))    = toLower($entity)
       OR toLower(coalesce(n.entryName, '')) = toLower($entity)
       OR toLower(coalesce(n.hgnc, ''))      = toLower($entity)
       OR toLower(coalesce(n.geneNames, '')) = toLower($entity)
    RETURN count(n) AS total
"""

QUERY_GET_SUBGRAPH_TEMPLATE = """
    // find the start node by name (any of a few common fields), then pick one
    MATCH (start)
    WHERE toLower(coalesce(start.label, ''))     = toLower($entity)
       OR toLower(coalesce(start.name, ''))      = toLower($entity)
       OR toLower(toString(coalesce(start.nodeId, ''))) = toLower($entity)
       OR toLower(coalesce(start.symbol, ''))    = toLower($entity)
       OR toLower(coalesce(start.entryName, '')) = toLower($entity)
    // if several nodes share the name, keep the most-connected one
    WITH start ORDER BY COUNT { (start)--() } DESC LIMIT 1

    // APOC bounded BFS spanning tree (each node once, shortest path)
    CALL apoc.path.spanningTree(start, {
        minLevel: 1,
        maxLevel: toInteger($max_hops),
        bfs: true,
        limit: toInteger($max_nodes),
        relationshipFilter: $rel_filter,
        labelFilter: $label_filter
    }) YIELD path
    WITH start, collect(path) AS paths
    WITH start,
         apoc.coll.toSet(apoc.coll.flatten([p IN paths | nodes(p)])) AS ns,
         apoc.coll.toSet(apoc.coll.flatten([p IN paths | relationships(p)])) AS rs

    // Build node maps in an isolated subquery: UNWIND rebinds each node to a real
    // variable so property access is on a variable (not a list-comprehension local).
    // This sidesteps the Neo4j "Property cannot be cast to ASTCachedProperty" planner bug.
    CALL {
        WITH ns
        UNWIND ns AS n
        RETURN collect({
            id: coalesce(toString(n.nodeId), toString(id(n))),
            labels: labels(n),
            name: coalesce(n.label, n.name, toString(n.nodeId)),
            properties: properties(n)
        }) AS node_maps
    }

    // Build relationship maps the same way.
    CALL {
        WITH rs
        UNWIND rs AS r
        WITH startNode(r) AS sn, endNode(r) AS en, r
        RETURN collect({
            type: type(r),
            start: coalesce(toString(sn.nodeId), toString(id(sn))),
            end: coalesce(toString(en.nodeId), toString(id(en))),
            properties: properties(r)
        }) AS rel_maps
    }

    RETURN {
        start: {
            id: coalesce(toString(start.nodeId), toString(id(start))),
            labels: labels(start),
            name: coalesce(start.label, start.name, toString(start.nodeId))
        },
        node_count: size(node_maps),
        relationship_count: size(rel_maps),
        nodes: node_maps,
        relationships: rel_maps
    } AS subgraph
"""
 