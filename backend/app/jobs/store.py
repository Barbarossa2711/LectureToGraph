"""In-memory job store. Jobs are single-user, local, and disposable; the durable
state is the staged graph in Neo4j and the workspace files on disk."""
from __future__ import annotations

import uuid

from app.models.jobs import Job, JobStatus


class JobStore:
    def __init__(self) -> None:
        self._jobs: dict[str, Job] = {}

    def create(self, provider: str, model: str, lecture_code: str | None,
               language: str = "de") -> Job:
        job = Job(
            id=uuid.uuid4().hex[:12],
            provider=provider,
            model=model,
            lecture_code=lecture_code,
            language=language,
            status=JobStatus.CREATED,
        )
        self._jobs[job.id] = job
        return job

    def get(self, job_id: str) -> Job | None:
        return self._jobs.get(job_id)

    def require(self, job_id: str) -> Job:
        job = self._jobs.get(job_id)
        if job is None:
            raise KeyError(job_id)
        return job


store = JobStore()
