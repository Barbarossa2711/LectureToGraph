"""Execute multi-statement .cypher files against the staging Neo4j, and the
scoped reset/export helpers the pipeline needs between stages."""
from __future__ import annotations

import re
from pathlib import Path

from neo4j import AsyncGraphDatabase

from app.db.neo4j import get_driver

# From inside the backend container, the user's host (e.g. Neo4j Desktop) is not
# at 127.0.0.1 — that's the container itself. Docker exposes the host as
# host.docker.internal (enabled via extra_hosts in docker-compose).
_LOCALHOST_RE = re.compile(r"(://)(127\.0\.0\.1|localhost)(?=[:/]|$)")


def rewrite_host_for_container(uri: str) -> str:
    return _LOCALHOST_RE.sub(r"\1host.docker.internal", uri)


def split_statements(text: str) -> list[str]:
    """Split a .cypher file into statements, honouring single-quoted strings
    (with backslash escapes) and stripping `//` line comments."""
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
        # not in a string
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
    return stmt.lstrip().upper().startswith("CREATE CONSTRAINT")


async def load_cypher_text(text: str, *, driver=None, database: str | None = None) -> dict:
    """Load constraints (auto-commit) then data MERGEs (single write tx).

    Defaults to the bundled staging driver; pass `driver`/`database` to load into
    an arbitrary Neo4j (used by the optional external-upload feature)."""
    statements = split_statements(text)
    constraints = [s for s in statements if _is_constraint(s)]
    data = [s for s in statements if not _is_constraint(s)]

    driver = driver or get_driver()
    session_kw = {"database": database} if database else {}
    async with driver.session(**session_kw) as session:
        for c in constraints:
            await session.run(c)

        async def _write(tx):
            for s in data:
                await tx.run(s)

        if data:
            await session.execute_write(_write)

    return {"constraints": len(constraints), "statements": len(data)}


async def load_cypher_file(path: Path) -> dict:
    return await load_cypher_text(path.read_text(encoding="utf-8"))


async def upload_to_external(
    uri: str, user: str, password: str, text: str, database: str | None = None
) -> dict:
    """Load a cypher document into an external Neo4j using user-supplied creds.

    Opens a throw-away driver, verifies connectivity, loads, and closes it."""
    driver = AsyncGraphDatabase.driver(rewrite_host_for_container(uri), auth=(user, password))
    try:
        await driver.verify_connectivity()
        return await load_cypher_text(text, driver=driver, database=database)
    finally:
        await driver.close()


# ── scoped reset / export helpers (scope = lecture.code id prefix) ───────────

async def delete_scope(code: str) -> None:
    driver = get_driver()
    async with driver.session() as session:
        await session.run(
            "MATCH (n) WHERE n.id STARTS WITH $code DETACH DELETE n", code=code
        )


async def delete_edge_types(code: str, types: list[str]) -> None:
    rel = "|".join(types)
    driver = get_driver()
    async with driver.session() as session:
        await session.run(
            f"MATCH (a)-[r:{rel}]->(b) "
            "WHERE a.id STARTS WITH $code AND b.id STARTS WITH $code DELETE r",
            code=code,
        )


async def delete_questions(code: str) -> None:
    driver = get_driver()
    async with driver.session() as session:
        await session.run(
            "MATCH (q:Question) WHERE q.id STARTS WITH $code DETACH DELETE q",
            code=code,
        )


# ── chapter-scoped helpers (one chapter is processed at a time) ──────────────

def chapter_prefix(code: str, chapter_no: int) -> str:
    return f"{code}_CH{chapter_no:02d}"


async def delete_chapter(code: str, chapter_no: int) -> None:
    """Delete one chapter's subtree (Chapter/Topic/Subtopic/Concept/Question nodes)."""
    pref = chapter_prefix(code, chapter_no)
    driver = get_driver()
    async with driver.session() as session:
        await session.run(
            "MATCH (n) WHERE n.id STARTS WITH $pref DETACH DELETE n", pref=pref
        )


async def delete_edge_types_in_chapter(code: str, chapter_no: int, types: list[str]) -> None:
    """Delete the concept edges originating from this chapter's concepts."""
    pref = chapter_prefix(code, chapter_no)
    rel = "|".join(types)
    driver = get_driver()
    async with driver.session() as session:
        await session.run(
            f"MATCH (a)-[r:{rel}]->(b) WHERE a.id STARTS WITH $pref DELETE r",
            pref=pref,
        )


async def delete_questions_in_chapter(code: str, chapter_no: int) -> None:
    pref = chapter_prefix(code, chapter_no)
    driver = get_driver()
    async with driver.session() as session:
        await session.run(
            "MATCH (q:Question) WHERE q.id STARTS WITH $pref DETACH DELETE q", pref=pref
        )


async def delete_orphan_slides_in_chapter(code: str, chapter_no: int) -> int:
    """Remove this chapter's content-less slides — :Slide nodes that cover no
    concept (no outgoing COVERS edge), e.g. table-of-contents / agenda / divider
    slides. Returns how many were deleted."""
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
    """A scoped query returning ONLY what the given stage added for this chapter
    (plus the endpoints of new edges), for the 'show only latest changes' view."""
    pref = chapter_prefix(code, chapter_no)
    if stage == "EDGES":
        # the concept edges created for this chapter, with both endpoints
        return (
            f"MATCH (a)-[r:PREREQUISITE|FACILITATOR|SAME_AS]->(b) "
            f"WHERE a.id STARTS WITH '{pref}' RETURN a, r, b"
        )
    if stage == "QUESTIONS":
        # this chapter's Question nodes and their HAS_QUESTION / TESTS edges + endpoints
        return (
            f"MATCH (q:Question) WHERE q.id STARTS WITH '{pref}' "
            f"OPTIONAL MATCH (c)-[hq:HAS_QUESTION]->(q) "
            f"OPTIONAL MATCH (q)-[t:TESTS]->(con) "
            f"RETURN q, hq, c, t, con"
        )
    # DOMAIN (or default): the chapter subtree (now includes this chapter's Slide
    # nodes and COVERS edges, since their ids share the chapter prefix)
    return (
        f"MATCH (n) WHERE n.id STARTS WITH '{pref}' "
        f"OPTIONAL MATCH (n)-[r]->(m) WHERE m.id STARTS WITH '{pref}' "
        f"RETURN n, r, m"
    )


def _esc(v) -> str:
    return str(v).replace("\\", "\\\\").replace("'", "\\'")


def _fmt(v) -> str:
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, (int, float)):
        return str(v)
    return "'" + _esc(v) + "'"


async def export_full_graph_cypher(code: str) -> str:
    """Serialize the CURRENT staged graph for a lecture (nodes with all properties
    + every relationship) to idempotent Cypher. Reflects manual edits made at the
    validation gates, so the downloaded file matches what you see in the graph."""
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
    """Serialize EVERYTHING belonging to one chapter into a single, self-contained
    idempotent .cypher file: the Lecture node, the chapter subtree (Chapter/Topic/
    Subtopic/Concept/Question/Slide), and every relationship originating in the
    chapter (HAS_*, PREREQUISITE/FACILITATOR/SAME_AS, TESTS, COVERS). This is the
    consolidated 'one file per chapter' output — a merge of the per-stage files,
    read back from Neo4j so it also reflects manual edits."""
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
        # the Lecture node first, so the file loads stand-alone
        lec = await session.run(
            "MATCH (l:Lecture {id:$code}) RETURN properties(l) AS props", code=code)
        lrec = await lec.single()
        if lrec:
            props = dict(lrec["props"])
            assigns = ", ".join(f"n.{k}={_fmt(v)}" for k, v in props.items())
            lines.append(f"MERGE (n:Lecture {{id:'{_esc(code)}'}})\n  SET {assigns};")
        # the chapter subtree (all ids share the chapter prefix)
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
        # the Lecture -> Chapter link (its source is the Lecture, outside the prefix)
        lines.append(
            f"MATCH (a {{id:'{_esc(code)}'}}), (b {{id:'{_esc(pref)}'}}) "
            "MERGE (a)-[:HAS_CHAPTER]->(b);")
        # every relationship that originates in this chapter (intra-chapter edges and
        # any outgoing cross-chapter edge; the other endpoint is matched if present)
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
    """Dump the :Slide nodes already staged for a lecture (all properties) plus
    their COVERS edges, so the slides stage of a LATER chapter sees what already
    exists and reuses ids instead of creating duplicate slide nodes."""
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
    """Dump the staged nodes for a lecture as `MERGE (n:Label {id:'...'})` lines,
    so the stage-2/3 verifier scripts (which glob `.cypher` files) and the agent
    see the current, possibly hand-edited, domain."""
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
