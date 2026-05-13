from fastapi import APIRouter, HTTPException
from app.db.neo4j import get_session
from app.models.domain import GraphResponse, GraphNode, GraphEdge, NodeType, EdgeType

router = APIRouter(prefix="/lectures", tags=["graph"])


@router.get("/{lecture_id}/graph", response_model=GraphResponse)
async def get_graph(lecture_id: str):
    async with get_session() as session:
        # Check lecture exists
        check = await session.run(
            "MATCH (l:Lecture {id: $id}) RETURN l", id=lecture_id
        )
        if not await check.single():
            raise HTTPException(404, "Lecture not found")

        # Fetch all nodes reachable from this lecture
        nodes_result = await session.run(
            """
            MATCH (l:Lecture {id: $id})
            OPTIONAL MATCH (l)-[*]->(n)
            WITH collect(DISTINCT l) + collect(DISTINCT n) AS all_nodes
            UNWIND all_nodes AS node
            RETURN DISTINCT node, labels(node) AS labels
            """,
            id=lecture_id,
        )
        nodes_records = await nodes_result.data()

        # Fetch all edges within the subgraph
        edges_result = await session.run(
            """
            MATCH (l:Lecture {id: $id})
            OPTIONAL MATCH (l)-[*]->(n)
            WITH collect(DISTINCT l) + collect(DISTINCT n) AS all_nodes
            UNWIND all_nodes AS a
            MATCH (a)-[r]->(b)
            WHERE b IN all_nodes
            RETURN DISTINCT a.id AS source_id, type(r) AS rel_type, b.id AS target_id
            """,
            id=lecture_id,
        )
        edges_records = await edges_result.data()

    nodes = []
    for r in nodes_records:
        node = r["node"]
        labels = r["labels"]
        node_label = next(
            (l for l in labels if l in {t.value for t in NodeType}), labels[0]
        )
        props = {k: v for k, v in dict(node).items() if k != "id"}
        nodes.append(GraphNode(id=node["id"], node_type=NodeType(node_label), properties=props))

    edges = []
    for r in edges_records:
        try:
            edge_type = EdgeType(r["rel_type"])
        except ValueError:
            continue
        edges.append(GraphEdge(
            source_id=r["source_id"],
            target_id=r["target_id"],
            edge_type=edge_type,
        ))

    return GraphResponse(nodes=nodes, edges=edges)
