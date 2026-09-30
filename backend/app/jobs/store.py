"""
In-memory job store. Jobs are single-user, local and disposable; the durable
state is the staged graph in Neo4j and the workspace files on disk.
"""
from __future__ import annotations

import uuid

from app.models.jobs import Job, JobStatus


class JobStore:
    """Holds all jobs of the running process by id."""

    def __init__(self) -> None:
        """Create an empty store."""
        self._jobs: dict[str, Job] = {}

    def create(self, provider: str, model: str, lecture_code: str | None,
               language: str = "de") -> Job:
        """
        Create and register a new job.

        :param provider: The LLM provider name.
        :param model: The model id.
        :param lecture_code: The lecture code, or None if not known yet.
        :param language: The language the agent uses with the user, "de" or "en".
        :return: The new job.
        """
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
        """
        Look up a job.

        :param job_id: The job id.
        :return: The job, or None if unknown.
        """
        return self._jobs.get(job_id)

    def require(self, job_id: str) -> Job:
        """
        Look up a job that must exist.

        :param job_id: The job id.
        :return: The job.
        :raises KeyError: If the job is unknown.
        """
        job = self._jobs.get(job_id)
        if job is None:
            raise KeyError(job_id)
        return job


store = JobStore()
