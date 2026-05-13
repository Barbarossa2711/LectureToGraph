import uuid
from fastapi import APIRouter, HTTPException
from app.db.neo4j import get_session
from app.models.domain import NodeCreate, NodeUpdate, NodeResponse, NodeType, EdgeType

router = APIRouter(prefix="/nodes", tags=["nodes"])

# Mapping from NodeType to the edge that connects it to its parent
_PARENT_EDGE: dict[NodeType, EdgeType] = {
    NodeType.CHAPTER: EdgeType.HAS_CHAPTER,
    NodeType.TOPIC: EdgeType.HAS_TOPIC,
    NodeType.SUBTOPIC: EdgeType.HAS_SUBTOPIC,
    NodeType.CONCEPT: EdgeType.HAS_CONCEPT,
    NodeType.REVIEW_QUESTION: EdgeType.HAS_REVIEW_QUESTION,
}


@router.post("", response_model=NodeResponse, status_code=201)
async def create_node(body: NodeCreate):
    node_id = str(uuid.uuid4())
    props = body.properties.model_dump(exclude_none=True)
    props["id"] = node_id
    label = body.node_type.value

    async with get_session() as session:
        # Verify lecture exists
        check = await session.run(
            "MATCH (l:Lecture {id: $id}) RETURN l", id=body.lecture_id
        )
        if not await check.single():
            raise HTTPException(404, "Lecture not found")

        # Create node
        await session.run(f"CREATE (n:{label} $props)", props=props)

        # Attach to lecture with belongs-to edge
        edge_type = _PARENT_EDGE.get(body.node_type, EdgeType.HAS_CONCEPT)
        if body.node_type == NodeType.CHAPTER:
            await session.run(
                f"MATCH (l:Lecture {{id: $lid}}), (n:{label} {{id: $nid}}) "
                f"CREATE (l)-[:{edge_type.value}]->(n)",
                lid=body.lecture_id,
                nid=node_id,
            )

    return NodeResponse(id=node_id, node_type=body.node_type, properties=props)


@router.get("/{node_id}", response_model=NodeResponse)
async def get_node(node_id: str):
    async with get_session() as session:
        result = await session.run(
            "MATCH (n {id: $id}) RETURN n, labels(n) AS labels", id=node_id
        )
        record = await result.single()
    if not record:
        raise HTTPException(404, "Node not found")
    return _map_node(record)


@router.put("/{node_id}", response_model=NodeResponse)
async def update_node(node_id: str, body: NodeUpdate):
    updates = body.properties.model_dump(exclude_none=True)
    if not updates:
        raise HTTPException(400, "No fields to update")
    set_clause = ", ".join(f"n.{k} = ${k}" for k in updates)
    async with get_session() as session:
        result = await session.run(
            f"MATCH (n {{id: $id}}) SET {set_clause} RETURN n, labels(n) AS labels",
            id=node_id,
            **updates,
        )
        record = await result.single()
    if not record:
        raise HTTPException(404, "Node not found")
    return _map_node(record)


@router.delete("/{node_id}", status_code=204)
async def delete_node(node_id: str):
    async with get_session() as session:
        result = await session.run(
            "MATCH (n {id: $id}) DETACH DELETE n RETURN count(n) AS deleted",
            id=node_id,
        )
        record = await result.single()
    if not record or record["deleted"] == 0:
        raise HTTPException(404, "Node not found")


def _map_node(record) -> NodeResponse:
    node = record["n"]
    labels = record["labels"]
    node_label = next((l for l in labels if l != "Lecture"), labels[0])
    props = dict(node)
    return NodeResponse(
        id=props.pop("id"),
        node_type=NodeType(node_label),
        properties=props,
    )
