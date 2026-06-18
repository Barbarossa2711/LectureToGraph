from __future__ import annotations

from pathlib import Path

from fastapi import UploadFile

from app.models.jobs import Job


def ensure_workspace(job: Job) -> Path:
    job.workspace.mkdir(parents=True, exist_ok=True)
    return job.workspace


def _safe_name(name: str) -> str:
    return Path(name).name  # strip any directory components


async def save_uploads(job: Job, files: list[UploadFile]) -> list[str]:
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
    p = (job.workspace / rel).resolve()
    if job.workspace.resolve() not in p.parents and p != job.workspace.resolve():
        raise ValueError("artifact path escapes workspace")
    return p
