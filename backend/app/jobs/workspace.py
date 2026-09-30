from __future__ import annotations

from pathlib import Path

from fastapi import UploadFile

from app.models.jobs import Job


def ensure_workspace(job: Job) -> Path:
    """
    Create the job's workspace directory if needed.

    :param job: The job.
    :return: The workspace directory.
    """
    job.workspace.mkdir(parents=True, exist_ok=True)
    return job.workspace


def _safe_name(name: str) -> str:
    """
    Strip directory components from an uploaded file name.

    :param name: The file name sent by the client.
    :return: The bare file name.
    """
    return Path(name).name


async def save_uploads(job: Job, files: list[UploadFile]) -> list[str]:
    """
    Store uploaded PDFs in the job workspace and record them on the job.

    :param job: The job.
    :param files: The uploaded files.
    :return: The stored file names.
    """
    ws = ensure_workspace(job)
    saved: list[str] = []
    for f in files:
        name = _safe_name(f.filename or "upload.pdf")
        dest = ws / name
        dest.write_bytes(await f.read())
        saved.append(name)
    job.uploaded_pdfs = sorted(set(job.uploaded_pdfs) | set(saved))
    return saved


def artifact_path(job: Job, rel: str) -> Path:
    """
    Resolve a workspace-relative artifact path and reject paths outside the workspace.

    :param job: The job.
    :param rel: The workspace-relative path.
    :return: The resolved absolute path.
    :raises ValueError: If the path escapes the workspace.
    """
    p = (job.workspace / rel).resolve()
    if job.workspace.resolve() not in p.parents and p != job.workspace.resolve():
        raise ValueError("artifact path escapes workspace")
    return p
