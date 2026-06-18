from fastapi import APIRouter, HTTPException
from app.db.neo4j import get_session
from app.models.domain import NodeCreate, NodeUpdate, NodeResponse, NodeType, PARENT_EDGE

router = APIRouter(prefix="/nodes", tags=["nodes"])


@router.post("", response_model=NodeResponse, status_code=201)
async def create_node(body: NodeCreate):
    label = body.node_type.value
    props = dict(body.properties)
    props["id"] = body.id

    async with get_session() as session:
        await session.run(f"MERGE (n:{label} {{id: $id}}) SET n += $props",
                          id=body.id, props=props)
        if body.parent_id:
            edge = PARENT_EDGE.get(body.node_type)
            if edge:
                ok = await session.run(
                    f"MATCH (p {{id: $pid}}), (n:{label} {{id: $nid}}) "
                    f"MERGE (p)-[:{edge.value}]->(n) RETURN p",
                    pid=body.parent_id, nid=body.id,
                )
                if not await ok.single():
                    raise HTTPException(404, "Parent node not found")

    return NodeResponse(id=body.id, node_type=body.node_type, properties=props)


@router.put("/{node_id}", response_model=NodeResponse)
async def update_node(node_id: str, body: NodeUpdate):
    updates = {k: v for k, v in body.properties.items() if k != "id"}
    async with get_session() as session:
        result = await session.run(
            "MATCH (n {id: $id}) SET n += $props RETURN n, labels(n) AS labels",
            id=node_id, props=updates,
        )
        record = await result.single()
    if not record:
        raise HTTPException(404, "Node not found")
    return _map_node(record)


@router.delete("/{node_id}", status_code=204)
async def delete_node(node_id: str):
    async with get_session() as session:
        result = await session.run(
            "MATCH (n {id: $id}) DETACH DELETE n RETURN count(n) AS deleted", id=node_id,
        )
        record = await result.single()
    if not record or record["deleted"] == 0:
        raise HTTPException(404, "Node not found")


def _map_node(record) -> NodeResponse:
    node = record["n"]
    labels = record["labels"]
    node_label = next((l for l in labels if l in {t.value for t in NodeType}), labels[0])
    props = dict(node)
    return NodeResponse(id=props["id"], node_type=NodeType(node_label), properties=props)
