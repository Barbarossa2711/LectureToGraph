from __future__ import annotations

import asyncio
import json

from fastapi import APIRouter, HTTPException, UploadFile, File
from fastapi.responses import FileResponse, Response
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

from app.config import settings
from app.jobs.events import bus
from app.jobs.store import store
from app.jobs.workspace import save_uploads, artifact_path
from app.models.jobs import JobSummary, JobStatus
from app.pipeline import runner
from app.pipeline.cypher_loader import (
    export_full_graph_cypher, upload_to_external, load_cypher_text, last_change_cypher,
)
from app.jobs.workspace import ensure_workspace

router = APIRouter(prefix="/jobs", tags=["jobs"])

# Strong references keep background tasks from being garbage-collected mid-run.
_tasks: set[asyncio.Task] = set()


def _schedule(coro) -> None:
    """
    Run a coroutine as background task.

    :param coro: The coroutine to run.
    :return: None
    """
    task = asyncio.create_task(coro)
    _tasks.add(task)
    task.add_done_callback(_tasks.discard)


class CreateJobBody(BaseModel):
    provider: str
    model: str
    lecture_code: str | None = None
    language: str = "de"


class AnswerBody(BaseModel):
    answers: dict


class RerunBody(BaseModel):
    feedback: str | None = None


class LanguageBody(BaseModel):
    language: str


class Neo4jUploadBody(BaseModel):
    uri: str
    user: str
    password: str
    database: str | None = None


def _require(job_id: str):
    """
    Look up a job for a request.

    :param job_id: The job id.
    :return: The job.
    :raises HTTPException: 404 if the job is unknown.
    """
    job = store.get(job_id)
    if job is None:
        raise HTTPException(404, "Job not found")
    return job


@router.post("")
async def create_job(body: CreateJobBody):
    """
    Create a job.

    :param body: Provider, model, optional lecture code and language.
    :return: The job summary.
    """
    job = store.create(body.provider, body.model, body.lecture_code, body.language)
    return JobSummary.of(job)


@router.post("/{job_id}/language")
async def set_language(job_id: str, body: LanguageBody):
    """
    Change the language the agent uses with the user.

    :param job_id: The job id.
    :param body: The language, "de" or "en".
    :return: The job summary.
    :raises HTTPException: 400 for any other language.
    """
    job = _require(job_id)
    if body.language not in ("de", "en"):
        raise HTTPException(400, "language must be 'de' or 'en'")
    job.language = body.language
    return JobSummary.of(job)


@router.post("/{job_id}/pdfs")
async def upload_pdfs(job_id: str, files: list[UploadFile] = File(...)):
    """
    Store lecture PDFs in the job workspace.

    :param job_id: The job id.
    :param files: The uploaded PDFs.
    :return: The stored file names.
    """
    job = _require(job_id)
    saved = await save_uploads(job, files)
    # Only the first upload advances the status. A later upload for another
    # chapter must not overwrite AWAITING_NEXT_CHAPTER or RUNNING.
    if job.status is JobStatus.CREATED:
        job.status = JobStatus.UPLOADED
    return {"saved": saved}


@router.post("/{job_id}/start")
async def start_job(job_id: str):
    """
    Start the pipeline with the first chapter in the background.

    :param job_id: The job id.
    :return: The job summary.
    :raises HTTPException: 400 if no PDF was uploaded.
    """
    job = _require(job_id)
    if not job.uploaded_pdfs:
        raise HTTPException(400, "Upload at least one PDF first")
    _schedule(runner.start(job))
    return JobSummary.of(job)


@router.get("/{job_id}")
async def get_job(job_id: str):
    """
    Return the current state of a job.

    :param job_id: The job id.
    :return: The job summary.
    """
    return JobSummary.of(_require(job_id))


@router.get("/{job_id}/events")
async def events(job_id: str):
    """
    Stream the job's events as server-sent events.

    The stream starts with the current status and a pending question, if any,
    so a reconnecting client can restore its state.

    :param job_id: The job id.
    :return: The event stream.
    """
    _require(job_id)

    async def gen():
        """
        Yield the initial state, then every published event of the job.

        :return: An async generator of SSE events.
        """
        job = store.get(job_id)
        yield {"event": "status", "data": json.dumps(
            {"status": job.status.value, "stage": job.stage.value})}
        if job.pending_question:
            yield {"event": "question", "data": json.dumps(job.pending_question)}
        async for ev in bus.subscribe(job_id):
            yield {"event": ev["type"], "data": json.dumps(ev["data"])}

    return EventSourceResponse(gen())


@router.post("/{job_id}/answer")
async def answer(job_id: str, body: AnswerBody):
    """
    Answer the agent's pending question and resume the stage in the background.

    :param job_id: The job id.
    :param body: The answers.
    :return: The job summary.
    :raises HTTPException: 409 if the job is not waiting for input.
    """
    job = _require(job_id)
    if job.status is not JobStatus.AWAITING_USER_INPUT:
        raise HTTPException(409, "Job is not awaiting input")
    _schedule(runner.resume(job, body.answers))
    return JobSummary.of(job)


@router.post("/{job_id}/gate/approve")
async def approve(job_id: str):
    """
    Approve the current stage's result and continue in the background.

    :param job_id: The job id.
    :return: The job summary.
    :raises HTTPException: 409 if the job is not waiting for validation.
    """
    job = _require(job_id)
    if job.status is not JobStatus.AWAITING_VALIDATION:
        raise HTTPException(409, "Job is not awaiting validation")
    _schedule(runner.approve_gate(job))
    return JobSummary.of(job)


@router.post("/{job_id}/add-chapter")
async def add_chapter(job_id: str):
    """
    Start processing the next chapter in the background.

    :param job_id: The job id.
    :return: The job summary.
    :raises HTTPException: 409 if the job is not waiting for the next chapter.
    """
    job = _require(job_id)
    if job.status is not JobStatus.AWAITING_NEXT_CHAPTER:
        raise HTTPException(409, "Job is not awaiting the next chapter")
    _schedule(runner.add_chapter(job))
    return JobSummary.of(job)


@router.post("/{job_id}/finish")
async def finish(job_id: str):
    """
    Mark the job as completed instead of adding another chapter.

    :param job_id: The job id.
    :return: The job summary.
    :raises HTTPException: 409 if the job is not waiting for the next chapter.
    """
    job = _require(job_id)
    if job.status is not JobStatus.AWAITING_NEXT_CHAPTER:
        raise HTTPException(409, "Job is not awaiting the next chapter")
    _schedule(runner.finish(job))
    return JobSummary.of(job)


@router.post("/{job_id}/stage/rerun")
async def rerun(job_id: str, body: RerunBody):
    """
    Discard the current stage's result and regenerate it in the background.

    :param job_id: The job id.
    :param body: Optional feedback for the new attempt.
    :return: The job summary.
    """
    job = _require(job_id)
    _schedule(runner.rerun_stage(job, body.feedback))
    return JobSummary.of(job)


@router.get("/{job_id}/artifact")
async def download_artifact(job_id: str, path: str):
    """
    Download a file from the job workspace.

    :param job_id: The job id.
    :param path: The workspace-relative path.
    :return: The file.
    :raises HTTPException: 404 if the file does not exist.
    """
    job = _require(job_id)
    p = artifact_path(job, path)
    if not p.exists():
        raise HTTPException(404, "Artifact not found")
    return FileResponse(str(p), filename=p.name)


@router.get("/{job_id}/full-cypher")
async def full_cypher(job_id: str):
    """
    Download the lecture's current graph, including manual edits, as one Cypher file.

    :param job_id: The job id.
    :return: The Cypher file as attachment.
    :raises HTTPException: 400 if no graph has been staged yet.
    """
    job = _require(job_id)
    if not job.lecture_code:
        raise HTTPException(400, "No staged graph yet")
    text = await export_full_graph_cypher(job.lecture_code)
    return Response(
        content=text,
        media_type="application/octet-stream",
        headers={"Content-Disposition": f"attachment; filename={job.lecture_code}_full.cypher"},
    )


@router.post("/{job_id}/save-cypher")
async def save_cypher(job_id: str):
    """
    Save the current graph, including manual edits, as .cypher file in the job workspace.

    The file is registered as downloadable artifact.

    :param job_id: The job id.
    :return: The job summary.
    :raises HTTPException: 400 if no graph has been staged yet.
    """
    job = _require(job_id)
    if not job.lecture_code:
        raise HTTPException(400, "No staged graph yet")
    text = await export_full_graph_cypher(job.lecture_code)
    ensure_workspace(job)
    rel = f"{job.lecture_code}_full.cypher"
    (job.workspace / rel).write_text(text, encoding="utf-8")
    saved = job.artifacts.setdefault("SAVED", [])
    if rel not in saved:
        saved.append(rel)
    return JobSummary.of(job)


def _browser_http_url() -> str:
    """
    Derive the Neo4j Browser URL (port 7474) from the bolt URI handed to the browser.

    :return: The HTTP URL of the Neo4j Browser.
    """
    uri = settings.neo4j_browser_uri
    host = uri.split("://", 1)[-1].split(":", 1)[0] or "localhost"
    return f"http://{host}:7474"


@router.get("/{job_id}/bundled-access")
async def bundled_access(job_id: str):
    """
    Describe how to reach the bundled Neo4j from the host.

    :param job_id: The job id.
    :return: Browser URL, bolt URI, user and password.
    """
    _require(job_id)
    return {
        "browser_http": _browser_http_url(),
        "bolt_uri": settings.neo4j_browser_uri,
        "user": settings.neo4j_browser_user,
        "password": settings.neo4j_browser_password,
    }


@router.post("/{job_id}/load-bundled")
async def load_bundled(job_id: str):
    """
    Load the current graph, including manual edits, into the bundled Neo4j again.

    The staged graph already lives there; this is idempotent and guarantees the
    database matches the exported Cypher, e.g. after a reset.

    :param job_id: The job id.
    :return: The load statistics and the Neo4j Browser URL.
    :raises HTTPException: 400 if no graph has been staged yet.
    """
    job = _require(job_id)
    if not job.lecture_code:
        raise HTTPException(400, "No staged graph yet")
    text = await export_full_graph_cypher(job.lecture_code)
    result = await load_cypher_text(text)
    return {"ok": True, **result, "browser_http": _browser_http_url()}


@router.post("/{job_id}/upload-neo4j")
async def upload_neo4j(job_id: str, body: Neo4jUploadBody):
    """
    Upload the current graph, including manual edits, into an external Neo4j.

    :param job_id: The job id.
    :param body: Bolt URI, credentials and optional database name.
    :return: The upload statistics.
    :raises HTTPException: 400 if no graph is staged or the upload fails.
    """
    job = _require(job_id)
    if not job.lecture_code:
        raise HTTPException(400, "No staged graph yet")
    text = await export_full_graph_cypher(job.lecture_code)
    try:
        result = await upload_to_external(
            body.uri, body.user, body.password, text, body.database or None)
    except Exception as e:  # noqa: BLE001
        raise HTTPException(400, f"{type(e).__name__}: {e}")
    return {"ok": True, **result}


@router.get("/{job_id}/viz-config")
async def viz_config(job_id: str):
    """
    Return the neovis.js configuration for the job's graph view.

    :param job_id: The job id.
    :return: Connection data, the query for the whole lecture and the query for the latest changes.
    """
    job = _require(job_id)
    code = job.lecture_code or "__none__"
    initial_cypher = (
        f"MATCH (n) WHERE n.id STARTS WITH '{code}' "
        f"OPTIONAL MATCH (n)-[r]->(m) WHERE m.id STARTS WITH '{code}' "
        "RETURN n, r, m"
    )
    last_cypher = None
    if job.lecture_code and job.last_loaded_stage is not None:
        last_cypher = last_change_cypher(
            job.lecture_code, job.last_loaded_stage.value, job.chapter_no)
    return {
        "serverUrl": settings.neo4j_browser_uri,
        "serverUser": settings.neo4j_browser_user,
        "serverPassword": settings.neo4j_browser_password,
        "initialCypher": initial_cypher,
        "lastChangeCypher": last_cypher,
        "lastChangeStage": job.last_loaded_stage.value if job.last_loaded_stage else None,
        "lectureCode": job.lecture_code,
    }
