from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field

from db_agent.skills.skill import SKILLS


class LoadSkillInput(BaseModel):
    """Input for the load_skill tool."""

    skill_name: str = Field(
        ...,
        description=(
            "The name of the skill to load "
            "(for example: 'sql-expert', 'python-analysis')."
        ),
    )


class LoadSkillTool(BaseTool):
    """Load the full content of a skill into the agent's context.

    Use this when you need detailed information about how to handle a specific
    type of request. This will provide you with comprehensive instructions,
    policies, and guidelines for the skill area.
    """

    name: str = "load_skill"
    description: str = (
        "Load detailed instructions for a specific skill into context. "
        "Input: 'skill_name' (string) naming one of the available skills. "
        "Use this to retrieve comprehensive skill instructions and policies "
        "before solving tasks that rely on that skill."
    )
    args_schema: type = LoadSkillInput

    def _run(self, skill_name: str) -> str:  # type: ignore[override]
        """Synchronous run - not used; we use async."""
        raise NotImplementedError("Use async ainvoke instead.")

    async def _arun(self, skill_name: str, **kwargs: object) -> str:  # type: ignore[override]
        """Asynchronously load and return the requested skill content."""
        for skill in SKILLS:
            if skill["name"] == skill_name:
                return f"Loaded skill: {skill_name}\n\n{skill['content']}"

        available = ", ".join(s["name"] for s in SKILLS)
        return f"Skill '{skill_name}' not found. Available skills: {available}"


load_skill = LoadSkillTool()
