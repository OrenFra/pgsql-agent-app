import asyncio
from typing import List

from models import *
from db_connect import init

from datetime import datetime


async def get_dir_state(entity_id: int, father_path: str,
                        state: int) -> List[
    tuple]:  # state is an integer - 0 is the most recent state, 1 is the one before it...
    path_query = f"{father_path}.*" + "{1}" if father_path else "*{1}"
    records = await DirRecord.raw(f"""
    SELECT * FROM dir_records
    WHERE entity_id={entity_id} and path ~ '{path_query}'
    """)

    records_metadata = await DirRecordMetadata.filter(entity_id=entity_id,
                                                      dir_record_id__in=[record.id for record in records])
    current_state_records = []

    # option 1 - not sorting and searching for each record. Time complexity - O(n^2)
    # for record in records:
    #     current_record_metadata = list(filter(lambda metadata: metadata.dir_record_id == record.id, records_metadata))
    #     if len(current_record_metadata) > 1:
    #         current_record_metadata.sort(key=lambda metadata: metadata.state_timestamp.timestamp(), reverse=True)
    #     current_state_records.append((record,
    #                                   current_record_metadata[state] if state < len(current_record_metadata) else
    #                                   current_record_metadata[-1]))

    # option 2 - with sorting everything according to the timestamp and the id. Time complexity - O(n log n)
    # records.sort(key=lambda record: record.id)
    # records_metadata.sort(key=lambda
    #     record_metadata: record_metadata.state_timestamp.timestamp() if record_metadata.state_timestamp else 0,
    #                       reverse=True)
    # records_metadata.sort(key=lambda record_metadata: record_metadata.dir_record_id)
    # j = 0
    # for i in range(len(records)):
    #     initial_index = j
    #     while j < len(records_metadata) and records_metadata[j].dir_record_id == records[i].id:
    #         j += 1
    #     current_record_metadata = records_metadata[initial_index:j]
    #     current_state_records.append((records[i],
    #                                   current_record_metadata[state] if state < len(current_record_metadata) else
    #                                   current_record_metadata[-1]))

    # option 3 - with dictionary. Time complexity - O(n)
    current_state_records_dict = {}
    for record in records:
        current_state_records_dict[record.id] = {"record": record, "metadata": []}

    for metadata in records_metadata:
        current_state_records_dict[metadata.dir_record_id]["metadata"].append(metadata)

    for key in current_state_records_dict.keys():
        if len(current_state_records_dict[key]["metadata"]) > 1:
            current_state_records_dict[key]["metadata"].sort(key=lambda metadata: metadata.state_timestamp.timestamp(),
                                                             reverse=True)

    for key in current_state_records_dict.keys():
        current_record = current_state_records_dict[key]
        current_state_records.append((current_record["record"],
                                      current_record["metadata"][state] if state < len(
                                          current_record["metadata"]) else
                                      current_record["metadata"][-1]))

    return current_state_records


async def main():
    await init()
    before = datetime.now()
    last_state_records = await get_dir_state(29, "686f6d65.75736572.646f63756d656e747321.666f6c6465725f3023", 0)
    former_state_records = await get_dir_state(29, "686f6d65.75736572.646f63756d656e747321.666f6c6465725f3023", 1)
    after = datetime.now()
    print(after - before)
    for i in range(len(last_state_records)):
        print(last_state_records[i])


asyncio.run(main())
