"""Search PostgreSQL tables and columns by a name fragment."""

from __future__ import annotations

import json
import re
from typing import Dict, List

from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field
from tortoise import Tortoise


class SearchSchemaInput(BaseModel):
    """Arguments for the search_schema tool."""

    name_fragment: str = Field(
        ...,
        description=(
            "Fragment of a table or column name to search for "
            "(e.g. 'extension', 'project', 'entity'). Use a single word or fragment"
            "It is matched case-insensitively."
        ),
    )


_NAME_FRAGMENT_RE = re.compile(r"^[A-Za-z0-9_]+$")


class SearchSchemaTool(BaseTool):
    """Search PostgreSQL tables and columns by a name fragment.

    Input:
    - name_fragment (str): fragment of a table/column name to search for.

    Output:
    - JSON array where each item has:
      - table: table name
      - column: column name

    Recommended usage:
    - Use this when you know the concept (e.g. 'extension', 'project') but do
      not remember the exact table or column name.
    - After finding candidates, call describe_table on the chosen table, then
      write SQL using execute_sql.
    """

    name: str = "search_schema"
    description: str = (
        "Search PostgreSQL tables and columns by a name fragment. Input: 'name_fragment' "
        "(single word or fragment). Returns all (table, column) pairs in the current schema "
        "whose names contain that fragment, case-insensitively. Use this when you know the "
        "concept but not the exact table/column name, and combine it with the SQL Expert skill "
        "to decide which tables to query."
    )
    args_schema: type = SearchSchemaInput

    def _run(self, name_fragment: str) -> str:  # type: ignore[override]
        """Synchronous run - not used; we use async."""
        raise NotImplementedError("Use async ainvoke instead.")

    async def _arun(self, name_fragment: str, **kwargs: object) -> str:  # type: ignore[override]
        """Return a JSON list of (table, column) pairs matching the fragment."""
        fragment = name_fragment.strip()
        if not fragment:
            return "Error: 'name_fragment' argument is required."
        if not _NAME_FRAGMENT_RE.match(fragment):
            return (
                "Error: Invalid name_fragment. Only letters, digits, and underscores "
                "are allowed."
            )

        try:
            conn = Tortoise.get_connection("default")
        except KeyError:
            return "Error: Database connection 'default' is not initialized."

        # Match fragment in table_name or column_name, within the current schema.
        # Since fragment is validated (alphanumeric + underscore only), we can
        # safely embed it into the LIKE pattern.
        like_pattern = f"%{fragment}%"
        query = f"""
            SELECT
                table_name AS table,
                column_name AS column
            FROM information_schema.columns
            WHERE table_schema = current_schema()
              AND (table_name ILIKE '{like_pattern}' OR column_name ILIKE '{like_pattern}')
            ORDER BY table_name, ordinal_position;
        """

        try:
            rows: List[Dict] = await conn.execute_query_dict(query)
        except Exception as e:  # pragma: no cover - defensive
            return f"Database error while searching schema: {type(e).__name__}: {e}"

        return json.dumps(rows, default=str)


search_schema_tool = SearchSchemaTool()
