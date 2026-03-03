"""Python REPL tool for data analysis - use ONLY after retrieving data via execute_sql."""

import pandas as pd
import numpy as np

from langchain_experimental.tools import PythonAstREPLTool


def get_python_repl_tool() -> PythonAstREPLTool:
    """Return PythonAstREPLTool with pandas/numpy pre-loaded.

    IMPORTANT: This tool must be used ONLY after data has been retrieved via execute_sql.
    Use it for analysis, aggregations, statistics, filtering, or formatting—never for DB access.
    """
    return PythonAstREPLTool(
        name="python_repl",
        description=(
            "Execute Python code for data analysis. Use ONLY after you have already "
            "retrieved data with execute_sql. Available: pandas as 'pd', numpy as 'np'. "
            "Use for aggregations, statistics, filtering, or formatting—never for database queries."
        ),
        globals={"pd": pd, "np": np},
    )
