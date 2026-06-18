from fastapi import APIRouter
from app.db.neo4j import get_session
from app.models.domain import GraphResponse, GraphNode, GraphEdge, NodeType, EdgeType

router = APIRouter(prefix="/lectures", tags=["graph"])


@router.get("/{code}/graph", response_model=GraphResponse)
async def get_graph(code: str):
    """Scoped subgraph for a lecture (server-side fallback to neovis.js)."""
    node_labels = {t.value for t in NodeType}
    edge_types = {t.value for t in EdgeType}

    async with get_session() as session:
        nodes_result = await session.run(
            "MATCH (n) WHERE n.id STARTS WITH $code RETURN n, labels(n) AS labels",
            code=code,
        )
        nodes_records = await nodes_result.data()

        edges_result = await session.run(
            "MATCH (a)-[r]->(b) WHERE a.id STARTS WITH $code AND b.id STARTS WITH $code "
            "RETURN a.id AS source_id, type(r) AS rel_type, b.id AS target_id",
            code=code,
        )
        edges_records = await edges_result.data()

    nodes = []
    for r in nodes_records:
        node = r["node"] if "node" in r else r["n"]
        labels = r["labels"]
        node_label = next((l for l in labels if l in node_labels), labels[0])
        nodes.append(GraphNode(
            id=node["id"], node_type=NodeType(node_label), properties=dict(node),
        ))

    edges = []
    for r in edges_records:
        if r["rel_type"] not in edge_types:
            continue
        edges.append(GraphEdge(
            source_id=r["source_id"],
            target_id=r["target_id"],
            edge_type=EdgeType(r["rel_type"]),
        ))

    return GraphResponse(nodes=nodes, edges=edges)
