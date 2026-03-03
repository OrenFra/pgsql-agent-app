from datetime import datetime
from tortoise import run_async

from data_insertion import insert_data
from db_connect import init
from models import *
import logging

from prepare_data_for_insertion import prepare_data_for_insertion
from filesystem_data_generator import FILE_PATH

# logging.basicConfig(level=logging.DEBUG)
#
# # This enables SQL logging from Tortoise
# logger = logging.getLogger("tortoise")
# logger.setLevel(logging.DEBUG)


async def run():
    # projects = await Project.all()
    # for p in projects:
    #     print(p.id, p.name)
    #
    # entities = await Entity.all()
    # for entity in entities:
    #     print(entity)
    #     print(await entity.project)
    #
    # dir_records = await DirRecord.all()
    # print(dir_records)
    #
    # dir_records_metadata = await DirRecordMetadata.all()
    # print(dir_records_metadata)

    # entity = await Entity.create(host_name="pc 1", project_id=1)
    # print(entity)

    # dir_record = await DirRecord.create(entity_id=8, path="a.b.c", raw_path=r"a\b\c")
    # print(dir_record.id, dir_record.entity_id, dir_record.path, dir_record.raw_path)
    #
    # now = datetime.now()
    # dir_record_metadata = await DirRecordMetadata.create(entity_id=1, dir_record_id=65, creation_time=now,
    #                                                      last_updated=now, state_timestamp=now)
    # print(dir_record_metadata)
    await init()
    start = datetime.now()
    for entity_dir in prepare_data_for_insertion(FILE_PATH):
        await insert_data(entity_dir, 2)
    end = datetime.now()
    print(end-start)


run_async(run())
