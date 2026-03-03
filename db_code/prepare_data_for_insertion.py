from typing import List
from collections.abc import Iterator

import pandas as pd


def prepare_data_for_insertion(excel_data_path: str) -> Iterator[List[dict]]:
    df = pd.read_excel(excel_data_path)
    records = df.to_dict(orient="records")
    initial_index = 0
    for i in range(len(records)):
        if records[i]["host_name"] != records[initial_index]["host_name"]:
            yield records[initial_index:i]
            initial_index = i
    yield records[initial_index:len(records)]
