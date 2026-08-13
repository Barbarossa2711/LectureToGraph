"""Maps each pipeline stage to its vendored skill assets and builds the system
prompt the agent runs with (the SKILL.md body plus a repo-specific addendum that
rebinds the skill's environment to our tool set and job workspace)."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path

SKILLS_DIR = Path(__file__).resolve().parent


class Stage(str, Enum):
    DOMAIN = "DOMAIN"
    EDGES = "EDGES"
    QUESTIONS = "QUESTIONS"


@dataclass(frozen=True)
class SkillDef:
    name: str
    skill_dir: Path
    allowed_scripts: frozenset[str]

    @property
    def skill_md(self) -> Path:
        return self.skill_dir / "SKILL.md"

    @property
    def scripts_dir(self) -> Path:
        return self.skill_dir / "scripts"

    @property
    def references_dir(self) -> Path:
        return self.skill_dir / "references"


STAGE_SKILLS: dict[Stage, SkillDef] = {
    Stage.DOMAIN: SkillDef(
        name="lecture-domain-model",
        skill_dir=SKILLS_DIR / "lecture-domain-model",
        allowed_scripts=frozenset({"json_to_cypher.py", "verify_slides.py"}),
    ),
    Stage.EDGES: SkillDef(
        name="lecture-concept-edges",
        skill_dir=SKILLS_DIR / "lecture-concept-edges",
        allowed_scripts=frozenset({"verify_edges.py"}),
    ),
    Stage.QUESTIONS: SkillDef(
        name="lecture-review-questions",
        skill_dir=SKILLS_DIR / "lecture-review-questions",
        allowed_scripts=frozenset({"verify_questions.py"}),
    ),
}


def _strip_frontmatter(text: str) -> str:
    """Drop a leading YAML front-matter block (--- ... ---)."""
    if text.startswith("---"):
        end = text.find("\n---", 3)
        if end != -1:
            nl = text.find("\n", end + 1)
            return text[nl + 1:] if nl != -1 else ""
    return text


_ADDENDUM = """

---

# Execution environment (READ THIS — it overrides the skill's tool assumptions)

You are running inside an automated pipeline, not interactive Claude Code. Your
sandbox is the **job workspace**; all file paths are relative to it.

Tools available to you:
- `read_pdf(path, pages?)` — read an uploaded PDF. Returns extracted text AND
  rendered page images. Use `pages` like "1-5" to page through large decks
  (max {max_pages} pages of images per call); call it repeatedly for more.
- `read_file(path)` / `write_file(path, content)` / `list_dir(path)` — plain
  text files inside the workspace. Write your intermediate artifacts here
  (e.g. `<name>.structure.json`, the `.cypher` files).
- `run_script(script, args)` — run a bundled skill script. Allowed for this
  stage: {allowed_scripts}. The script's own directory is on the path; pass the
  filename only (e.g. "json_to_cypher.py").
- `ask_user(questions)` — ask the user. `questions` is a list of
  `{{header, question, options?, multiSelect?}}`. The pipeline pauses and shows
  these to the user; their answers come back as a tool result. Use this exactly
  where the skill says to ask the user.
- `stage_complete(summary, artifacts)` — call this once, at the very end, when
  the stage's `.cypher` artifact(s) are written and verified. `artifacts` is the
  list of workspace-relative paths you produced. After this the user reviews the
  resulting graph visually and validates it.

Rules:
- Do NOT print Cypher by hand for the domain model — always go through
  `run_script("json_to_cypher.py", [...])`.
- The uploaded PDFs are already in the workspace; `list_dir(".")` to see them.
- When the skill text mentions the `Read` tool or `AskUserQuestion`, use
  `read_pdf`/`read_file` and `ask_user` respectively.
"""


_LANG_DIRECTIVE = {
    "de": (
        "\n\n# Sprache\n"
        "Kommuniziere mit dem Benutzer AUSSCHLIESSLICH auf Deutsch. Alle `ask_user`-Fragen, "
        "Überschriften (`header`), Antwortoptionen und Zusammenfassungen MÜSSEN auf Deutsch sein, "
        "unabhängig davon, in welcher Sprache die Skill-Anleitung verfasst ist. Die Graph-Inhalte "
        "(Knoten-/Konzeptnamen, Fragetexte) bleiben in der Originalsprache der Vorlesung."
    ),
    "en": (
        "\n\n# Language\n"
        "Communicate with the user exclusively in English (all `ask_user` questions, headers, "
        "options and summaries)."
    ),
}


def stage_system_prompt(stage: Stage, *, max_pages: int, language: str = "de") -> str:
    skill = STAGE_SKILLS[stage]
    body = _strip_frontmatter(skill.skill_md.read_text(encoding="utf-8"))
    addendum = _ADDENDUM.format(
        max_pages=max_pages,
        allowed_scripts=", ".join(sorted(skill.allowed_scripts)) or "(none)",
    )
    lang = _LANG_DIRECTIVE.get(language, _LANG_DIRECTIVE["de"])
    return body + addendum + lang
