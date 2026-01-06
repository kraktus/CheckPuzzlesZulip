# Database Migration: Peewee to SQLModel

This directory contains migration scripts for transitioning the database from peewee to sqlmodel.

## Migration Script

### `migrate_peewee_to_sqlmodel.py`

This script migrates an existing SQLite database from the old peewee schema to the new sqlmodel schema.

#### What it does:

1. Creates a backup of the original database with a timestamp
2. Reads all data from the old database using peewee models (PuzzleReport and Puzzle tables)
3. Creates a new database with the sqlmodel schema
4. Migrates all data using sqlmodel models, converting field types as needed:
   - `zulip_message_id`: Converted from integer to string (primary key)
   - All boolean fields stored as integers (0/1)
   - Bitfield values preserved as integers
5. Replaces the old database with the migrated version

#### Installation:

First, install the migration dependencies (includes peewee):

```bash
uv sync --group migration
```

#### Usage:

```bash
uv run --group migration python migrations/migrate_peewee_to_sqlmodel.py <path_to_database>
```

#### Example:

```bash
# Migrate the main database
uv run --group migration python migrations/migrate_peewee_to_sqlmodel.py puzzle_reports.db
```

#### Safety:

- The script creates a timestamped backup before making any changes
- The backup is saved in the same directory with the format: `<original_name>.backup_YYYYMMDD_HHMMSS.db`
- If something goes wrong, you can restore from the backup

#### Implementation Details:

- **Reading**: Uses peewee models to read from the old database (cleaner than raw SQL)
- **Writing**: Uses sqlmodel models to write to the new database
- **Type Safety**: Both reading and writing benefit from ORM type checking

#### Schema Changes:

**PuzzleReport table:**
- `zulip_message_id`: Now TEXT (was INTEGER) - serves as primary key
- `checked`: Now stored as INTEGER (0 or 1)
- `issues`: Bitfield stored as INTEGER
  - Bit 1: has_multiple_solutions
  - Bit 2: has_missing_mate_theme
  - Bit 4: is_deleted_from_lichess

**Puzzle table:**
- `status`: Bitfield stored as INTEGER
  - Bit 1: is_deleted

All other fields remain the same type and structure.

## Notes

- The migration is one-way: it converts from peewee to sqlmodel schema
- After migration, the application code uses sqlmodel exclusively
- The migration preserves all data integrity and relationships
- Peewee is only required for running the migration script, not for normal application use
