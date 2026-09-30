from __future__ import annotations

from app.skills.registry import Stage

# Relationship types a stage creates, deleted before the stage is re-run.
STAGE_EDGE_TYPES: dict[Stage, list[str]] = {
    Stage.EDGES: ["PREREQUISITE", "FACILITATOR", "SAME_AS"],
}


def questions_raw_name(chapter_no: int) -> str:
    """
    Name the file for the review questions captured verbatim in the domain stage.

    The questions stage reads this file instead of reading the PDF again.

    :param chapter_no: The chapter number.
    :return: The workspace-relative file name.
    """
    return f"questions_raw_ch{chapter_no:02d}.json"


def _questions_capture_block(chapter_no: int) -> str:
    """
    Build the prompt part asking the domain stage to capture the review questions verbatim.

    :param chapter_no: The chapter number.
    :return: The prompt text.
    """
    fname = questions_raw_name(chapter_no)
    return (
        "\n\nALSO, while you already have the deck open (so it need NOT be read again later), extract "
        f"this chapter's review questions (Wiederholungsfragen / Kontrollfragen / Quiz / Repetition) "
        f"VERBATIM and save them to `{fname}` (write_file) as a JSON list of objects: "
        '`[{"index": 1, "text": "<exact question text>", "pageNr": 12}, ...]`. '
        "Keep the wording exact (fix only obvious OCR splits/typos). Do NOT map them to concepts and do "
        "NOT write any Cypher for them here — the concept mapping is stage 3. If the chapter has no "
        f"review questions, write an empty list `[]` to `{fname}`. (This file is an intermediate, not a "
        "stage_complete artifact.)"
    )


def _slides_block(chapter_no: int) -> str:
    """
    Build the prompt part asking the domain stage to create Slide nodes with COVERS edges.

    :param chapter_no: The chapter number.
    :return: The prompt text.
    """
    chno = f"CH{chapter_no:02d}"
    return (
        f"\n\nTHEN, in this same step, add the SLIDES for chapter {chapter_no}. Turn this chapter's "
        "slide deck into `:Slide` nodes — one node per slide/page — and link each slide to the "
        "Concept(s) it presents via a COVERS edge (see the 'Step 3 — Slides' section of the skill).\n"
        "- If `slides.cypher` exists in your workspace, read_file it first: it lists the `:Slide` nodes "
        "already created for earlier chapters. One physical page = exactly ONE `:Slide` node; do NOT "
        f"recreate a page already listed there, and only create slides for chapter {chapter_no}'s pages.\n"
        f"- Each `:Slide` needs all eight properties; the id is `<CODE>_{chno}_SL<pageNr>`. EVERY "
        "property MUST be `s.`-prefixed.\n"
        f"- HARD REQUIREMENT: every Concept of this chapter (ids starting with <CODE>_{chno}) MUST be "
        "the target of at least one COVERS edge — no concept may be left without a source slide.\n"
        "- Do NOT create `:Slide` nodes for content-less slides: table of contents, agenda, section "
        "dividers, pure recap/Wiederholungsfragen, or image-only slides. Only create a `:Slide` if it "
        "presents at least one concept (i.e. it will have ≥ 1 COVERS edge). Any free-standing Slide "
        "without a COVERS edge is removed automatically, so don't bother creating it.\n"
        f"- Write the slides into a separate file `<name>_slides.cypher`, then verify with run_script("
        "\"verify_slides.py\", [\"--domain\", \"<name>.cypher\", \"--slides\", \"<name>_slides.cypher\"]).\n"
        "Only call stage_complete once verify_slides.py prints HARD CHECKS PASSED. Pass BOTH artifacts in "
        "order — the structural `<name>.cypher` FIRST, then `<name>_slides.cypher` (the structure must "
        "load before the COVERS edges can attach)."
    )


def _domain_kickoff(chapter_no: int, is_first: bool) -> str:
    """
    Build the kickoff message of the domain stage.

    :param chapter_no: The chapter number.
    :param is_first: True for the first chapter, which also creates the lecture.
    :return: The prompt text.
    """
    chno = f"CH{chapter_no:02d}"
    if is_first:
        return (
            f"Stage 1 — domain model + slides, CHAPTER {chapter_no} only. The uploaded lecture PDF(s) are "
            "already in your workspace; call list_dir(\".\") to see them and read them with read_pdf.\n\n"
            "First decide what kind of document you have:\n"
            "- If a PDF covers the WHOLE lecture (multiple chapters), read its table of contents / "
            "structure, list the chapters you detect WITH their page ranges, and call ask_user to let "
            "the user CONFIRM or correct that chapter breakdown. Then build ONLY the first chapter.\n"
            "- If a PDF is a SINGLE chapter, just process it as the first chapter.\n\n"
            f"Process EXACTLY ONE chapter now and number it {chno} (ids like <CODE>_{chno}, "
            f"<CODE>_{chno}_T01, …). Do NOT create any other chapter. Write the <name>.structure.json, "
            "generate the structural .cypher via run_script(\"json_to_cypher.py\", "
            "[\"<name>.structure.json\", \"<name>.cypher\"]). Use ask_user for missing lecture metadata "
            "or ambiguous granularity."
            + _questions_capture_block(chapter_no)
            + _slides_block(chapter_no)
        )
    return (
        f"Stage 1 — domain model + slides, ADDING CHAPTER {chapter_no}. The lecture already exists; its "
        "current domain model (all previously added chapters) is in `domain.cypher` in your workspace — "
        "read it with read_file. Do NOT recreate or modify existing chapters.\n\n"
        "Find the new chapter's material:\n"
        "- If the user just uploaded a NEW single-chapter PDF, use it (list_dir to find the newest file).\n"
        "- Otherwise continue with the comprehensive PDF: take the chapter that comes AFTER the highest "
        "chapter already present in domain.cypher.\n"
        "Propose the chapter (title + page range) and call ask_user to confirm before building it.\n\n"
        f"Then add EXACTLY this one chapter and number it {chno} (ids start with <CODE>_{chno}). Write the "
        "structure.json for this chapter and run json_to_cypher.py to produce its `<name>.cypher`. The new "
        "chapter must reuse the existing Lecture node and attach via HAS_CHAPTER."
        + _questions_capture_block(chapter_no)
        + _slides_block(chapter_no)
    )


def _edges_kickoff(chapter_no: int) -> str:
    """
    Build the kickoff message of the concept edge stage.

    :param chapter_no: The chapter number.
    :return: The prompt text.
    """
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
    """
    Build the kickoff message of the review question stage.

    :param chapter_no: The chapter number.
    :return: The prompt text.
    """
    chno = f"CH{chapter_no:02d}"
    raw = questions_raw_name(chapter_no)
    return (
        f"Stage 3 — review questions for CHAPTER {chapter_no} ({chno}) ONLY. The domain model is in "
        "`domain.cypher` (read_file).\n\n"
        f"The verbatim questions were ALREADY extracted during step 1 into `{raw}`. read_file it and use "
        "it as your question source — do NOT read the PDF again unless that file is missing or clearly "
        f"incomplete. If `{raw}` is an empty list `[]`, this chapter has no review questions: call "
        "stage_complete immediately with an empty artifact list and do nothing else.\n\n"
        "Your job here is the concept MAPPING: for each question from the file, find the fitting "
        f"Concept(s) and write the questions .cypher for this chapter only "
        f"(`{chapter_no:02d}-<chapter-slug>_questions.cypher`). Use each question's `text`, `index` and "
        "`pageNr` from the file verbatim.\n\n"
        "EXACT Cypher format — EVERY property MUST be prefixed with its node variable, and every "
        "statement ends with `;`. A property name on its own (e.g. `note='...'`) is a SYNTAX ERROR; "
        "it must be `q.note='...'`. Template for one question with two TESTS edges:\n"
        f"CREATE CONSTRAINT IF NOT EXISTS FOR (q:Question) REQUIRE q.id IS UNIQUE;\n"
        f"MERGE (q:Question {{id:'<CODE>_{chno}_Q04'}})\n"
        "  SET q.text='Warum setzt ein INNER JOIN das relationale Modell voraus?',\n"
        f"      q.index=4, q.chapter='<CODE>_{chno}', q.pageNr=2,\n"
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
    """
    Build the first user message of a stage.

    :param stage: The stage.
    :param chapter_no: The chapter number.
    :param is_first_chapter: True for the first chapter of the job.
    :return: The prompt text.
    """
    if stage is Stage.DOMAIN:
        return _domain_kickoff(chapter_no, is_first_chapter)
    if stage is Stage.EDGES:
        return _edges_kickoff(chapter_no)
    return _questions_kickoff(chapter_no)
