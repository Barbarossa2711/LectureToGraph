"""
Executes multi-statement .cypher files against Neo4j and provides the lecture- and
chapter-scoped delete and export helpers the pipeline needs between stages.
"""
from __future__ import annotations

import re
from pathlib import Path

from neo4j import AsyncGraphDatabase

from app.db.neo4j import get_driver

# Inside the backend container, 127.0.0.1 is the container itself, not the user's
# host (e.g. Neo4j Desktop). Docker exposes the host as host.docker.internal
# (enabled via extra_hosts in docker-compose).
_LOCALHOST_RE = re.compile(r"(://)(127\.0\.0\.1|localhost)(?=[:/]|$)")


def rewrite_host_for_container(uri: str) -> str:
    """
    Replace localhost or 127.0.0.1 in a URI with host.docker.internal.

    :param uri: The Neo4j URI entered by the user.
    :return: The URI reachable from inside the container.
    """
    return _LOCALHOST_RE.sub(r"\1host.docker.internal", uri)


def split_statements(text: str) -> list[str]:
    """
    Split a .cypher file into statements at semicolons.

    Semicolons inside single-quoted strings (with backslash escapes) are kept;
    // line comments are removed.

    :param text: The Cypher text.
    :return: The non-empty statements without trailing semicolon.
    """
    stmts: list[str] = []
    buf: list[str] = []
    in_str = False
    escape = False
    i = 0
    n = len(text)
    while i < n:
        ch = text[i]
        if in_str:
            buf.append(ch)
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == "'":
                in_str = False
            i += 1
            continue
        if ch == "/" and i + 1 < n and text[i + 1] == "/":
            j = text.find("\n", i)
            i = n if j == -1 else j
            continue
        if ch == "'":
            in_str = True
            buf.append(ch)
            i += 1
            continue
        if ch == ";":
            stmt = "".join(buf).strip()
            if stmt:
                stmts.append(stmt)
            buf = []
            i += 1
            continue
        buf.append(ch)
        i += 1
    tail = "".join(buf).strip()
    if tail:
        stmts.append(tail)
    return stmts


def _is_constraint(stmt: str) -> bool:
    """
    Check whether a statement creates a constraint.

    :param stmt: The Cypher statement.
    :return: True for CREATE CONSTRAINT statements.
    """
    return stmt.lstrip().upper().startswith("CREATE CONSTRAINT")


async def load_cypher_text(text: str, *, driver=None, database: str | None = None) -> dict:
    """
    Run a Cypher document: first the constraints in auto-commit mode, then all other
    statements in one write transaction.

    :param text: The Cypher text.
    :param driver: The target driver, or None for the bundled staging database.
    :param database: The target database, or None for the default database.
    :return: The number of constraints and of other statements.
    """
    statements = split_statements(text)
    constraints = [s for s in statements if _is_constraint(s)]
    data = [s for s in statements if not _is_constraint(s)]

    driver = driver or get_driver()
    session_kw = {"database": database} if database else {}
    async with driver.session(**session_kw) as session:
        for c in constraints:
            await session.run(c)

        async def _write(tx):
            """
            Run all data statements in the given transaction.

            :param tx: The write transaction.
            :return: None
            """
            for s in data:
                await tx.run(s)

        if data:
            await session.execute_write(_write)

    return {"constraints": len(constraints), "statements": len(data)}


async def load_cypher_file(path: Path) -> dict:
    """
    Run a .cypher file against the staging database.

    :param path: The path of the file.
    :return: The number of constraints and of other statements.
    """
    return await load_cypher_text(path.read_text(encoding="utf-8"))


async def upload_to_external(
    uri: str, user: str, password: str, text: str, database: str | None = None
) -> dict:
    """
    Load a Cypher document into an external Neo4j with a temporary driver.

    :param uri: The bolt URI; localhost is rewritten to reach the Docker host.
    :param user: The user name.
    :param password: The password.
    :param text: The Cypher text.
    :param database: The target database, or None for the default database.
    :return: The number of constraints and of other statements.
    """
    driver = AsyncGraphDatabase.driver(rewrite_host_for_container(uri), auth=(user, password))
    try:
        await driver.verify_connectivity()
        return await load_cypher_text(text, driver=driver, database=database)
    finally:
        await driver.close()


async def delete_scope(code: str) -> None:
    """
    Delete every node of a lecture, i.e. every node whose id starts with its code.

    :param code: The lecture code.
    :return: None
    """
    driver = get_driver()
    async with driver.session() as session:
        await session.run(
            "MATCH (n) WHERE n.id STARTS WITH $code DETACH DELETE n", code=code
        )


async def delete_edge_types(code: str, types: list[str]) -> None:
    """
    Delete all edges of the given types within a lecture.

    :param code: The lecture code.
    :param types: The relationship types.
    :return: None
    """
    rel = "|".join(types)
    driver = get_driver()
    async with driver.session() as session:
        await session.run(
            f"MATCH (a)-[r:{rel}]->(b) "
            "WHERE a.id STARTS WITH $code AND b.id STARTS WITH $code DELETE r",
            code=code,
        )


async def delete_questions(code: str) -> None:
    """
    Delete all Question nodes of a lecture.

    :param code: The lecture code.
    :return: None
    """
    driver = get_driver()
    async with driver.session() as session:
        await session.run(
            "MATCH (q:Question) WHERE q.id STARTS WITH $code DETACH DELETE q",
            code=code,
        )


def chapter_prefix(code: str, chapter_no: int) -> str:
    """
    Build the id prefix shared by all nodes of a chapter.

    :param code: The lecture code.
    :param chapter_no: The chapter number.
    :return: The prefix <CODE>_CHNN.
    """
    return f"{code}_CH{chapter_no:02d}"


async def delete_chapter(code: str, chapter_no: int) -> None:
    """
    Delete every node of a chapter with its edges.

    :param code: The lecture code.
    :param chapter_no: The chapter number.
    :return: None
    """
    pref = chapter_prefix(code, chapter_no)
    driver = get_driver()
    async with driver.session() as session:
        await session.run(
            "MATCH (n) WHERE n.id STARTS WITH $pref DETACH DELETE n", pref=pref
        )


async def delete_edge_types_in_chapter(code: str, chapter_no: int, types: list[str]) -> None:
    """
    Delete the edges of the given types that start in a chapter.

    :param code: The lecture code.
    :param chapter_no: The chapter number.
    :param types: The relationship types.
    :return: None
    """
    pref = chapter_prefix(code, chapter_no)
    rel = "|".join(types)
    driver = get_driver()
    async with driver.session() as session:
        await session.run(
            f"MATCH (a)-[r:{rel}]->(b) WHERE a.id STARTS WITH $pref DELETE r",
            pref=pref,
        )


async def delete_questions_in_chapter(code: str, chapter_no: int) -> None:
    """
    Delete the Question nodes of a chapter.

    :param code: The lecture code.
    :param chapter_no: The chapter number.
    :return: None
    """
    pref = chapter_prefix(code, chapter_no)
    driver = get_driver()
    async with driver.session() as session:
        await session.run(
            "MATCH (q:Question) WHERE q.id STARTS WITH $pref DETACH DELETE q", pref=pref
        )


async def delete_orphan_slides_in_chapter(code: str, chapter_no: int) -> int:
    """
    Delete the chapter's Slide nodes without a COVERS edge, e.g. table of contents or agenda slides.

    :param code: The lecture code.
    :param chapter_no: The chapter number.
    :return: The number of deleted slides.
    """
    pref = chapter_prefix(code, chapter_no)
    driver = get_driver()
    async with driver.session() as session:
        result = await session.run(
            "MATCH (s:Slide) WHERE s.id STARTS WITH $pref AND NOT (s)-[:COVERS]->() "
            "DETACH DELETE s RETURN count(s) AS n",
            pref=pref,
        )
        rec = await result.single()
        return int(rec["n"]) if rec else 0


def last_change_cypher(code: str, stage: str, chapter_no: int) -> str:
    """
    Build the query for the "latest changes" view: what a stage added in a chapter,
    plus the endpoints of new edges.

    For the domain stage this is the chapter subtree, which includes its Slide nodes
    and COVERS edges, since their ids share the chapter prefix.

    :param code: The lecture code.
    :param stage: The stage value, "DOMAIN", "EDGES" or "QUESTIONS".
    :param chapter_no: The chapter number.
    :return: The Cypher query.
    """
    pref = chapter_prefix(code, chapter_no)
    if stage == "EDGES":
        return (
            f"MATCH (a)-[r:PREREQUISITE|FACILITATOR|SAME_AS]->(b) "
            f"WHERE a.id STARTS WITH '{pref}' RETURN a, r, b"
        )
    if stage == "QUESTIONS":
        return (
            f"MATCH (q:Question) WHERE q.id STARTS WITH '{pref}' "
            f"OPTIONAL MATCH (c)-[hq:HAS_QUESTION]->(q) "
            f"OPTIONAL MATCH (q)-[t:TESTS]->(con) "
            f"RETURN q, hq, c, t, con"
        )
    return (
        f"MATCH (n) WHERE n.id STARTS WITH '{pref}' "
        f"OPTIONAL MATCH (n)-[r]->(m) WHERE m.id STARTS WITH '{pref}' "
        f"RETURN n, r, m"
    )


def _esc(v) -> str:
    """
    Escape a value for a single-quoted Cypher string.

    :param v: The value.
    :return: The value as string with backslashes and apostrophes escaped.
    """
    return str(v).replace("\\", "\\\\").replace("'", "\\'")


def _fmt(v) -> str:
    """
    Format a property value as Cypher literal.

    :param v: The value.
    :return: A boolean, number or quoted string literal.
    """
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, (int, float)):
        return str(v)
    return "'" + _esc(v) + "'"


async def export_full_graph_cypher(code: str) -> str:
    """
    Export the lecture's current graph with all node properties and relationships as
    idempotent Cypher.

    The export is read from Neo4j, so it contains the manual edits made at the
    validation gates and matches what the graph view shows.

    :param code: The lecture code.
    :return: The Cypher text.
    """
    driver = get_driver()
    lines = [
        "// Full export of the current staged graph (includes manual edits).",
        "// Idempotent: safe to load into any Neo4j with MERGE.",
        "",
    ]
    async with driver.session() as session:
        nodes = await session.run(
            "MATCH (n) WHERE n.id STARTS WITH $code "
            "RETURN labels(n)[0] AS label, properties(n) AS props ORDER BY n.id",
            code=code,
        )
        lines.append("// --- Nodes ---")
        async for rec in nodes:
            props = dict(rec["props"])
            nid = props.get("id")
            assigns = ", ".join(f"n.{k}={_fmt(v)}" for k, v in props.items())
            lines.append(f"MERGE (n:{rec['label']} {{id:'{_esc(nid)}'}})\n  SET {assigns};")

        rels = await session.run(
            "MATCH (a)-[r]->(b) WHERE a.id STARTS WITH $code AND b.id STARTS WITH $code "
            "RETURN a.id AS s, type(r) AS t, b.id AS o ORDER BY s, t, o",
            code=code,
        )
        lines.append("")
        lines.append("// --- Relationships ---")
        async for rec in rels:
            lines.append(
                "MATCH (a {{id:'{s}'}}), (b {{id:'{o}'}}) MERGE (a)-[:{t}]->(b);".format(
                    s=_esc(rec["s"]), o=_esc(rec["o"]), t=rec["t"]))
    return "\n".join(lines) + "\n"


_CONSTRAINT_LABELS = ["Lecture", "Chapter", "Topic", "Subtopic", "Concept", "Question", "Slide"]


async def export_chapter_cypher(code: str, chapter_no: int) -> str:
    """
    Export everything belonging to one chapter as a self-contained, idempotent Cypher file.

    The file contains the constraints, the Lecture node, all nodes of the chapter and
    every relationship starting in the chapter. It replaces the per-stage files and is
    read from Neo4j, so it contains manual edits.

    :param code: The lecture code.
    :param chapter_no: The chapter number.
    :return: The Cypher text.
    """
    pref = chapter_prefix(code, chapter_no)
    driver = get_driver()
    lines = [
        f"// Consolidated export of chapter {chapter_no} ({pref}) — single file per chapter.",
        "// Idempotent (MERGE) and self-contained: includes the Lecture node + HAS_CHAPTER.",
        "",
        "// --- Constraints ---",
    ]
    for label in _CONSTRAINT_LABELS:
        lines.append(
            f"CREATE CONSTRAINT {label.lower()}_id IF NOT EXISTS "
            f"FOR (n:{label}) REQUIRE n.id IS UNIQUE;"
        )
    lines.append("")
    async with driver.session() as session:
        lines.append("// --- Nodes ---")
        # The Lecture node comes first, so the file loads on its own.
        lec = await session.run(
            "MATCH (l:Lecture {id:$code}) RETURN properties(l) AS props", code=code)
        lrec = await lec.single()
        if lrec:
            props = dict(lrec["props"])
            assigns = ", ".join(f"n.{k}={_fmt(v)}" for k, v in props.items())
            lines.append(f"MERGE (n:Lecture {{id:'{_esc(code)}'}})\n  SET {assigns};")
        nodes = await session.run(
            "MATCH (n) WHERE n.id STARTS WITH $pref "
            "RETURN labels(n)[0] AS label, properties(n) AS props ORDER BY n.id",
            pref=pref,
        )
        async for rec in nodes:
            props = dict(rec["props"])
            assigns = ", ".join(f"n.{k}={_fmt(v)}" for k, v in props.items())
            lines.append(f"MERGE (n:{rec['label']} {{id:'{_esc(props.get('id'))}'}})\n  SET {assigns};")

        lines.append("")
        lines.append("// --- Relationships ---")
        # The Lecture node lies outside the chapter prefix, so HAS_CHAPTER is added explicitly.
        lines.append(
            f"MATCH (a {{id:'{_esc(code)}'}}), (b {{id:'{_esc(pref)}'}}) "
            "MERGE (a)-[:HAS_CHAPTER]->(b);")
        # Includes edges into other chapters; they are created if the target exists.
        rels = await session.run(
            "MATCH (a)-[r]->(b) WHERE a.id STARTS WITH $pref "
            "RETURN a.id AS s, type(r) AS t, b.id AS o ORDER BY s, t, o",
            pref=pref,
        )
        async for rec in rels:
            lines.append(
                "MATCH (a {{id:'{s}'}}), (b {{id:'{o}'}}) MERGE (a)-[:{t}]->(b);".format(
                    s=_esc(rec["s"]), o=_esc(rec["o"]), t=rec["t"]))
    return "\n".join(lines) + "\n"


async def export_slides_cypher(code: str) -> str:
    """
    Export the lecture's existing Slide nodes and their COVERS edges.

    The domain stage of a later chapter reads this file to reuse slide ids instead
    of creating duplicates.

    :param code: The lecture code.
    :return: The Cypher text.
    """
    driver = get_driver()
    lines = [
        "// Existing :Slide nodes already in the graph.",
        "// Do NOT recreate these — reuse the exact same id if you encounter the same page again.",
        "",
    ]
    async with driver.session() as session:
        nodes = await session.run(
            "MATCH (s:Slide) WHERE s.id STARTS WITH $code "
            "RETURN properties(s) AS props ORDER BY s.id",
            code=code,
        )
        async for rec in nodes:
            props = dict(rec["props"])
            assigns = ", ".join(f"s.{k}={_fmt(v)}" for k, v in props.items())
            lines.append(f"MERGE (s:Slide {{id:'{_esc(props.get('id'))}'}})\n  SET {assigns};")
        rels = await session.run(
            "MATCH (s:Slide)-[:COVERS]->(c:Concept) WHERE s.id STARTS WITH $code "
            "RETURN s.id AS s, c.id AS c ORDER BY s, c",
            code=code,
        )
        async for rec in rels:
            lines.append(
                "MATCH (s:Slide {{id:'{s}'}}), (c:Concept {{id:'{c}'}}) "
                "MERGE (s)-[:COVERS]->(c);".format(s=_esc(rec["s"]), c=_esc(rec["c"])))
    return "\n".join(lines) + "\n"


async def export_domain_cypher(code: str) -> str:
    """
    Export the ids and labels of the lecture's nodes as MERGE lines.

    The agent and the verification scripts of stages 2 and 3 read this file to
    see the current, possibly manually edited, domain model.

    :param code: The lecture code.
    :return: The Cypher text.
    """
    driver = get_driver()
    lines = ["// Exported staged domain for verification."]
    async with driver.session() as session:
        result = await session.run(
            "MATCH (n) WHERE n.id STARTS WITH $code "
            "RETURN labels(n)[0] AS label, n.id AS id ORDER BY id",
            code=code,
        )
        async for rec in result:
            lines.append("MERGE (n:%s {id:'%s'})  SET n.id='%s';" % (
                rec["label"], rec["id"], rec["id"]))
    return "\n".join(lines) + "\n"
