from contextlib import asynccontextmanager
from neo4j import AsyncGraphDatabase, AsyncDriver
from app.config import settings

_driver: AsyncDriver | None = None


async def init_driver() -> None:
    global _driver
    _driver = AsyncGraphDatabase.driver(
        settings.neo4j_uri,
        auth=(settings.neo4j_user, settings.neo4j_password),
    )
    await _driver.verify_connectivity()
    await _create_constraints()


async def close_driver() -> None:
    global _driver
    if _driver:
        await _driver.close()
        _driver = None


def get_driver() -> AsyncDriver:
    if _driver is None:
        raise RuntimeError("Neo4j driver not initialised")
    return _driver


@asynccontextmanager
async def get_session():
    async with get_driver().session() as session:
        yield session


async def _create_constraints() -> None:
    labels = ["Lecture", "Chapter", "Topic", "Subtopic", "Concept", "ReviewQuestion"]
    async with get_driver().session() as session:
        for label in labels:
            await session.run(
                f"CREATE CONSTRAINT ON (n:{label}) ASSERT n.id IS UNIQUE"
            )
