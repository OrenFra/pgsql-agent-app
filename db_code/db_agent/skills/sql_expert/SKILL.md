---
name: sql-expert
description: Use this skill for ALL the requests that require querying the database or understanding the PostgreSQL filesystem database schema to answer questions about it.
---

# SQL expert for the filesystem database

## Overview

Use this skill whenever a user asks questions that must be answered by querying the PostgreSQL database that stores
filesystem information for projects, entities (computers), directory records, and directory metadata.

This skill contains:

- High-level workflow for exploring the schema and writing correct SQL.
- Safety rules for read-only access and efficient querying.
- Guidance on when and how to use the database tools:
    - `search_schema`
    - `describe_table`
    - `execute_sql`
- A separate `db_schema.md` file in this same skill directory with detailed table and relationship references.

## Tools provided by this skill

The following tools are relevant for this skill. Use them as building blocks rather than exposing them directly to the
user.

- **`search_schema`** – Search PostgreSQL tables and columns by a name fragment.
    - **When to use**: You know the concept (for example: “extension”, “project”, “entity”) but not the exact table or
      column name.
    - **How to use**:
        - Provide a short, single-word fragment like `"extension"` or `"project"`.
        - Use the returned `(table, column)` pairs to identify candidate tables and columns.

- **`describe_table`** – Describe a single PostgreSQL table: columns, keys, and relationships.
    - **When to use**: Before writing any non‑trivial SQL against a table, or whenever you are not 100% sure about its
      columns, primary key, or foreign keys.
    - **How to use**:
        - Provide the bare table name (for
          example: `"projects"`, `"entities"`, `"dir_records"`, `"dir_records_metadata"`).
        - Read the JSON output to understand column names, data types, nullability, defaults, primary key columns, and
          foreign key relationships.

- **`execute_sql`** – Execute a single read-only SQL `SELECT` or `WITH` query.
    - **When to use**: After you have confirmed the schema and are ready to run a specific read-only query to fetch
      aggregated results or a limited subset of rows.
    - **How to use**:
        - Provide one valid `SELECT` or `WITH` statement as the `query` string.
        - Focus on aggregated or filtered queries rather than large unfiltered scans, especially on partitioned tables.

## Core workflow

Follow this general workflow when using this skill:

1. **Clarify the user’s question** in your own words so you understand what needs to be measured, counted, grouped, or
   compared.
2. **Review `db_schema.md`** in this skill for a consolidated reference of the projects, entities, dir_records, and
   dir_records_metadata tables and how they relate.
3. **Explore the schema if needed**:
    - If you are unsure which tables exist or where the data might live, call `search_schema` with a short concept
      fragment.
    - If you have a candidate table but are not certain about its columns or relationships, call `describe_table`.
4. **Design one OR MORE read‑only SQL queries** that:
    - Filter as much as possible in SQL rather than in Python.
    - Use `WHERE` clauses to constrain on relevant fields.
    - Filter for a specific partition in the partitioned tables if possible.
    - Use appropriate aggregates (`COUNT`, `SUM`, `AVG`, `MIN`, `MAX`, `GROUP BY`) when the user asks for high-level
      statistics.
5. **Execute your query with `execute_sql`** and carefully inspect:
    - Column names and types.
    - The rows returned
6. **Iterate**:
    - **You do not have to write one sql query to answer the user's question.** If you think it is better to split the
      search to multiple different queries that fetch different data (for example from different tables) and then
      combines it, you are encouraged to do so.
    - If the result does not fit what you searched to answer the user, redefine your sql query after inspection the db
      schema and rethinking.
    - Feel free to return to the execute_sql tool at any time also after moving to other tools if you feel like you need
      more information from the db.
7. **Only after the SQL results fully support the user’s question**, formulate a clear natural‑language answer grounded
   strictly in the data returned (Possibly use python after if needed).

## Safety and performance rules

Always follow these rules when using this skill:

- **Read‑only access only**:
    - Never attempt to `INSERT`, `UPDATE`, `DELETE`, `DROP`, `TRUNCATE`, `ALTER`, `CREATE`, `GRANT`, or `REVOKE`.
    - Only `SELECT` and `WITH` queries are allowed. If a query is not strictly read‑only, do not attempt to run it.
- **Never guess the schema**:
    - If you are not sure about table or column names, always review the **`db_schema.md`** instead of guessing.
    - Use `db_schema.md` as a reliable reference.
- **Use the database engine for heavy lifting**:
    - Perform aggregations and filtering in SQL whenever possible instead of fetching large raw datasets.
    - Avoid scanning entire partitioned tables without filters; always filter by partition key if possible.
- Default to clear, high‑level explanations of what the data shows.

## Examples (conceptual)

These are example patterns; adapt them to the actual question and schema:

- **Show computers present in the db**:
    - Use `db_schema.md` to understand the entities table and what to search.
    - Based on this data run a query to find all entities and the project they relate
      to: `Select e.id, e.host_name, p.name from entities e join projects p on e.project_id = p.id`
    - Use the data returned from this query to give the user the computer's names and the projects they belong to.

- **Most common file extensions per computer**:
    - Use `db_schema.md` to understand how the computers and the file extensions are connected (via the
      dir_records_metadata table) and understand what query to run.
    - Use `execute_sql` to aggregate counts of file extensions grouped by `entity_id` (and join back
      to `entities` for host names):
      `select drm.file_extension, drm.entity_id, e.host_name, count(*) from dir_records_metadata drm join entities e on drm.entity_id = e.id group by drm.entity_id, drm.file_extension, e.host_name order by entity_id, count desc`.
      Then you can use python or find yourself the top asked file extensions for each computer and give them to the user
      with the computer name.

Remember: the SQL you write must respect the read‑only and performance rules above, and your final answer must be fully
supported by the query results.
