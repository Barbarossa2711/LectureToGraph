from __future__ import annotations

from enum import Enum
from pathlib import Path

from pydantic import BaseModel, Field

from app.config import settings
from app.models.ai import Message, ToolResultBlock
from app.skills.registry import Stage

STAGE_ORDER = [Stage.DOMAIN, Stage.EDGES, Stage.QUESTIONS]


class JobStatus(str, Enum):
    CREATED = "CREATED"
    UPLOADED = "UPLOADED"
    RUNNING = "RUNNING"
    AWAITING_USER_INPUT = "AWAITING_USER_INPUT"
    AWAITING_VALIDATION = "AWAITING_VALIDATION"
    AWAITING_NEXT_CHAPTER = "AWAITING_NEXT_CHAPTER"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class Job(BaseModel):
    id: str
    provider: str
    model: str
    lecture_code: str | None = None
    language: str = "de"   # language the agent uses with the user ("de" | "en")

    stage: Stage = Stage.DOMAIN
    status: JobStatus = JobStatus.CREATED

    # The pipeline processes one chapter at a time.
    chapter_no: int = 1

    conversation: list[Message] = Field(default_factory=list)
    pending_question: dict | None = None
    resume_tool_use_id: str | None = None
    # Results of the other tool calls in the same turn as a pending ask_user
    pending_results: list[ToolResultBlock] = Field(default_factory=list)

    # Stage value -> workspace-relative artifact paths, accumulated across chapters
    artifacts: dict[str, list[str]] = Field(default_factory=dict)
    # Artifacts of the most recent stage_complete, i.e. what to load next
    last_artifacts: list[str] = Field(default_factory=list)
    # Stage whose changes the graph view highlights as the latest
    last_loaded_stage: Stage | None = None
    error: str | None = None
    uploaded_pdfs: list[str] = Field(default_factory=list)

    @property
    def workspace(self) -> Path:
        """
        The job's directory for uploads and generated artifacts.

        :return: The workspace path.
        """
        return settings.workspace_dir / self.id

    def next_stage(self) -> Stage | None:
        """
        Determine the stage after the current one.

        :return: The next stage, or None after the last stage.
        """
        i = STAGE_ORDER.index(self.stage)
        return STAGE_ORDER[i + 1] if i + 1 < len(STAGE_ORDER) else None


class JobSummary(BaseModel):
    """The client-facing view of a job, without the conversation."""
    id: str
    provider: str
    model: str
    lecture_code: str | None
    language: str
    stage: Stage
    status: JobStatus
    chapter_no: int
    last_loaded_stage: Stage | None
    pending_question: dict | None
    artifacts: dict[str, list[str]]
    error: str | None
    uploaded_pdfs: list[str]

    @classmethod
    def of(cls, job: Job) -> "JobSummary":
        """
        Build the summary of a job.

        :param job: The job.
        :return: The summary.
        """
        return cls(
            id=job.id, provider=job.provider, model=job.model,
            lecture_code=job.lecture_code, language=job.language,
            stage=job.stage, status=job.status,
            chapter_no=job.chapter_no, last_loaded_stage=job.last_loaded_stage,
            pending_question=job.pending_question, artifacts=job.artifacts,
            error=job.error, uploaded_pdfs=job.uploaded_pdfs,
        )
