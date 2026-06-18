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

    # chapter currently being processed (the pipeline runs one chapter at a time)
    chapter_no: int = 1

    conversation: list[Message] = Field(default_factory=list)
    pending_question: dict | None = None
    resume_tool_use_id: str | None = None
    # tool results already computed for other tools in the same batch as a pending ask_user
    pending_results: list[ToolResultBlock] = Field(default_factory=list)

    # stage value -> list of workspace-relative artifact paths (accumulated across chapters)
    artifacts: dict[str, list[str]] = Field(default_factory=dict)
    # artifacts produced by the most recent stage_complete (what to load now)
    last_artifacts: list[str] = Field(default_factory=list)
    # the stage whose changes are currently the "latest" (for the scoped graph view)
    last_loaded_stage: Stage | None = None
    error: str | None = None
    uploaded_pdfs: list[str] = Field(default_factory=list)

    @property
    def workspace(self) -> Path:
        return settings.workspace_dir / self.id

    def next_stage(self) -> Stage | None:
        i = STAGE_ORDER.index(self.stage)
        return STAGE_ORDER[i + 1] if i + 1 < len(STAGE_ORDER) else None


class JobSummary(BaseModel):
    """The client-facing view (omits the full conversation)."""
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
        return cls(
            id=job.id, provider=job.provider, model=job.model,
            lecture_code=job.lecture_code, language=job.language,
            stage=job.stage, status=job.status,
            chapter_no=job.chapter_no, last_loaded_stage=job.last_loaded_stage,
            pending_question=job.pending_question, artifacts=job.artifacts,
            error=job.error, uploaded_pdfs=job.uploaded_pdfs,
        )
