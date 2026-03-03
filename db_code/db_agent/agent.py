"""LangChain ReAct-style agent factory for the AI Data Agent."""

from pathlib import Path

from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage
from langchain.agents import create_agent

from db_agent.tools import execute_sql_tool, get_python_repl_tool


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
    """Create the LangChain agent with Tortoise SQL and Python REPL tools."""
    instructions = _load_master_instructions()
    llm = ChatGroq(
        model="llama-3.3-70b-versatile",
        temperature=0,
        # Reads GROQ_API_KEY from environment; do not hardcode secrets in code.
    )
    tools = [execute_sql_tool, get_python_repl_tool()]
    prompt = SystemMessage(content=instructions)
    return create_agent(llm, tools, system_prompt=prompt)
