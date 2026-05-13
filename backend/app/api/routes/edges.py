from fastapi import APIRouter, HTTPException
from app.db.neo4j import get_session
from app.models.domain import EdgeCreate, EdgeResponse

router = APIRouter(prefix="/edges", tags=["edges"])


@router.post("", response_model=EdgeResponse, status_code=201)
async def create_edge(body: EdgeCreate):
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
