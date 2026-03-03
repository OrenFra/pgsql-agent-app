"""Python REPL tool for data analysis - use ONLY after retrieving data via execute_sql."""

import pandas as pd
import numpy as np

from langchain_experimental.tools import PythonAstREPLTool


def get_python_tool() -> PythonAstREPLTool:
    """Return PythonAstREPLTool with pandas/numpy pre-loaded.

    IMPORTANT: This tool must be used ONLY after data has been retrieved via execute_sql.
    Use it for analysis, aggregations, statistics, filtering, or formatting—never for DB access.
    This REPL cannot import any third-party libraries; it may only use Python's standard library.
    pandas is available as 'pd' and numpy as 'np' without importing them inside the REPL code.
    """
    return PythonAstREPLTool(
        name="python_repl",
        description=(
            "Execute Python code for data analysis. Use ONLY after you have already "
            "retrieved data with execute_sql. This REPL cannot import any third-party "
            "libraries and may only use Python's built-in standard library. "
            "pandas is available as 'pd' and numpy as 'np' without importing them. "
            "Use for aggregations, statistics, filtering, or formatting—never for database queries."
        ),
        globals={"pd": pd, "np": np},
    )
