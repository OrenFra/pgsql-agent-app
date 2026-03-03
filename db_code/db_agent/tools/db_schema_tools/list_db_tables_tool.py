"""List all user tables in the current PostgreSQL database."""

from __future__ import annotations

import json
from typing import Dict, List

from langchain_core.tools import BaseTool
from pydantic import BaseModel
from tortoise import Tortoise


class _NoArgs(BaseModel):
    """No arguments are required for this tool."""

    pass


class ListDBTablesTool(BaseTool):
    """List all user tables in the current PostgreSQL database.

    This tool has no arguments. When invoked, it returns a JSON array where
    each item describes one table. Example output (formatted here for clarity):

    [
      {
        "schema": "public",
        "table": "projects",
        "table_type": "BASE TABLE",
        "estimated_row_count": 120.0
      },
      {
        "schema": "public",
        "table": "entities",
        "table_type": "BASE TABLE",
        "estimated_row_count": 4500.0
      }
    ]

    Recommended usage:
    - Call this FIRST when you are not sure which tables exist.
    - Use it to discover table names before writing any SQL.
    """

    name: str = "list_db_tables"
    description: str = (
        "List all user tables in the current PostgreSQL database, including their schema, "
        "table type (e.g. BASE TABLE, PARTITIONED TABLE) and an estimated row count. "
        "This tool takes NO arguments. Call it when you are unsure which tables exist "
        "or want a quick overview of the database structure before writing SQL."
    )
    args_schema: type = _NoArgs

    def _run(self) -> str:  # type: ignore[override]
        """Synchronous run - not used; we use async."""
        raise NotImplementedError("Use async ainvoke instead.")

    async def _arun(self, **kwargs: object) -> str:  # type: ignore[override]
        """Return a JSON list of all user tables and basic metadata."""
        try:
            conn = Tortoise.get_connection("default")
        except KeyError:
            return "Error: Database connection 'default' is not initialized."

        # Restrict to non-system schemas; rely on PostgreSQL's catalogs.
        query = """
            SELECT
                n.nspname AS schema,
                c.relname AS table,
                CASE c.relkind
                    WHEN 'r' THEN 'BASE TABLE'
                    WHEN 'p' THEN 'PARTITIONED TABLE'
                    WHEN 'v' THEN 'VIEW'
                    ELSE c.relkind::text
                END AS table_type,
                c.reltuples AS estimated_row_count
            FROM pg_class c
            JOIN pg_namespace n ON n.oid = c.relnamespace
            WHERE c.relkind IN ('r', 'p')
              AND n.nspname NOT IN ('pg_catalog', 'information_schema', 'pg_toast')
            ORDER BY n.nspname, c.relname;
        """
        try:
            rows: List[Dict] = await conn.execute_query_dict(query)
        except Exception as e:  # pragma: no cover - defensive
            return f"Database error while listing tables: {type(e).__name__}: {e}"

        return json.dumps(rows, default=str)


list_db_tables_tool = ListDBTablesTool()
