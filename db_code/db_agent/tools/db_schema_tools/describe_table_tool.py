"""Describe a single PostgreSQL table: columns, keys, and relationships."""

from __future__ import annotations

import json
import re
from typing import Dict, List

from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field
from tortoise import Tortoise


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


describe_table_tool = DescribeTableTool()
