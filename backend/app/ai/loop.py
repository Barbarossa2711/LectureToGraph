"""The provider-agnostic agent loop. Runs turns against the current job
conversation until it must pause (ask_user) or hands off (stage_complete)."""
from __future__ import annotations

from enum import Enum
from typing import Awaitable, Callable

from app.config import settings
from app.ai.base import LLMProvider
from app.ai.tools import TOOLS
from app.ai.tool_exec import execute_tool
from app.models.ai import Message, TextBlock, ToolResultBlock
from app.models.jobs import Job

Emit = Callable[[str, dict], Awaitable[None]]


class StageOutcome(str, Enum):
    PAUSED_QUESTION = "PAUSED_QUESTION"
    AWAIT_VALIDATION = "AWAIT_VALIDATION"
    MAX_TURNS = "MAX_TURNS"
    FAILED = "FAILED"


async def run_until_pause(
    job: Job, provider: LLMProvider, system: str, emit: Emit,
) -> StageOutcome:
    idle_nudges = 0

    for _ in range(settings.agent_max_turns):
        try:
            resp = await provider.chat(
                system=system,
                messages=job.conversation,
                tools=TOOLS,
                model=job.model,
                max_tokens=settings.agent_max_tokens,
            )
        except Exception as e:  # noqa: BLE001
            job.error = f"{type(e).__name__}: {e}"
            await emit("error", {"message": job.error})
            return StageOutcome.FAILED

        job.conversation.append(resp.assistant_message)
        text = resp.assistant_message.text_parts()
        if text:
            await emit("log", {"text": text})

        tool_uses = resp.assistant_message.tool_uses()
        if not tool_uses:
            idle_nudges += 1
            if idle_nudges > 3:
                job.error = "Model stopped without calling stage_complete."
                await emit("error", {"message": job.error})
                return StageOutcome.FAILED
            job.conversation.append(Message(role="user", content=[TextBlock(text=(
                "You did not call any tool. If this stage is finished, call "
                "stage_complete with the produced artifact paths. Otherwise continue."
            ))]))
            continue
        idle_nudges = 0

        results: list[ToolResultBlock] = []
        pause_call = None
        completed = False

        for call in tool_uses:
            await emit("tool", {"name": call.name, "input": call.input})
            if call.name == "ask_user":
                pause_call = call
                continue
            if call.name == "stage_complete":
                artifacts = call.input.get("artifacts", []) or []
                job.last_artifacts = list(artifacts)
                # accumulate across chapters for the download list, de-duplicated
                existing = job.artifacts.get(job.stage.value, [])
                job.artifacts[job.stage.value] = existing + [a for a in artifacts if a not in existing]
                results.append(ToolResultBlock(
                    tool_use_id=call.id,
                    content=[TextBlock(text="Acknowledged. Awaiting user validation.")],
                ))
                completed = True
                continue
            results.append(await execute_tool(job, call))

        if pause_call is not None:
            job.pending_results = results
            job.resume_tool_use_id = pause_call.id
            job.pending_question = pause_call.input
            await emit("question", pause_call.input)
            return StageOutcome.PAUSED_QUESTION

        job.conversation.append(Message(role="user", content=results))
        if completed:
            await emit("gate", {"artifacts": job.artifacts.get(job.stage.value, [])})
            return StageOutcome.AWAIT_VALIDATION

    job.error = "Reached max agent turns."
    await emit("error", {"message": job.error})
    return StageOutcome.MAX_TURNS


def build_answer_message(job: Job, answers: dict) -> Message:
    """Combine any deferred batch results with the user's answer into the
    tool_result message that resumes the conversation."""
    import json
    answer_block = ToolResultBlock(
        tool_use_id=job.resume_tool_use_id or "",
        content=[TextBlock(text="User answered:\n" + json.dumps(answers, ensure_ascii=False))],
    )
    content = list(job.pending_results) + [answer_block]
    job.pending_results = []
    job.pending_question = None
    job.resume_tool_use_id = None
    return Message(role="user", content=content)
