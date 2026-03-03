"""
Insert dir_record and dir_record_metadata with generated (fake) paths.

Generates synthetic paths per entity/computer and inserts ~1000 records each.
No real filesystem access.

Run from db_code directory:
  cd db_code && python -m insert_from_filesystem
"""

import asyncio
import random
from datetime import datetime, timedelta, timezone

import tortoise.exceptions
from tortoise import Tortoise

from db_connect import init as init_db
from models import DirRecord, DirRecordMetadata, Entity, Project
from path_encode import encode_path, get_raw_sub_path

# Host names (computers); each gets unique generated paths
ENTITY_NAMES: list[str] = ["pc1", "pc2", "pc3", "pc4", "pc5"]

RECORDS_PER_ENTITY = 1000
PROJECT_NAME = "filesystem_scan"

# Path generation config: different root patterns per entity (no real FS access)
PATH_ROOTS_WINDOWS = [
    r"c:\users\user\Documents",
    r"c:\users\user\Downloads",
    r"c:\projects\workspace",
    r"c:\data\exports",
    r"c:\apps\config",
]
PATH_ROOTS_UNIX = [
    "/home/user/documents",
    "/home/user/projects",
    "/var/data",
    "/opt/apps",
    "/tmp/work",
]
FILE_EXTENSIONS = [".txt", ".json", ".py", ".log", ".csv", ".xml", ".md", ".cfg", ".yml", ""]


def _ensure_path_length(path: str, max_len: int = 255) -> str:
    """Truncate path if too long for DB column."""
    if len(path) <= max_len:
        return path
    return path[: max_len - 3] + "..."


def _parse_base_name_and_extension(raw_path: str) -> tuple[str, str]:
    """Extract base_name and file_extension from path."""
    import os

    name = os.path.basename(raw_path)
    if "." in name and not name.startswith("."):
        base, ext = name.rsplit(".", 1)
        return base[:255], ("." + ext)[:255]
    return (name[:255] if name else "unnamed"), ""


def _add_to_unique_fathers(path: str, raw_path: str, entity_id: int, unique_fathers: set) -> None:
    """Collect parent paths that must exist (from path_encode.add_to_unique_fathers)."""
    father = ""
    for label in path.split(".")[:-1]:
        father += f".{label}" if father else label
        raw_father = get_raw_sub_path(father, raw_path)
        unique_fathers.add((father, raw_father, entity_id))


def generate_paths_for_entity(host_name: str, limit: int) -> list[tuple[str, datetime, datetime]]:
    """
    Generate synthetic (raw_path, creation_time, last_updated) for one entity.
    Each entity gets different path prefixes. Returns list of (raw_path, creation_time, last_updated).
    """
    result: list[tuple[str, datetime, datetime]] = []
    base_time = datetime.now(tz=timezone.utc)
    entity_idx = hash(host_name) % (len(PATH_ROOTS_WINDOWS) + len(PATH_ROOTS_UNIX))
    roots = PATH_ROOTS_WINDOWS + PATH_ROOTS_UNIX
    root = roots[entity_idx % len(roots)]
    use_windows = "\\" in root or (len(root) > 0 and root[0].islower())
    sep = "\\" if use_windows else "/"

    for i in range(limit):
        depth = (i % 4) + 1
        parts = [root]
        for d in range(depth):
            parts.append(f"folder_{i // (100 ** (d + 1)) % 100}")
        ext = FILE_EXTENSIONS[i % len(FILE_EXTENSIONS)]
        fname = f"file_{i}{ext}" if ext else f"dir_{i}"
        parts.append(fname)
        raw_path = sep.join(parts)

        creation = base_time - timedelta(days=random.randint(0, 365), seconds=random.randint(0, 86400))
        last_updated = creation + timedelta(minutes=random.randint(0, 1000))
        result.append((raw_path, creation, last_updated))

    return result


async def ensure_partition(host_name: str, project_id: int) -> Entity:
    """Get or create entity and its partition tables."""
    entity = await Entity.filter(host_name=host_name, project_id=project_id).first()
    if not entity:
        entity = await Entity.create(host_name=host_name, project_id=project_id)
        conn = Tortoise.get_connection("default")
        await conn.execute_script(
            f"""
            CREATE TABLE IF NOT EXISTS public.dir_records_{entity.id}
            PARTITION OF public.dir_records
            FOR VALUES IN ({entity.id});

            CREATE INDEX IF NOT EXISTS dir_records_{entity.id}_path_gist
            ON public.dir_records_{entity.id}
            USING GIST (path);

            CREATE TABLE IF NOT EXISTS public.dir_records_metadata_{entity.id}
            PARTITION OF public.dir_records_metadata
            FOR VALUES IN ({entity.id});
            """
        )
    return entity


async def insert_record_with_metadata(
    entity_id: int,
    raw_path: str,
    creation_time: datetime | None,
    last_updated: datetime | None,
    base_name: str,
    file_extension: str,
) -> None:
    """Insert a single DirRecord and DirRecordMetadata."""
    path = encode_path(raw_path)
    raw_path_safe = _ensure_path_length(raw_path)
    path_safe = _ensure_path_length(path)

    try:
        dir_record, created = await DirRecord.get_or_create(
            entity_id=entity_id,
            path=path_safe,
            defaults={"raw_path": raw_path_safe},
        )
    except tortoise.exceptions.IntegrityError:
        dir_record = await DirRecord.get(entity_id=entity_id, path=path_safe)
        created = False

    if created:
        await DirRecordMetadata.create(
            entity_id=entity_id,
            dir_record_id=dir_record.id,
            creation_time=creation_time,
            last_updated=last_updated,
            base_name=base_name,
            file_extension=file_extension,
        )


async def insert_missing_father_records(
    unique_fathers: list[tuple[str, str, int]],
) -> None:
    """Insert parent DirRecords and minimal metadata (for path hierarchy)."""
    for path_enc, raw_path, entity_id in unique_fathers:
        path_safe = _ensure_path_length(path_enc)
        raw_safe = _ensure_path_length(raw_path)
        base_name, file_extension = _parse_base_name_and_extension(raw_path)

        try:
            dir_record, created = await DirRecord.get_or_create(
                entity_id=entity_id,
                path=path_safe,
                defaults={"raw_path": raw_safe},
            )
        except tortoise.exceptions.IntegrityError:
            dir_record = await DirRecord.get(entity_id=entity_id, path=path_safe)
            created = False

        if created:
            await DirRecordMetadata.create(
                entity_id=entity_id,
                dir_record_id=dir_record.id,
                creation_time=None,
                last_updated=None,
                base_name=base_name,
                file_extension=file_extension,
            )


async def insert_entity_paths(host_name: str, project_id: int) -> int:
    """Insert ~RECORDS_PER_ENTITY generated paths for one entity. Returns count inserted."""
    entity = await ensure_partition(host_name, project_id)
    entity_id = entity.id

    paths_data = generate_paths_for_entity(host_name, RECORDS_PER_ENTITY)
    unique_fathers: set[tuple[str, str, int]] = set()
    records: list[tuple[str, datetime, datetime]] = []

    for raw_path, creation_time, last_updated in paths_data:
        path_enc = encode_path(raw_path)
        path_safe = _ensure_path_length(path_enc)
        raw_safe = _ensure_path_length(raw_path)
        _add_to_unique_fathers(path_safe, raw_safe, entity_id, unique_fathers)
        records.append((raw_path, creation_time, last_updated))

    for raw_path, _, _ in records:
        path_enc = encode_path(raw_path)
        path_safe = _ensure_path_length(path_enc)
        raw_safe = _ensure_path_length(raw_path)
        unique_fathers.discard((path_safe, raw_safe, entity_id))

    await insert_missing_father_records(list(unique_fathers))

    inserted = 0
    for raw_path, creation_time, last_updated in records:
        base_name, file_extension = _parse_base_name_and_extension(raw_path)
        try:
            await insert_record_with_metadata(
                entity_id=entity_id,
                raw_path=raw_path,
                creation_time=creation_time,
                last_updated=last_updated,
                base_name=base_name,
                file_extension=file_extension,
            )
            inserted += 1
        except Exception as e:
            print(f"  Skip {raw_path[:60]}...: {e}")

    return inserted


async def main() -> None:
    """Run the insertion for all configured entities."""
    await init_db()

    project, _ = await Project.get_or_create(name=PROJECT_NAME)

    for host_name in ENTITY_NAMES:
        print(f"Inserting generated paths for {host_name}...")
        n = await insert_entity_paths(host_name, project.id)
        print(f"  Inserted {n} records for {host_name}")

    await Tortoise.close_connections()
    print("Done.")


if __name__ == "__main__":
    asyncio.run(main())