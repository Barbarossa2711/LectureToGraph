from fastapi import APIRouter, HTTPException
from app.db.neo4j import get_session
from app.models.domain import LectureSummary

router = APIRouter(prefix="/lectures", tags=["lectures"])


@router.get("", response_model=list[LectureSummary])
async def list_lectures():
    """
    List all lectures in the staging database.

    :return: The lectures ordered by name.
    """
    async with get_session() as session:
        result = await session.run("MATCH (l:Lecture) RETURN l ORDER BY l.name")
        records = await result.data()
    return [_map(r["l"]) for r in records]


@router.delete("/{code}", status_code=204)
async def delete_lecture(code: str):
    """
    Delete a lecture and every node whose id starts with its code.

    :param code: The lecture code.
    :return: None
    :raises HTTPException: 404 if no node matched.
    """
    async with get_session() as session:
        result = await session.run(
            "MATCH (n) WHERE n.id STARTS WITH $code DETACH DELETE n RETURN count(n) AS d",
            code=code,
        )
        record = await result.single()
    if not record or record["d"] == 0:
        raise HTTPException(404, "Lecture not found")


def _map(node) -> LectureSummary:
    """
    Convert a Lecture node into its summary.

    :param node: The Neo4j Lecture node.
    :return: The lecture summary.
    """
    d = dict(node)
    return LectureSummary(
        id=d.get("id"), code=d.get("code", d.get("id")),
        name=d.get("name"), prof=d.get("prof"), term=d.get("term"),
    )
