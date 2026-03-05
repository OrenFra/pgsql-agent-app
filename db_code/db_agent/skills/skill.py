from pathlib import Path
from typing import List, TypedDict


class Skill(TypedDict):
    """A skill that can be progressively disclosed to the agent."""

    name: str  # Unique identifier for the skill
    description: str  # 1-2 sentence description to show in system prompt
    content: str  # Full skill content with detailed instructions


def _read_text(path: Path) -> str:
    """Read a UTF-8 text file and return its contents."""
    return path.read_text(encoding="utf-8")


_BASE_DIR = Path(__file__).parent

# Python analysis skill: content exactly mirrors python-analysis/SKILL.md.
_PYTHON_ANALYSIS_CONTENT = _read_text(_BASE_DIR / "python-analysis" / "SKILL.md")

PYTHON_ANALYSIS_SKILL: Skill = {
    "name": "python-analysis",
    "description": (
        "Use this skill for requests that require Python-based analysis of data already "
        "retrieved from the PostgreSQL database using SQL."
    ),
    "content": _PYTHON_ANALYSIS_CONTENT,
}

# SQL expert skill: content is sql-expert/SKILL.md followed by db_schema.md.
_SQL_EXPERT_SKILL_MD = _read_text(_BASE_DIR / "sql-expert" / "SKILL.md")
_SQL_EXPERT_DB_SCHEMA_MD = _read_text(_BASE_DIR / "sql-expert" / "db_schema.md")
_SQL_EXPERT_CONTENT = _SQL_EXPERT_SKILL_MD + "\n\n" + _SQL_EXPERT_DB_SCHEMA_MD

SQL_EXPERT_SKILL: Skill = {
    "name": "sql-expert",
    "description": (
        "Use this skill for ALL the requests that require querying the database or "
        "understanding the PostgreSQL filesystem database schema to answer questions about it."
    ),
    "content": _SQL_EXPERT_CONTENT,
}

SKILLS: List[Skill] = [
    PYTHON_ANALYSIS_SKILL,
    SQL_EXPERT_SKILL,
]
