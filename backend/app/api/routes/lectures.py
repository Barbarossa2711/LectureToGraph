import uuid
from fastapi import APIRouter, HTTPException
from app.db.neo4j import get_session
from app.models.domain import LectureCreate, LectureUpdate, LectureResponse

router = APIRouter(prefix="/lectures", tags=["lectures"])


@router.get("", response_model=list[LectureResponse])
async def list_lectures():
    async with get_session() as session:
        result = await session.run("MATCH (l:Lecture) RETURN l")
        records = await result.data()
    return [_map_lecture(r["l"]) for r in records]


@router.post("", response_model=LectureResponse, status_code=201)
async def create_lecture(body: LectureCreate):
    lecture_id = str(uuid.uuid4())
    props = {"id": lecture_id, **body.model_dump(exclude_none=True)}
    async with get_session() as session:
        result = await session.run(
            "CREATE (l:Lecture $props) RETURN l", props=props
        )
        record = await result.single()
    return _map_lecture(record["l"])


@router.get("/{lecture_id}", response_model=LectureResponse)
async def get_lecture(lecture_id: str):
    async with get_session() as session:
        result = await session.run(
            "MATCH (l:Lecture {id: $id}) RETURN l", id=lecture_id
        )
        record = await result.single()
    if not record:
        raise HTTPException(404, "Lecture not found")
    return _map_lecture(record["l"])


@router.put("/{lecture_id}", response_model=LectureResponse)
async def update_lecture(lecture_id: str, body: LectureUpdate):
    updates = body.model_dump(exclude_none=True)
    if not updates:
        raise HTTPException(400, "No fields to update")
    set_clause = ", ".join(f"l.{k} = ${k}" for k in updates)
    async with get_session() as session:
        result = await session.run(
            f"MATCH (l:Lecture {{id: $id}}) SET {set_clause} RETURN l",
            id=lecture_id,
            **updates,
        )
        record = await result.single()
    if not record:
        raise HTTPException(404, "Lecture not found")
    return _map_lecture(record["l"])


@router.delete("/{lecture_id}", status_code=204)
async def delete_lecture(lecture_id: str):
    async with get_session() as session:
        result = await session.run(
            """
            MATCH (l:Lecture {id: $id})
            OPTIONAL MATCH (l)-[*]->(n)
            DETACH DELETE l, n
            RETURN count(l) AS deleted
            """,
            id=lecture_id,
        )
        record = await result.single()
    if not record or record["deleted"] == 0:
        raise HTTPException(404, "Lecture not found")


def _map_lecture(node) -> LectureResponse:
    return LectureResponse(
        id=node["id"],
        title=node["title"],
        professor=node["professor"],
        description=node.get("description"),
        semester=node.get("semester"),
    )
