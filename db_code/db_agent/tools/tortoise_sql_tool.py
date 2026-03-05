"""Custom async read-only SQL tool using Tortoise ORM."""

import re
from typing import List, Dict

from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field
from tortoise import Tortoise


class ExecuteSQLInput(BaseModel):
    """Input for the execute_sql tool."""

    query: str = Field(description="Read-only SQL SELECT or WITH query to execute")


# Dangerous SQL patterns - reject if found (case-insensitive)
_READ_ONLY_PATTERN = re.compile(
    r"^\s*(select|with)\s+",
    re.IGNORECASE | re.DOTALL,
)
_DANGEROUS_PATTERNS = [
    re.compile(r"\b(insert|update|delete|drop|truncate|alter|create|grant|revoke)\b", re.IGNORECASE),
    re.compile(r";\s*(select|insert|update|delete|drop)", re.IGNORECASE),  # Multiple statements
]


def _is_read_only(sql: str) -> bool:
    """Check that SQL is read-only (SELECT or WITH)."""
    sql_stripped = sql.strip()
    if not sql_stripped:
        return False
    if not _READ_ONLY_PATTERN.match(sql_stripped):
        return False
    for pat in _DANGEROUS_PATTERNS:
        if pat.search(sql):
            return False
    return True


class ExecuteSQLTool(BaseTool):
    """Execute read-only SQL queries against the PostgreSQL database via Tortoise ORM."""

    name: str = "execute_sql"
    description: str = (
        "Execute a single read-only SQL SELECT (or WITH) query against the PostgreSQL database. "
        "Argument: 'query' (string) containing one valid, read-only SQL statement. "
        "Only SELECT and WITH (CTE) queries are allowed; any attempt to modify data is rejected. "
        "Use this tool after you understand the relevant tables and columns (see the SQL Expert skill and schema tools) "
        "to fetch aggregated results or a focused subset of rows."
    )
    args_schema: type = ExecuteSQLInput

    def _run(self, query: str) -> str:
        """Synchronous run - not used; we use async."""
        raise NotImplementedError("Use async ainvoke instead.")

    async def _arun(self, query: str, **kwargs: object) -> str:
        """Execute the SQL query asynchronously and return results or error."""
        if not query or not query.strip():
            return "Error: Empty SQL query."

        if not _is_read_only(query):
            return (
                "Error: Only SELECT and WITH (CTE) read-only queries are allowed. "
                "Rejecting query for safety."
            )

        try:
            conn = Tortoise.get_connection("default")
            rows: List[Dict] = await conn.execute_query_dict(query)
            if not rows:
                return "Query returned no rows."

            total_rows = len(rows)
            max_rows = 100
            sample = rows[:max_rows]
            columns = list(sample[0].keys()) if sample else []

            header = (
                f"Query returned {total_rows} rows. "
                f"Showing first {min(total_rows, max_rows)}. "
                f"Columns: {', '.join(columns)}.\n"
            )
            return header + repr(sample)
        except Exception as e:
            return f"Database error: {type(e).__name__}: {e}"


execute_sql_tool = ExecuteSQLTool()
