# Filesystem database schema reference

This file summarizes the core tables, their meaning and relationships in the database.

## Overview

The database models filesystem paths and their metadata across multiple computers (*called entities*) divided to
different projects.

- A **project** represents a logical grouping of computers.
- An **entity** represents a single computer (host) that belongs to a project.
- A **dir record** represents individual filesystem path of a computer(entity).
- A **dir record metadata** represents metadata of a specific path.

Some tables are partitioned by `entity_id`. Avoid unfiltered scans of these partitioned tables; always filter
by `entity_id` if possible.

## Tables

### `projects`

- **Purpose**: Catalog of all projects.
- **Key columns**:
    - `id`: Primary key.
    - `name`: Human‑readable project name.

### `entities`

- **Purpose**: Catalog of all computers (entities).
- **Key columns**:
    - `id`: Primary key.
    - `host_name`: Host/computer name.
    - `project_id`: Foreign key referencing `projects.id`.

### `dir_records`

- **Purpose**: Records representing filesystem paths of the entities. The records can represent filesystem files and
  directories. The filesystems can be windows or non-windows.
- **Partitioning**: Partitioned by `entity_id`.
- **Key columns**:
    - `id`: Primary key.
    - `entity_id`: Foreign key referencing `entities.id`. The entity that this path belongs to.
    - `raw_path`: The actual filesystem path string (for example, `C:\\temp`).
    - `path`: Encoded path stored as an `ltree` datatype for efficient hierarchical path queries.

### `dir_records_metadata`

- **Purpose**: Metadata for each filesystem path (for reach dir_record).
- **Partitioning**: Partitioned by `entity_id`.
- **Key columns**:
    - `id`: Primary key.
    - `entity_id`: Foreign key referencing `entities.id`. The entity that this path metadata belongs to.
    - `dir_record_id`: Foreign key referencing `dir_records.id` (the path this metadata describes).
    - `creation_time`: File or directory creation timestamp.
    - `last_updated`: Last modification timestamp.
    - `base_name`: File or directory base name.
    - `file_extension`: File extension, if present.

## Relationship summary

- `projects` ←→ `entities`
    - `entities.project_id` → `projects.id`
    - Each entity belongs to exactly one project.

- `entities` ←→ `dir_records`
    - `dir_records.entity_id` → `entities.id`
    - Each directory record belongs to exactly one entity (computer).

- `entities` ←→ `dir_records_metadata`
    - `dir_records_metadata.entity_id` → `entities.id`
    - Each metadata record belongs to exactly one entity (computer).

- `dir_records` ←→ `dir_records_metadata`
    - `dir_records_metadata.dir_record_id` → `dir_records.id`
    - Each metadata record describes exactly one directory record (path).
