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
        "Execute a read-only SQL SELECT (or WITH) query against the PostgreSQL database. "
        "Argument: 'query' (string) containing a single read-only SQL statement. "
        "Database schema summary:\n"
        "- projects(id, name)\n"
        "- entities(id, host_name, project_id -> projects.id)\n"
        "- dir_records(id, entity_id -> entities.id, raw_path, path)\n"
        "- dir_records_metadata(id, entity_id -> entities.id, dir_record_id -> dir_records.id, "
        "creation_time, last_updated, base_name, file_extension)\n\n"
        "Best practices:\n"
        "- You do not need to query all the data in one query, you can explore and query some data, then process the result you got and decide what to query next to answer the user."
        "- Filter only with valid sql and on valid table and COLUMN names."
        "- If you can, filter by entity_id to avoid scanning all partitions in the dir records and dir records metadata tables.\n"
        "- Prefer doing aggregations (COUNT, GROUP BY, AVG, MIN/MAX) in SQL instead of Python.\n"
        "- Avoid selecting wide, unfiltered data from partitioned tables.\n\n"
        "Example 1 (count paths per host in a project):\n"
        "  SELECT e.host_name, COUNT(*) AS path_count\n"
        "  FROM projects p\n"
        "  JOIN entities e ON e.project_id = p.id\n"
        "  JOIN dir_records dr ON dr.entity_id = e.id\n"
        "  WHERE p.name = 'X'\n"
        "  GROUP BY e.host_name\n"
        "  ORDER BY path_count DESC;\n\n"
        "Example 2 (Get most unique file extension of each computer):\n"
        "  Select * from entities\n"
        "  This way you know all the entities and their ids\n"
        "  Then you can find all the file extensions appearances like this:\n"
        "  select count(*), entity_id, file_extension from dir_records_metadata group by entity_id, file_extension order by entity_id"
        "  Then you can cross this data with the entities you queried before and find the top 1 most common file extension for each computer"
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
