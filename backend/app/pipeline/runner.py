"""
Pipeline orchestration: drives a job through the three stages of one chapter at a
time, pauses at ask_user and at validation gates and loads each stage's Cypher into
Neo4j. Once a chapter's questions are approved, the job offers another chapter.
"""
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
    """
    Set the job status and publish it.

    :param job: The job.
    :param status: The new status.
    :return: None
    """
    job.status = status
    await bus.publish(job.id, "status", {"status": status.value, "stage": job.stage.value})


async def _fail(job: Job, e: Exception) -> None:
    """
    Record an error on the job, publish it and mark the job as failed.

    :param job: The job.
    :param e: The exception that ended the stage.
    :return: None
    """
    job.error = f"{type(e).__name__}: {e}"
    await bus.publish(job.id, "error", {"message": job.error})
    await _set_status(job, JobStatus.FAILED)


async def _seed_stage(job: Job) -> None:
    """
    Prepare the workspace and start a new conversation for the current stage and chapter.

    If the lecture exists, its current domain model is written to domain.cypher so
    later chapters and stages see the existing nodes. The domain stage additionally
    gets slides.cypher, so it reuses slides of earlier chapters instead of duplicating them.

    :param job: The job.
    :return: None
    """
    ensure_workspace(job)
    if job.lecture_code:
        domain = await cl.export_domain_cypher(job.lecture_code)
        (job.workspace / "domain.cypher").write_text(domain, encoding="utf-8")
        if job.stage is Stage.DOMAIN:
            slides = await cl.export_slides_cypher(job.lecture_code)
            (job.workspace / "slides.cypher").write_text(slides, encoding="utf-8")
    is_first = job.chapter_no == 1
    kickoff = stage_kickoff(job.stage, job.chapter_no, is_first)
    job.conversation = [Message(role="user", content=[TextBlock(text=kickoff)])]


async def run_stage(job: Job) -> None:
    """
    Run the current stage until it asks a question, awaits validation or fails.

    :param job: The job.
    :return: None
    """
    try:
        await _set_status(job, JobStatus.RUNNING)
        provider = get_provider(job.provider)
        system = stage_system_prompt(
            job.stage, max_pages=settings.pdf_max_pages_per_batch, language=job.language)
        await _drive(job, provider, system)
    except Exception as e:  # noqa: BLE001
        await _fail(job, e)


async def resume(job: Job, answers: dict) -> None:
    """
    Continue a paused stage with the user's answers.

    :param job: The job waiting for input.
    :param answers: The answers to the pending question.
    :return: None
    """
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
    """
    Run the agent loop and set the job status from its outcome.

    When the stage completes, its Cypher artifacts are loaded into Neo4j.

    :param job: The job.
    :param provider: The LLM provider.
    :param system: The system prompt of the stage.
    :return: None
    """
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
    else:
        await _set_status(job, JobStatus.FAILED)


async def _load_stage_artifacts(job: Job) -> None:
    """
    Load the Cypher files of the completed stage into Neo4j.

    The lecture code is taken from the first domain model. After the domain stage,
    slides without a COVERS edge (table of contents, agenda, ...) are deleted.

    :param job: The job.
    :return: None
    """
    for rel in job.last_artifacts:
        if not rel.lower().endswith(".cypher"):
            continue
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
    if job.stage is Stage.DOMAIN and job.lecture_code:
        removed = await cl.delete_orphan_slides_in_chapter(job.lecture_code, job.chapter_no)
        if removed:
            await bus.publish(job.id, "log", {
                "text": f"{removed} inhaltslose Folie(n) ohne Konzept entfernt."})


async def _consolidate_chapter(job: Job) -> None:
    """
    Write one consolidated <CODE>_CHNN.cypher for the finished chapter.

    The download list is reduced to these files, so one .cypher per chapter is offered.

    :param job: The job.
    :return: None
    """
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
    """
    Continue after the user approved a stage.

    After the last stage the chapter is consolidated and the job waits for the next chapter.

    :param job: The job.
    :return: None
    """
    try:
        nxt = job.next_stage()
        if nxt is None:
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
    """
    Start the next chapter with the domain stage; existing chapters are kept.

    :param job: The job.
    :return: None
    """
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
    """
    Mark the job as completed.

    :param job: The job.
    :return: None
    """
    await _set_status(job, JobStatus.COMPLETED)


async def rerun_stage(job: Job, feedback: str | None) -> None:
    """
    Regenerate the current stage; errors mark the job as failed.

    :param job: The job.
    :param feedback: Optional user feedback for the new attempt.
    :return: None
    """
    try:
        await _rerun_stage(job, feedback)
    except Exception as e:  # noqa: BLE001
        await _fail(job, e)


async def _rerun_stage(job: Job, feedback: str | None) -> None:
    """
    Delete what the current stage created in this chapter and run the stage again.

    :param job: The job.
    :param feedback: Optional user feedback, appended to the kickoff message.
    :return: None
    """
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
    """
    Start the pipeline with the domain stage of the first chapter.

    :param job: The job.
    :return: None
    """
    try:
        job.stage = Stage.DOMAIN
        job.chapter_no = 1
        await _seed_stage(job)
    except Exception as e:  # noqa: BLE001
        await _fail(job, e)
        return
    await run_stage(job)
