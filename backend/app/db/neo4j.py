from contextlib import asynccontextmanager
from neo4j import AsyncGraphDatabase, AsyncDriver
from app.config import settings

_driver: AsyncDriver | None = None


async def init_driver() -> None:
    """
    Connect to the staging Neo4j and create the uniqueness constraints on node ids.

    :return: None
    """
    global _driver
    _driver = AsyncGraphDatabase.driver(
        settings.neo4j_uri,
        auth=(settings.neo4j_user, settings.neo4j_password),
    )
    await _driver.verify_connectivity()
    await _create_constraints()


async def close_driver() -> None:
    """
    Close the Neo4j driver if it is open.

    :return: None
    """
    global _driver
    if _driver:
        await _driver.close()
        _driver = None


def get_driver() -> AsyncDriver:
    """
    Return the shared Neo4j driver.

    :return: The driver created by init_driver.
    :raises RuntimeError: If init_driver has not run.
    """
    if _driver is None:
        raise RuntimeError("Neo4j driver not initialised")
    return _driver


@asynccontextmanager
async def get_session():
    """
    Open a Neo4j session on the shared driver.

    :return: An async context manager yielding the session.
    """
    async with get_driver().session() as session:
        yield session


async def _create_constraints() -> None:
    """
    Create a uniqueness constraint on id for every node label, if missing.

    :return: None
    """
    labels = ["Lecture", "Chapter", "Topic", "Subtopic", "Concept", "Question", "Slide"]
    async with get_driver().session() as session:
        for label in labels:
            await session.run(
                f"CREATE CONSTRAINT IF NOT EXISTS "
                f"FOR (n:{label}) REQUIRE n.id IS UNIQUE"
            )
