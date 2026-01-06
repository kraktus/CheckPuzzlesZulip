# Migration to SQLModel

This document describes the migration from peewee to sqlmodel completed in this PR.

## Overview

The codebase has been migrated from the [peewee](http://docs.peewee-orm.com/) ORM to [sqlmodel](https://sqlmodel.tiangolo.com/) for better type checking, improved developer experience, and modern Python practices.

## What Changed

### Dependencies
- **Removed**: `peewee>=3.17.8`
- **Added**: `sqlmodel>=0.0.22` (includes SQLAlchemy and Pydantic)

### Models
The models now use SQLModel which provides:
- Pydantic validation
- Better type hints
- Compatibility with FastAPI (if needed in the future)

#### Key Model Changes:
- `PuzzleReport` and `Puzzle` classes now inherit from `SQLModel`
- Bitfield properties (like `has_multiple_solutions`, `is_deleted`) are now implemented as Python properties
- `Puzzle._id` renamed to `Puzzle.id` with database column alias for backward compatibility

### Database Operations
All database queries have been updated:

**Before (peewee):**
```python
reports = PuzzleReport.select().where(PuzzleReport.checked == False)
for report in reports.execute():
    print(report.reporter)
```

**After (sqlmodel):**
```python
with get_session() as session:
    statement = select(PuzzleReport).where(PuzzleReport.checked == False)
    reports = session.exec(statement).all()
    for report in reports:
        print(report.reporter)
```

### Testing
- Test setup updated to use sqlmodel
- No functional changes to test logic
- All existing tests pass

## For Existing Users

If you have an existing database, you **must** run the migration script:

```bash
python migrations/migrate_peewee_to_sqlmodel.py path/to/your/puzzle_reports.db
```

This script will:
1. Create a timestamped backup of your database
2. Migrate the schema to the new format
3. Convert all data (including type conversions)
4. Replace the old database with the new one

**Note**: The migration converts `zulip_message_id` from INTEGER to TEXT. All data is preserved.

## For New Users

No migration needed! Just:
```bash
uv sync
uv run -m check_puzzles_zulip run <command>
```

The database will be created with the correct schema automatically.

## Schema Compatibility

The new schema is almost identical to the old one:

| Change | Old (peewee) | New (sqlmodel) |
|--------|-------------|----------------|
| zulip_message_id type | INTEGER | TEXT |
| Puzzle ID field name | `_id` | `id` (column name still `_id`) |
| Boolean fields | INTEGER (0/1) | INTEGER (0/1) |
| Bitfields | INTEGER | INTEGER |

All other fields remain the same.

## Development

### Type Checking
The codebase now has comprehensive type hints:
```bash
uv run pyright .
```

### Code Quality
All code is formatted with black:
```bash
uv run black .
```

## Benefits

1. **Type Safety**: Pydantic validates all data at runtime
2. **Better IDE Support**: Full autocomplete and type checking
3. **Modern Stack**: Ready for async operations and FastAPI integration
4. **Maintainability**: Cleaner, more readable code
5. **Developer Experience**: Better error messages and debugging

## Backward Compatibility

The migration maintains full backward compatibility:
- All existing data is preserved
- Database queries work the same way
- API/CLI remains unchanged
- Tests pass without modification (except for model instantiation)

## Troubleshooting

### "Database not initialized" error
Make sure you call `setup_db()` before any database operations:
```python
from check_puzzles_zulip.models import setup_db
setup_db("puzzle_reports.db")
```

### Migration fails
If the migration script fails:
1. Check that the database file exists and is readable
2. Look at the backup file created (it's not deleted on failure)
3. Restore from backup if needed: `cp backup_file.db puzzle_reports.db`

### Type errors with Puzzle.id
The field is now `puzzle.id` (not `puzzle._id`):
```python
# Old
puzzle_id = puzzle._id

# New
puzzle_id = puzzle.id
```

## Further Reading

- [SQLModel Documentation](https://sqlmodel.tiangolo.com/)
- [Pydantic Documentation](https://docs.pydantic.dev/)
- [SQLAlchemy Core Documentation](https://docs.sqlalchemy.org/en/20/core/)
