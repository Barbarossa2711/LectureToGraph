from fastapi import APIRouter, HTTPException
from app.db.neo4j import get_session
from app.models.domain import EdgeCreate, EdgeResponse

router = APIRouter(prefix="/edges", tags=["edges"])


@router.post("", response_model=EdgeResponse, status_code=201)
async def create_edge(body: EdgeCreate):
    """
    Create an edge between two nodes unless it exists.

    :param body: Source id, target id and edge type.
    :return: The edge.
    :raises HTTPException: 404 if a node is missing.
    """
    rel_type = body.edge_type.value
    async with get_session() as session:
        result = await session.run(
            f"""
            MATCH (a {{id: $source_id}}), (b {{id: $target_id}})
            MERGE (a)-[r:{rel_type}]->(b)
            RETURN r
            """,
            source_id=body.source_id,
            target_id=body.target_id,
        )
        record = await result.single()
    if not record:
        raise HTTPException(404, "One or both nodes not found")
    return EdgeResponse(
        source_id=body.source_id,
        target_id=body.target_id,
        edge_type=body.edge_type,
    )


@router.delete("", status_code=204)
async def delete_edge(source_id: str, target_id: str, edge_type: str):
    """
    Delete the edges of a type between two nodes.

    :param source_id: The id of the source node.
    :param target_id: The id of the target node.
    :param edge_type: The relationship type.
    :return: None
    :raises HTTPException: 404 if no edge matched.
    """
    async with get_session() as session:
        result = await session.run(
            f"""
            MATCH (a {{id: $source_id}})-[r:{edge_type}]->(b {{id: $target_id}})
            DELETE r
            RETURN count(r) AS deleted
            """,
            source_id=source_id,
            target_id=target_id,
        )
        record = await result.single()
    if not record or record["deleted"] == 0:
        raise HTTPException(404, "Edge not found")
