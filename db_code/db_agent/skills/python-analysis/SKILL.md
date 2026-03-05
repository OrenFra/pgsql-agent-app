---
name: python-analysis
description: Use this skill for requests that require Python-based analysis of data already retrieved from the PostgreSQL database using SQL.
---

# Python analysis for SQL results

## Overview

Use this skill when a user’s question requires additional analysis, transformation, or formatting of data that has
already been fetched from the database with SQL.

This skill explains how to:

- Decide when Python is appropriate vs. writing more SQL.
- Use the `python_repl` tool safely and effectively.
- Combine SQL queries and Python analysis into a coherent workflow while keeping the user-facing answer clear and
  grounded in data.

Always fetch data first with `execute_sql` (guided by the SQL expert skill) before using this skill for further
analysis.

## Tool provided by this skill

- **`python_repl`** – A restricted Python REPL with `pandas` and `numpy` pre-loaded.
    - **Capabilities**:
        - Run small Python snippets over data you have already retrieved with SQL.
        - Use `pandas` as `pd` and `numpy` as `np` without importing them.
        - Perform aggregations, statistics, filtering, reshaping, and formatting.
    - **Limitations**:
        - No import statements are allowed.
        - Must not be used for direct database access.
        - Should not perform network or filesystem operations outside the agent’s controlled environment.

## When to use Python vs. SQL

Prefer **SQL** when:

- You can express the computation as aggregations or filters directly in a query (for example, counts, sums, averages,
  minimum/maximum, grouping, or simple joins).
- You only need summary statistics or small result sets that SQL can compute efficiently.

Reach for **Python analysis** with this skill when:

- You need to combine and process data from multiple different sql queries you ran.
- You need to perform more complex transformations on a reasonably sized result set, such as:
    - Computing additional derived metrics from SQL outputs.
    - Pivoting, reshaping, or reindexing tables for presentation.
    - Applying multi-step filtering or ranking logic that is easier to express in code.

Always ensure that the dataset you pass into Python is small enough to handle comfortably in memory.

## How to use `python_repl`

1. **Fetch data with SQL first**:
    - Use the SQL expert skill and tools (`execute_sql`, `describe_table`, `search_schema`) to design and run the right
      query/queries.
    - Confirm the SQL results match what you need conceptually before turning to Python.
2. **Plan your Python transformation**:
    - Decide what you need to compute or transform (for example, additional aggregations, derived columns, sorting,
      pivoting).
    - Keep the code focused and minimal, tailored to the current question.
3. **Write a concise Python snippet**:
    - Assume the result is available in the context you designed (for example, as a variable you define from the tool
      output).
    - Use `pd` for DataFrame operations and `np` for numeric operations.
    - Avoid imports and side effects; stick to analytical logic only.
4. **Run the snippet via `python_repl`**:
    - Pass your entire code block as a single string argument (`query`) to the `python_repl` tool.
5. **Interpret the result**:
    - Read the Python output (for example, a DataFrame summary or computed numbers).
    - Translate it into a clear natural‑language explanation for the user.

## Safety and constraints

When using this skill:

- **No imports**:
    - Do not add any `import` statements. Use only the standard library plus the pre-loaded `pd` and `np`.
- **Analysis only**:
    - Do not attempt to connect to the database, the network, or external systems from Python.
    - Never modify data; analysis must be read‑only with respect to the database results.
- **Controlled scope**:
    - Keep snippets short and task‑focused.
    - Avoid writing large or deeply nested scripts; if logic becomes too complex, reconsider whether additional SQL
      queries would be more appropriate.

## Suggested actions

Use this skill for tasks such as:

- Processing and analyzing data retrieve from multiple different sql queries.
- Computing descriptive statistics (means, medians, standard deviations) over SQL result sets.
- Ranking or sorting entities based on multiple metrics from SQL.
- Creating grouped summaries or simple pivot-style tables for presentation.
- Filtering SQL results according to multi-step conditions that are easier to express in Python.

For each of these, verify that the starting dataset was produced by a safe, read‑only SQL query and that the Python code
remains within the constraints above.
