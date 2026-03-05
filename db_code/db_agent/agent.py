"""Deep Agent factory for the AI Data Agent."""

from pathlib import Path

from deepagents import create_deep_agent
from deepagents.backends.filesystem import FilesystemBackend
from langchain_groq import ChatGroq
from langchain_ollama import ChatOllama

from db_agent.tools import (
    execute_sql_tool,
    get_python_tool,
    describe_table_tool,
    search_schema_tool,
)


def _load_master_instructions() -> str:
    """Load master_instructions.md from the db_agent directory."""
    path = Path(__file__).parent / "master_instructions.md"
    if not path.exists():
        return (
            "You are an intelligent data analyst assistant. "
            "Query the database first with execute_sql, then use python_repl for analysis if needed."
        )
    return path.read_text(encoding="utf-8")


def create_db_agent():
    """Create the Deep Agent with database and Python analysis tools."""
    instructions = _load_master_instructions()

    llm = ChatGroq(
        model="llama-3.3-70b-versatile",
        temperature=0,
    )

    tools = [
        describe_table_tool,
        search_schema_tool,
        execute_sql_tool,
        get_python_tool(),
    ]

    # Use a filesystem backend rooted at the project so skills and other files
    # are available to the deep agent.
    project_root = Path(__file__).resolve().parents[2]
    skills_dir = project_root / "db_code" / "db_agent" / "skills"
    backend = FilesystemBackend(root_dir=str(skills_dir), virtual_mode=True)

    agent = create_deep_agent(
        model=llm,
        tools=tools,
        system_prompt=instructions,
        backend=backend,
        skills=[str(skills_dir)],
    )

    return agent
