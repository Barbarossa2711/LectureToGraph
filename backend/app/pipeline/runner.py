"""Pipeline orchestration: drive a job across the three stages of ONE chapter at
a time, pausing at ask_user and validation gates, loading each stage's cypher into
Neo4j. After a chapter's questions are approved the job offers another chapter."""
from __future__ import annotations

import re

from app.config import settings
from app.ai.loop import run_until_pause, build_answer_message, StageOutcome
from app.ai.registry import get_provider
from app.jobs.events import bus
from app.jobs.workspace import ensure_workspace, artifact_path
from app.models.ai import Message, TextBlock
from app.models.jobs import Job, JobStatus
from app.pipeline import cypher_loader as cl
from app.pipeline.stages import stage_kickoff, STAGE_EDGE_TYPES
from app.skills.registry import Stage, stage_system_prompt

_LECTURE_RE = re.compile(r"MERGE \(n:Lecture \{id:'([^']+)'\}\)")


async def _set_status(job: Job, status: JobStatus) -> None:
    job.status = status
    await bus.publish(job.id, "status", {"status": status.value, "stage": job.stage.value})


async def _fail(job: Job, e: Exception) -> None:
    job.error = f"{type(e).__name__}: {e}"
    await bus.publish(job.id, "error", {"message": job.error})
    await _set_status(job, JobStatus.FAILED)


async def _seed_stage(job: Job) -> None:
    """Prepare workspace + the kickoff message for the current stage/chapter."""
    ensure_workspace(job)
    # whenever a lecture already exists, expose its current domain to the agent
    # (so additional chapters and the edge/question stages see existing nodes)
    if job.lecture_code:
        domain = await cl.export_domain_cypher(job.lecture_code)
        (job.workspace / "domain.cypher").write_text(domain, encoding="utf-8")
        # the domain stage now also creates slides; expose the slides that already
        # exist (from earlier chapters) so it reuses their ids instead of duplicating
        if job.stage is Stage.DOMAIN:
            slides = await cl.export_slides_cypher(job.lecture_code)
            (job.workspace / "slides.cypher").write_text(slides, encoding="utf-8")
    is_first = job.chapter_no == 1
    kickoff = stage_kickoff(job.stage, job.chapter_no, is_first)
    job.conversation = [Message(role="user", content=[TextBlock(text=kickoff)])]


async def run_stage(job: Job) -> None:
    """Run the current stage to its next pause (question / validation / failure)."""
    try:
        await _set_status(job, JobStatus.RUNNING)
        provider = get_provider(job.provider)
        system = stage_system_prompt(
            job.stage, max_pages=settings.pdf_max_pages_per_batch, language=job.language)
        await _drive(job, provider, system)
    except Exception as e:  # noqa: BLE001
        await _fail(job, e)


async def resume(job: Job, answers: dict) -> None:
    try:
        job.conversation.append(build_answer_message(job, answers))
        await _set_status(job, JobStatus.RUNNING)
        provider = get_provider(job.provider)
        system = stage_system_prompt(
            job.stage, max_pages=settings.pdf_max_pages_per_batch, language=job.language)
        await _drive(job, provider, system)
    except Exception as e:  # noqa: BLE001
        await _fail(job, e)


async def _drive(job: Job, provider, system: str) -> None:
    emit = bus.emitter(job.id)
    outcome = await run_until_pause(job, provider, system, emit)

    if outcome is StageOutcome.PAUSED_QUESTION:
        await _set_status(job, JobStatus.AWAITING_USER_INPUT)
    elif outcome is StageOutcome.AWAIT_VALIDATION:
        try:
            await _load_stage_artifacts(job)
        except Exception as e:  # noqa: BLE001
            job.error = f"Loading cypher failed: {e}"
            await bus.publish(job.id, "error", {"message": job.error})
            await _set_status(job, JobStatus.FAILED)
            return
        await _set_status(job, JobStatus.AWAITING_VALIDATION)
    else:  # FAILED / MAX_TURNS
        await _set_status(job, JobStatus.FAILED)


async def _load_stage_artifacts(job: Job) -> None:
    for rel in job.last_artifacts:
        if not rel.lower().endswith(".cypher"):
            continue  # ignore intermediate artifacts like the structure.json
        p = artifact_path(job, rel)
        if not p.exists():
            continue
        text = p.read_text(encoding="utf-8")
        if job.stage is Stage.DOMAIN and job.lecture_code is None:
            m = _LECTURE_RE.search(text)
            if m:
                job.lecture_code = m.group(1)
        await cl.load_cypher_text(text)
    job.last_loaded_stage = job.stage
    # the domain stage also creates slides — drop content-less ones (no COVERS edge),
    # e.g. table-of-contents / agenda slides, so no free-standing Slide nodes remain
    if job.stage is Stage.DOMAIN and job.lecture_code:
        removed = await cl.delete_orphan_slides_in_chapter(job.lecture_code, job.chapter_no)
        if removed:
            await bus.publish(job.id, "log", {
                "text": f"{removed} inhaltslose Folie(n) ohne Konzept entfernt."})


async def _consolidate_chapter(job: Job) -> None:
    """Write the single consolidated `<CODE>_CHNN.cypher` for the finished chapter
    and collapse the download list so only ONE .cypher per chapter is offered."""
    code = job.lecture_code
    if not code:
        return
    text = await cl.export_chapter_cypher(code, job.chapter_no)
    name = f"{code}_CH{job.chapter_no:02d}.cypher"
    ensure_workspace(job)
    (job.workspace / name).write_text(text, encoding="utf-8")
    consolidated = job.artifacts.get("KAPITEL", [])
    if name not in consolidated:
        consolidated = consolidated + [name]
    job.artifacts = {"KAPITEL": consolidated}


async def approve_gate(job: Job) -> None:
    try:
        nxt = job.next_stage()
        if nxt is None:
            # finished this chapter -> consolidate to one file, then offer another chapter
            await _consolidate_chapter(job)
            await _set_status(job, JobStatus.AWAITING_NEXT_CHAPTER)
            return
        job.stage = nxt
        await _seed_stage(job)
    except Exception as e:  # noqa: BLE001
        await _fail(job, e)
        return
    await run_stage(job)


async def add_chapter(job: Job) -> None:
    """Start the next chapter: re-enter the DOMAIN stage additively."""
    try:
        job.chapter_no += 1
        job.stage = Stage.DOMAIN
        job.last_loaded_stage = None
        await _seed_stage(job)
    except Exception as e:  # noqa: BLE001
        await _fail(job, e)
        return
    await run_stage(job)


async def finish(job: Job) -> None:
    await _set_status(job, JobStatus.COMPLETED)


async def rerun_stage(job: Job, feedback: str | None) -> None:
    try:
        await _rerun_stage(job, feedback)
    except Exception as e:  # noqa: BLE001
        await _fail(job, e)


async def _rerun_stage(job: Job, feedback: str | None) -> None:
    code = job.lecture_code
    if code:
        if job.stage is Stage.DOMAIN:
            if job.chapter_no == 1:
                await cl.delete_scope(code)
                job.lecture_code = None
            else:
                await cl.delete_chapter(code, job.chapter_no)
        elif job.stage is Stage.EDGES:
            await cl.delete_edge_types_in_chapter(code, job.chapter_no, STAGE_EDGE_TYPES[Stage.EDGES])
        elif job.stage is Stage.QUESTIONS:
            await cl.delete_questions_in_chapter(code, job.chapter_no)
    await _seed_stage(job)
    if feedback:
        job.conversation.append(Message(role="user", content=[TextBlock(
            text=f"User feedback on the previous attempt: {feedback}"
        )]))
    await run_stage(job)


async def start(job: Job) -> None:
    try:
        job.stage = Stage.DOMAIN
        job.chapter_no = 1
        await _seed_stage(job)
    except Exception as e:  # noqa: BLE001
        await _fail(job, e)
        return
    await run_stage(job)
