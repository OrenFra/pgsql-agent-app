"""Schema introspection tools for the AI Database Agent.

These tools let the model inspect the live PostgreSQL schema at runtime
instead of relying only on static documentation. They are designed to be:

- Safe: all queries are read-only and target system catalog / information_schema.
- Focused: each tool answers a specific question about the schema.
- LLM-friendly: responses are concise JSON the model can easily read and use.

Tool overview for the model:

- list_db_tables
    - No inputs.
    - Returns all user tables in the current database, including their schema,
      table type (e.g. BASE TABLE, PARTITIONED TABLE) and an estimated row count.
    - Use this when you are not sure which tables exist or what they are called.

- describe_table
    - Input: table (str) – name of a single table (e.g. "dir_records_metadata").
    - Returns a structured JSON description of that table:
      columns, data types, nullability, defaults, primary key and foreign keys.
    - Use this whenever you are not completely sure about the structure of a
      table before writing a non-trivial SQL query against it.

- search_schema
    - Input: name_fragment (str) – fragment of a table/column name
      (e.g. "extension", "project", "entity").
    - Returns all tables/columns whose name contains that fragment.
    - Use this when you know the concept but not the exact table/column name.
"""

from __future__ import annotations

import json
import re
from typing import Dict, List

from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field
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


class DescribeTableInput(BaseModel):
    """Arguments for the describe_table tool."""

    table: str = Field(
        ...,
        description=(
            "Name of the table to describe (e.g. 'projects', 'entities', "
            "'dir_records', 'dir_records_metadata'). Schema is assumed from the "
            "current search_path; do not include a schema prefix."
        ),
    )


_TABLE_NAME_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


class DescribeTableTool(BaseTool):
    """Describe a single PostgreSQL table: columns, keys, and relationships.

    Input:
    - table (str): the table name (without schema).

    Output:
    - JSON object with:
      - table: table name
      - columns: list of column definitions with:
        - name, data_type, is_nullable (bool), default, is_pk (bool), is_fk (bool)
        - references (for foreign keys): {\"table\", \"column\"}
      - primary_key: list of PK column names
      - foreign_keys: list of foreign key definitions with:
        - column, references_table, references_column

    Recommended usage:
    - Call this BEFORE writing a non-trivial query when you are not 100% sure
      about a table's columns or relationships.
    - Combine with list_db_tables and search_schema for robust schema discovery.
    """

    name: str = "describe_table"
    description: str = (
        "Describe a single PostgreSQL table: columns, data types, nullability, defaults, "
        "primary key, and foreign keys. Input: 'table' (name of the table, without schema). "
        "Use this tool whenever you are not completely sure about a table's structure before "
        "writing SQL that reads from it."
    )
    args_schema: type = DescribeTableInput

    def _run(self, table: str) -> str:  # type: ignore[override]
        """Synchronous run - not used; we use async."""
        raise NotImplementedError("Use async ainvoke instead.")

    async def _arun(self, table: str, **kwargs: object) -> str:  # type: ignore[override]
        """Return a JSON description of the requested table."""
        table = table.strip()
        if not table:
            return "Error: 'table' argument is required."
        if not _TABLE_NAME_RE.match(table):
            return (
                "Error: Invalid table name. Only letters, digits, and underscores are allowed, "
                "and it must not start with a digit."
            )

        try:
            conn = Tortoise.get_connection("default")
        except KeyError:
            return "Error: Database connection 'default' is not initialized."

        # 1) Column definitions.
        columns_sql = f"""
            SELECT
                column_name,
                data_type,
                is_nullable,
                column_default
            FROM information_schema.columns
            WHERE table_name = '{table}'
              AND table_schema = current_schema()
            ORDER BY ordinal_position;
        """

        # 2) Primary key columns.
        pk_sql = f"""
            SELECT
                a.attname AS column_name
            FROM pg_index i
            JOIN pg_class c ON c.oid = i.indrelid
            JOIN pg_namespace n ON n.oid = c.relnamespace
            JOIN pg_attribute a ON a.attrelid = i.indrelid
                                 AND a.attnum = ANY(i.indkey)
            WHERE c.relname = '{table}'
              AND n.nspname = current_schema()
              AND i.indisprimary;
        """

        # 3) Foreign keys.
        fk_sql = f"""
            SELECT
                kcu.column_name,
                ccu.table_name AS foreign_table,
                ccu.column_name AS foreign_column
            FROM information_schema.table_constraints tc
            JOIN information_schema.key_column_usage kcu
              ON tc.constraint_name = kcu.constraint_name
             AND tc.table_schema = kcu.table_schema
            JOIN information_schema.constraint_column_usage ccu
              ON ccu.constraint_name = tc.constraint_name
             AND ccu.table_schema = tc.table_schema
            WHERE tc.constraint_type = 'FOREIGN KEY'
              AND tc.table_name = '{table}'
              AND tc.table_schema = current_schema();
        """

        try:
            columns_rows: List[Dict] = await conn.execute_query_dict(columns_sql)
            pk_rows: List[Dict] = await conn.execute_query_dict(pk_sql)
            fk_rows: List[Dict] = await conn.execute_query_dict(fk_sql)
        except Exception as e:  # pragma: no cover - defensive
            return f"Database error while describing table: {type(e).__name__}: {e}"

        if not columns_rows:
            return (
                f"Error: Table '{table}' does not exist in the current schema "
                "or has no columns."
            )

        pk_cols = {row["column_name"] for row in pk_rows}

        fk_map: Dict[str, Dict[str, str]] = {}
        fk_list: List[Dict[str, str]] = []
        for row in fk_rows:
            col_name = row["column_name"]
            foreign_table = row["foreign_table"]
            foreign_column = row["foreign_column"]
            details = {
                "table": foreign_table,
                "column": foreign_column,
            }
            fk_map[col_name] = details
            fk_list.append(
                {
                    "column": col_name,
                    "references_table": foreign_table,
                    "references_column": foreign_column,
                }
            )

        columns_output: List[Dict] = []
        for row in columns_rows:
            name = row["column_name"]
            col: Dict[str, object] = {
                "name": name,
                "data_type": row["data_type"],
                "is_nullable": row["is_nullable"] == "YES",
                "default": row["column_default"],
                "is_pk": name in pk_cols,
                "is_fk": name in fk_map,
            }
            if name in fk_map:
                col["references"] = fk_map[name]
            columns_output.append(col)

        result = {
            "table": table,
            "columns": columns_output,
            "primary_key": sorted(pk_cols),
            "foreign_keys": fk_list,
        }

        return json.dumps(result, default=str)


class SearchSchemaInput(BaseModel):
    """Arguments for the search_schema tool."""

    name_fragment: str = Field(
        ...,
        description=(
            "Fragment of a table or column name to search for "
            "(e.g. 'extension', 'project', 'entity'). Only letters, digits, "
            "and underscores are allowed; it is matched case-insensitively."
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
        "(letters, digits, underscores). Returns all (table, column) pairs in the current "
        "schema whose names contain that fragment, case-insensitively. Use this when you "
        "know the concept but not the exact table/column name."
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


# Singleton tool instances to be imported and registered with the agent.
list_db_tables_tool = ListDBTablesTool()
describe_table_tool = DescribeTableTool()
search_schema_tool = SearchSchemaTool()
