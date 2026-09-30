from __future__ import annotations

import asyncio
import sys
from pathlib import Path

from app.models.ai import ToolUseBlock, ToolResultBlock, TextBlock
from app.models.jobs import Job
from app.ai.pdf import read_pdf_blocks
from app.skills.registry import STAGE_SKILLS


def _safe_path(root: Path, rel: str) -> Path:
    """
    Resolve a workspace-relative path and reject paths outside the workspace.

    :param root: The job workspace.
    :param rel: The path given by the model.
    :return: The resolved absolute path.
    :raises ValueError: If the path escapes the workspace.
    """
    p = (root / rel).resolve()
    root = root.resolve()
    if not (p == root or root in p.parents):
        raise ValueError(f"path '{rel}' escapes the job workspace")
    return p


def _ok(call: ToolUseBlock, text: str) -> ToolResultBlock:
    """
    Build a successful text tool result.

    :param call: The tool call being answered.
    :param text: The result text.
    :return: The tool result.
    """
    return ToolResultBlock(tool_use_id=call.id, content=[TextBlock(text=text)])


def _err(call: ToolUseBlock, text: str) -> ToolResultBlock:
    """
    Build a failed text tool result.

    :param call: The tool call being answered.
    :param text: The error message.
    :return: The tool result flagged as error.
    """
    return ToolResultBlock(tool_use_id=call.id, content=[TextBlock(text=text)], is_error=True)


async def execute_tool(job: Job, call: ToolUseBlock) -> ToolResultBlock:
    """
    Execute a workspace tool call. ask_user and stage_complete are handled by the agent loop.

    Any exception is returned to the model as an error result instead of being raised.

    :param job: The job whose workspace the tool works in.
    :param call: The tool call from the model.
    :return: The tool result.
    """
    root = job.workspace
    root.mkdir(parents=True, exist_ok=True)
    args = call.input or {}

    try:
        if call.name == "read_pdf":
            path = _safe_path(root, args["path"])
            if not path.exists():
                return _err(call, f"file not found: {args['path']}")
            blocks = await asyncio.to_thread(read_pdf_blocks, path, args.get("pages"))
            return ToolResultBlock(tool_use_id=call.id, content=blocks)

        if call.name == "read_file":
            path = _safe_path(root, args["path"])
            if not path.exists():
                return _err(call, f"file not found: {args['path']}")
            return _ok(call, path.read_text(encoding="utf-8"))

        if call.name == "write_file":
            path = _safe_path(root, args["path"])
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(args.get("content", ""), encoding="utf-8")
            return _ok(call, f"wrote {args['path']} ({len(args.get('content', ''))} bytes)")

        if call.name == "list_dir":
            path = _safe_path(root, args.get("path", "."))
            if not path.exists():
                return _ok(call, "(empty)")
            names = sorted(p.name + ("/" if p.is_dir() else "") for p in path.iterdir())
            return _ok(call, "\n".join(names) or "(empty)")

        if call.name == "run_script":
            return await _run_script(job, call)

        return _err(call, f"unknown tool '{call.name}'")
    except Exception as e:  # noqa: BLE001 — surface any tool failure back to the model
        return _err(call, f"{type(e).__name__}: {e}")


async def _run_script(job: Job, call: ToolUseBlock) -> ToolResultBlock:
    """
    Run a skill script that is whitelisted for the job's current stage.

    :param job: The job; the script runs with its workspace as working directory.
    :param call: The run_script tool call with script name and arguments.
    :return: The exit code, stdout and stderr; flagged as error on a non-zero exit code.
    """
    skill = STAGE_SKILLS[job.stage]
    script = call.input.get("script", "")
    if script not in skill.allowed_scripts:
        return _err(call, (
            f"script '{script}' is not allowed in stage {job.stage.value}. "
            f"Allowed: {sorted(skill.allowed_scripts)}"
        ))
    script_path = skill.scripts_dir / script
    if not script_path.exists():
        return _err(call, f"script not found on server: {script}")

    cmd = [sys.executable, str(script_path), *(str(a) for a in call.input.get("args", []))]
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        cwd=str(job.workspace),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    out, err = await proc.communicate()
    text = (
        f"exit_code: {proc.returncode}\n"
        f"--- stdout ---\n{out.decode('utf-8', 'replace')}\n"
        f"--- stderr ---\n{err.decode('utf-8', 'replace')}"
    )
    return ToolResultBlock(
        tool_use_id=call.id,
        content=[TextBlock(text=text)],
        is_error=proc.returncode != 0,
    )
