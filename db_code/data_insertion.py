from typing import List

from dateutil import parser
import pandas as pd
import tortoise.exceptions
from tortoise import Tortoise, run_async
from models import *
from path_encode import encode_path, get_raw_sub_path


# every call to the function is with records from 1 entity. The connection to the project must be specified.
# this function expects all the times to be strings representing timezone aware datetime objects
async def insert_data(records: List[dict], project_id: int) -> None:
    await check_partition(records[0], project_id)

    entity = await Entity.get(project_id=project_id, host_name=records[0]["host_name"])
    entity_id = entity.id
    del entity
    unique_fathers = set()
    for record in records:
        record["raw_path"] = record["path"]
        record["path"] = encode_path(record["path"])
        record["entity_id"] = entity_id
        add_to_unique_fathers(record["path"], record["raw_path"], record["entity_id"], unique_fathers)
        await insert_record(record)

    for record in records:
        if (record["path"], record["raw_path"], record["entity_id"]) in unique_fathers:
            unique_fathers.remove((record["path"], record["raw_path"], record["entity_id"]))

    await insert_missing_father_records(list(unique_fathers))


def add_to_unique_fathers(path: str, raw_path: str, entity_id: int, unique_fathers: set) -> None:
    father = ""
    for label in path.split('.')[:-1]:
        father += f".{label}" if father else label
        raw_father = get_raw_sub_path(father, raw_path)
        unique_fathers.add((father, raw_father, entity_id))


async def insert_record(record: dict) -> None:
    try:
        dir_record, was_created = await DirRecord.get_or_create(
            defaults={"entity_id": record["entity_id"], "path": record["path"], "raw_path": record["raw_path"]},
            entity_id=record["entity_id"], path=record["path"])
    except tortoise.exceptions.IntegrityError as e:
        print(e)
        dir_record = await DirRecord.get(entity_id=record["entity_id"], path=record["path"])
        was_created = False

    if was_created:
        await insert_record_metadata(record, dir_record.id)
    else:
        metadata_list = await DirRecordMetadata.filter(entity_id=record["entity_id"],
                                                       dir_record_id=dir_record.id)
        if len(metadata_list) == 1:
            if metadata_list[0].state_timestamp is None:
                await metadata_list[0].delete()
            await insert_record_metadata(record, dir_record.id)
        else:
            metadata_list.sort(key=lambda metadata: metadata.state_timestamp.timestamp(), reverse=True)
            if parser.parse(record["state_timestamp"]) > metadata_list[-1].state_timestamp:
                await metadata_list[-1].delete()
                await insert_record_metadata(record, dir_record.id)


async def insert_record_metadata(record: dict, dir_record_id: int) -> None:
    await DirRecordMetadata.create(entity_id=record["entity_id"], dir_record_id=dir_record_id,
                                   creation_time=parser.parse(record["creation_time"]),
                                   last_updated=parser.parse(record["last_updated"]),
                                   state_timestamp=parser.parse(record["state_timestamp"]))


async def insert_missing_father_records(records: List[tuple]) -> None:
    for record in records:
        try:
            dir_record, was_created = await DirRecord.get_or_create(
                defaults={"path": record[0], "raw_path": record[1], "entity_id": record[2]}, entity_id=record[2],
                path=record[0])
        except tortoise.exceptions.IntegrityError as e:
            print(e)
            was_created = False

        if was_created:
            await DirRecordMetadata.create(entity_id=record[2], dir_record_id=dir_record.id)


async def check_partition(row: dict, project_id: int) -> None:
    try:
        entity = await Entity.filter(host_name=row["host_name"]).first()
        if not entity:
            entity = await Entity.create(host_name=row["host_name"], project_id=project_id)

            conn = Tortoise.get_connection("default")
            await conn.execute_script(f"""
                CREATE TABLE public.dir_records_{entity.id}
                PARTITION OF public.dir_records
                FOR VALUES IN ({entity.id});
                
                CREATE INDEX dir_records_{entity.id}_path_gist
                ON public.dir_records_{entity.id}
                USING GIST (path);
                
                
                CREATE TABLE public.dir_records_metadata_{entity.id}
                PARTITION OF public.dir_records_metadata
                FOR VALUES IN ({entity.id});""")
    except (tortoise.exceptions.OperationalError, tortoise.exceptions.IntegrityError) as e:
        print(e)
