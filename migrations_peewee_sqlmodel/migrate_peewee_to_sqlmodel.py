#!/usr/bin/env python3
"""
Migration script to migrate a SQLite database from peewee schema to sqlmodel schema.

This script:
1. Reads data from the old peewee database using peewee models
2. Creates a new database with sqlmodel schema
3. Migrates all data from old to new database using sqlmodel models
4. Creates a backup of the old database

Usage:
    python migrate_peewee_to_sqlmodel.py <path_to_old_db>

Example:
    python migrate_peewee_to_sqlmodel.py puzzle_reports.db
"""

import sys
import shutil
from pathlib import Path
from datetime import datetime

# Import peewee for reading old database
from peewee import (
    Model,
    FixedCharField,
    CharField,
    IntegerField,
    TextField,
    BooleanField,
    BitField,
    SqliteDatabase,
)

# Import sqlmodel for writing new database
import sys
from sqlmodel import Session

sys.path.insert(0, str(Path(__file__).parent.parent))
from check_puzzles_zulip.models import (
    setup_db as setup_sqlmodel_db,
    PuzzleReport as SQLModelPuzzleReport,
    Puzzle as SQLModelPuzzle,
)

# Peewee models for reading old database
old_db = SqliteDatabase(None)


class PeeweeBaseModel(Model):
    class Meta:
        database = old_db


class PeeweePuzzleReport(PeeweeBaseModel):
    zulip_message_id = CharField(primary_key=True)
    reporter = CharField()
    puzzle_id = FixedCharField(5)
    report_version = IntegerField()
    sf_version = CharField()
    move = IntegerField()
    details = TextField()
    checked = BooleanField(default=False)
    local_evaluation = TextField()
    issues = BitField()
    has_multiple_solutions = issues.flag(1)
    has_missing_mate_theme = issues.flag(2)
    is_deleted_from_lichess = issues.flag(4)

    class Meta:
        table_name = "puzzlereport"


class PeeweePuzzle(PeeweeBaseModel):
    _id = FixedCharField(5, primary_key=True)
    initialPly = IntegerField(null=True)
    solution = CharField(null=True)
    themes = TextField(null=True)
    game_pgn = TextField(null=True)
    status = BitField()
    is_deleted = status.flag(1)

    class Meta:
        table_name = "puzzle"


def migrate_database(old_db_path: str) -> None:
    """Migrate database from peewee to sqlmodel schema"""

    old_db_path = Path(old_db_path)
    if not old_db_path.exists():
        print(f"Error: Database file '{old_db_path}' does not exist")
        sys.exit(1)

    # Create backup
    backup_path = old_db_path.with_suffix(
        f'.backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}.db'
    )
    print(f"Creating backup: {backup_path}")
    shutil.copy2(old_db_path, backup_path)

    # Connect to old database with peewee
    print(f"Reading from old database: {old_db_path}")
    old_db.init(str(old_db_path))
    old_db.connect()

    # Read old data using peewee models
    print("Reading PuzzleReport data...")
    old_reports = list(PeeweePuzzleReport.select())
    print(f"Found {len(old_reports)} puzzle reports")

    print("Reading Puzzle data...")
    old_puzzles = list(PeeweePuzzle.select())
    print(f"Found {len(old_puzzles)} puzzles")

    old_db.close()

    # Create new database with sqlmodel
    new_db_path = old_db_path.with_suffix(".new.db")
    print(f"Creating new database: {new_db_path}")
    new_engine = setup_sqlmodel_db(str(new_db_path))

    # Migrate data using sqlmodel
    print("Migrating puzzle reports...")

    with Session(new_engine) as session:
        for old_report in old_reports:
            # Convert bitfield issues to datetime fields
            has_multiple_solutions = (
                datetime.now() if old_report.has_multiple_solutions else None
            )
            has_missing_mate_theme = (
                datetime.now() if old_report.has_missing_mate_theme else None
            )
            is_deleted_from_lichess = (
                datetime.now() if old_report.is_deleted_from_lichess else None
            )
            checked_at = datetime.now() if old_report.checked else None

            new_report = SQLModelPuzzleReport(
                zulip_message_id=str(old_report.zulip_message_id),
                reporter=old_report.reporter,
                puzzle_id=old_report.puzzle_id,
                report_version=old_report.report_version,
                sf_version=old_report.sf_version or "",
                move=old_report.move,
                details=old_report.details,
                checked_at=checked_at,
                local_evaluation=old_report.local_evaluation or "",
                has_multiple_solutions=has_multiple_solutions,
                has_missing_mate_theme=has_missing_mate_theme,
                is_deleted_from_lichess=is_deleted_from_lichess,
            )
            session.add(new_report)
        session.commit()

    print("Migrating puzzles...")
    with Session(new_engine) as session:
        for old_puzzle in old_puzzles:
            # Convert status bitfield to deleted_at datetime
            deleted_at = datetime.now() if old_puzzle.is_deleted else None

            new_puzzle = SQLModelPuzzle(
                lichess_id=old_puzzle._id,
                initialPly=old_puzzle.initialPly,
                solution=old_puzzle.solution,
                themes=old_puzzle.themes,
                game_pgn=old_puzzle.game_pgn,
                deleted_at=deleted_at,
            )
            session.add(new_puzzle)
        session.commit()

    print(f"Migration complete!")
    print(f"Original database backed up to: {backup_path}")
    print(f"New database: {new_db_path}")


def main():
    if len(sys.argv) != 2:
        print("Usage: python migrate_peewee_to_sqlmodel.py <path_to_database>")
        print("Example: python migrate_peewee_to_sqlmodel.py puzzle_reports.db")
        sys.exit(1)

    db_path = sys.argv[1]
    migrate_database(db_path)


if __name__ == "__main__":
    main()
