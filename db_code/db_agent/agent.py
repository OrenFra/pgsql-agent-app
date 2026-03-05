"""Agent factory for the AI Data Agent."""

from pathlib import Path

from langchain.agents import create_agent
from langchain_groq import ChatGroq

from db_agent.tools import (
    describe_table_tool,
    execute_sql_tool,
    get_python_tool,
    search_schema_tool,
    load_skill,
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
    """Create the LangChain agent with database and Python analysis tools."""
    instructions = _load_master_instructions()
    tools = [
        load_skill,
        describe_table_tool,
        search_schema_tool,
        execute_sql_tool,
        get_python_tool()
    ]

    llm = ChatGroq(
        model="openai/gpt-oss-120b",
        temperature=0,
    )

    agent = create_agent(
        model=llm,
        tools=tools,
        system_prompt=instructions,
    )

    return agent
