"""Provider-agnostic tool schemas exposed to the agent. The set is the same for
every stage; `run_script` is gated per-stage at execution time via the skill's
allowed_scripts whitelist."""
from __future__ import annotations

from app.models.ai import ToolSchema
from app.config import settings

TOOLS: list[ToolSchema] = [
    ToolSchema(
        name="read_pdf",
        description=(
            "Read an uploaded PDF from the job workspace. Returns extracted text and "
            "rendered page images. Use `pages` (e.g. \"1-5\") to page through large "
            f"decks; at most {settings.pdf_max_pages_per_batch} pages of images per call."
        ),
        input_schema={
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Workspace-relative path to the PDF."},
                "pages": {"type": "string", "description": "Optional page range, e.g. '1-5' or '3'."},
            },
            "required": ["path"],
        },
    ),
    ToolSchema(
        name="read_file",
        description="Read a UTF-8 text file from the job workspace.",
        input_schema={
            "type": "object",
            "properties": {"path": {"type": "string"}},
            "required": ["path"],
        },
    ),
    ToolSchema(
        name="write_file",
        description="Write a UTF-8 text file into the job workspace (creates parent dirs).",
        input_schema={
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "content": {"type": "string"},
            },
            "required": ["path", "content"],
        },
    ),
    ToolSchema(
        name="list_dir",
        description="List files in a workspace directory (default '.').",
        input_schema={
            "type": "object",
            "properties": {"path": {"type": "string"}},
        },
    ),
    ToolSchema(
        name="run_script",
        description=(
            "Run a bundled skill script (by filename, e.g. 'json_to_cypher.py'). "
            "Only scripts whitelisted for the current stage are allowed. Returns "
            "stdout, stderr and the exit code."
        ),
        input_schema={
            "type": "object",
            "properties": {
                "script": {"type": "string", "description": "Script filename, e.g. 'json_to_cypher.py'."},
                "args": {"type": "array", "items": {"type": "string"}, "description": "CLI arguments."},
            },
            "required": ["script"],
        },
    ),
    ToolSchema(
        name="ask_user",
        description=(
            "Ask the user one or more questions and pause until they answer. Use this "
            "wherever the skill says to ask the user (ambiguous granularity, missing "
            "metadata, borderline decisions)."
        ),
        input_schema={
            "type": "object",
            "properties": {
                "questions": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "header": {"type": "string", "description": "Short label (<= 12 chars)."},
                            "question": {"type": "string"},
                            "multiSelect": {"type": "boolean"},
                            "options": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "label": {"type": "string"},
                                        "description": {"type": "string"},
                                    },
                                    "required": ["label"],
                                },
                            },
                        },
                        "required": ["header", "question"],
                    },
                }
            },
            "required": ["questions"],
        },
    ),
    ToolSchema(
        name="stage_complete",
        description=(
            "Call once when this stage is finished: its .cypher artifact(s) are written "
            "and (where applicable) verified. After this the user reviews the resulting "
            "graph visually and validates it."
        ),
        input_schema={
            "type": "object",
            "properties": {
                "summary": {"type": "string", "description": "Short summary of what was produced."},
                "artifacts": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Workspace-relative paths of produced files (.cypher etc.).",
                },
            },
            "required": ["summary", "artifacts"],
        },
    ),
]
