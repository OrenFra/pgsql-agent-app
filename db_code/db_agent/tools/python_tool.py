"""Python REPL tool for data analysis - use ONLY after retrieving data via execute_sql."""

import pandas as pd
import numpy as np

from langchain_experimental.tools import PythonAstREPLTool


def get_python_tool() -> PythonAstREPLTool:
    """Return PythonAstREPLTool with pandas/numpy pre-loaded.

    IMPORTANT RULES FOR THIS TOOL:
    - Do NOT write any import statements. pandas is already available as 'pd' and numpy as 'np'.
    - Use this tool ONLY after data has been retrieved via execute_sql.
    - Use it only for analysis, aggregations, statistics, filtering, or formatting—never for DB access.
    - Pass your code as a single string argument (field name: 'query').
    - This REPL may only use Python's standard library plus the pre-loaded 'pd' and 'np'.
    """
    return PythonAstREPLTool(
        name="python_repl",
        description=(
            "Run small Python snippets to analyze data you already fetched with execute_sql. "
            "Do NOT write any import statements—pandas is available as 'pd' and numpy as 'np' "
            "without importing them. Use this tool only for aggregations, statistics, filtering, "
            "or formatting of existing data, never for database access. Pass your code as a single "
            "string input (field name: 'query')."
        ),
        globals={"pd": pd, "np": np},
    )
