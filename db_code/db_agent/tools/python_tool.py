"""Python REPL tool for data analysis - use ONLY after retrieving data via execute_sql."""

import pandas as pd
import numpy as np

from langchain_experimental.tools import PythonAstREPLTool


def get_python_tool() -> PythonAstREPLTool:
    """Return PythonAstREPLTool with pandas/numpy pre-loaded.
    """
    return PythonAstREPLTool(
        name="python_repl",
        description=(
            "Run small Python snippets to analyze data you already fetched with execute_sql. "
            "Do NOT write any import statements— pandas is available as 'pd' and numpy as 'np' "
            "without importing them. Use this tool only for aggregations, statistics, filtering, "
            "or formatting of existing data. Pass your code as a single "
            "string input (field name: 'query'). See the Python Analysis skill for guidance on when "
            "and how to use this tool effectively."
        ),
        globals={"pd": pd, "np": np},
    )
