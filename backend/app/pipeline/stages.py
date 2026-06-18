from __future__ import annotations

from app.skills.registry import Stage

# Relationship types each stage contributes (used to scope a re-run reset).
STAGE_EDGE_TYPES: dict[Stage, list[str]] = {
    Stage.EDGES: ["PREREQUISITE", "FACILITATOR", "SAME_AS"],
}


def _domain_kickoff(chapter_no: int, is_first: bool) -> str:
    chno = f"CH{chapter_no:02d}"
    if is_first:
        return (
            f"Stage 1 — domain model, CHAPTER {chapter_no} only. The uploaded lecture PDF(s) are "
            "already in your workspace; call list_dir(\".\") to see them and read them with read_pdf.\n\n"
            "First decide what kind of document you have:\n"
            "- If a PDF covers the WHOLE lecture (multiple chapters), read its table of contents / "
            "structure, list the chapters you detect WITH their page ranges, and call ask_user to let "
            "the user CONFIRM or correct that chapter breakdown. Then build ONLY the first chapter.\n"
            "- If a PDF is a SINGLE chapter, just process it as the first chapter.\n\n"
            f"Process EXACTLY ONE chapter now and number it {chno} (ids like <CODE>_{chno}, "
            f"<CODE>_{chno}_T01, …). Do NOT create any other chapter. Write the <name>.structure.json, "
            "generate the .cypher via run_script(\"json_to_cypher.py\", [\"<name>.structure.json\", "
            "\"<name>.cypher\"]). Use ask_user for missing lecture metadata or ambiguous granularity. "
            "When the .cypher is written, call stage_complete with its path."
        )
    return (
        f"Stage 1 — domain model, ADDING CHAPTER {chapter_no}. The lecture already exists; its current "
        "domain model (all previously added chapters) is in `domain.cypher` in your workspace — read it "
        "with read_file. Do NOT recreate or modify existing chapters.\n\n"
        "Find the new chapter's material:\n"
        "- If the user just uploaded a NEW single-chapter PDF, use it (list_dir to find the newest file).\n"
        "- Otherwise continue with the comprehensive PDF: take the chapter that comes AFTER the highest "
        "chapter already present in domain.cypher.\n"
        "Propose the chapter (title + page range) and call ask_user to confirm before building it.\n\n"
        f"Then add EXACTLY this one chapter and number it {chno} (ids start with <CODE>_{chno}). Write the "
        "structure.json for this chapter, run json_to_cypher.py, and call stage_complete with the new "
        f".cypher path. The new chapter must reuse the existing Lecture node and attach via HAS_CHAPTER."
    )


def _edges_kickoff(chapter_no: int) -> str:
    chno = f"CH{chapter_no:02d}"
    return (
        f"Stage 2 — concept edges for CHAPTER {chapter_no} ({chno}) ONLY. The full domain model is in "
        "`domain.cypher` (read_file); the lecture PDF(s) are present. Author the concept edges only for "
        f"this chapter's concepts (ids starting with <CODE>_{chno}). Write one set of edge .cypher files "
        f"named after this chapter: `{chapter_no:02d}-<chapter-slug>_prerequisites.cypher`, "
        f"`{chapter_no:02d}-<chapter-slug>_facilitators.cypher`, and "
        f"`{chapter_no:02d}-<chapter-slug>_same_as.cypher`. Then verify with run_script("
        "\"verify_edges.py\", [\"--domain\", \"domain.cypher\", \"--prereq\", \"*_prerequisites.cypher\", "
        "\"--facilitator\", \"*_facilitators.cypher\", \"--sameas\", \"*_same_as.cypher\"]). Only call "
        "stage_complete once verify_edges.py prints ALL CHECKS PASSED; pass this chapter's edge .cypher "
        "paths as artifacts."
    )


def _questions_kickoff(chapter_no: int) -> str:
    chno = f"CH{chapter_no:02d}"
    return (
        f"Stage 3 — review questions for CHAPTER {chapter_no} ({chno}) ONLY. The domain model is in "
        "`domain.cypher` (read_file). The lecture PDF(s) are present. Extract this chapter's "
        f"Wiederholungsfragen and write the questions .cypher for this chapter only "
        f"(`{chapter_no:02d}-<chapter-slug>_questions.cypher`).\n\n"
        "EXACT Cypher format — EVERY property MUST be prefixed with its node variable, and every "
        "statement ends with `;`. A property name on its own (e.g. `note='...'`) is a SYNTAX ERROR; "
        "it must be `q.note='...'`. Template for one question with two TESTS edges:\n"
        f"CREATE CONSTRAINT IF NOT EXISTS FOR (q:Question) REQUIRE q.id IS UNIQUE;\n"
        f"MERGE (q:Question {{id:'<CODE>_{chno}_Q04'}})\n"
        "  SET q.text='Warum setzt ein INNER JOIN das relationale Modell voraus?',\n"
        f"      q.index=4, q.chapter='<CODE>_{chno}', q.pageNumber=2,\n"
        "      q.source='Vorlesung.pdf', q.note='Cross-chapter exception: ...';\n"
        f"MATCH (c:Chapter {{id:'<CODE>_{chno}'}}), (q:Question {{id:'<CODE>_{chno}_Q04'}}) "
        "MERGE (c)-[:HAS_QUESTION]->(q);\n"
        f"MATCH (q:Question {{id:'<CODE>_{chno}_Q04'}}), (c:Concept {{id:'<CODE>_CH01_T01_C01'}}) "
        "MERGE (q)-[:TESTS]->(c);\n\n"
        "`q.note` is OPTIONAL (only for documented cross-chapter exceptions); if present it MUST be "
        "`q.note='...'`, never a bare `note='...'`. Escape any literal ASCII apostrophe inside string "
        "values with a backslash.\n\n"
        "IMPORTANT: do NOT ask the user to textually review or confirm the TESTS connections — decide "
        "them yourself, write the file, and the user will validate everything visually on the graph "
        "afterwards. Use ask_user ONLY for information you genuinely cannot infer from the slides. Verify "
        "with run_script(\"verify_questions.py\", [\"--domain\", \"domain.cypher\", \"--questions\", "
        "\"*_questions.cypher\"]), then call stage_complete with this chapter's questions .cypher path "
        "once the hard checks pass."
    )


def stage_kickoff(stage: Stage, chapter_no: int, is_first_chapter: bool) -> str:
    if stage is Stage.DOMAIN:
        return _domain_kickoff(chapter_no, is_first_chapter)
    if stage is Stage.EDGES:
        return _edges_kickoff(chapter_no)
    return _questions_kickoff(chapter_no)
