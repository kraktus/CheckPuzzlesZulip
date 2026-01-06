#!/usr/bin/env python3
"""
Migration script to migrate a SQLite database from peewee schema to sqlmodel schema.

This script:
1. Reads data from the old peewee database
2. Creates a new database with sqlmodel schema
3. Migrates all data from old to new database
4. Creates a backup of the old database

Usage:
    python migrate_peewee_to_sqlmodel.py <path_to_old_db>

Example:
    python migrate_peewee_to_sqlmodel.py puzzle_reports.db
"""

import sys
import sqlite3
import shutil
from pathlib import Path
from datetime import datetime


def migrate_database(old_db_path: str) -> None:
    """Migrate database from peewee to sqlmodel schema"""
    
    old_db_path = Path(old_db_path)
    if not old_db_path.exists():
        print(f"Error: Database file '{old_db_path}' does not exist")
        sys.exit(1)
    
    # Create backup
    backup_path = old_db_path.with_suffix(f'.backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}.db')
    print(f"Creating backup: {backup_path}")
    shutil.copy2(old_db_path, backup_path)
    
    # Connect to old database
    print(f"Reading from old database: {old_db_path}")
    old_conn = sqlite3.connect(old_db_path)
    old_conn.row_factory = sqlite3.Row
    old_cursor = old_conn.cursor()
    
    # Read old data
    print("Reading PuzzleReport data...")
    old_cursor.execute("SELECT * FROM puzzlereport")
    puzzle_reports = [dict(row) for row in old_cursor.fetchall()]
    print(f"Found {len(puzzle_reports)} puzzle reports")
    
    print("Reading Puzzle data...")
    old_cursor.execute("SELECT * FROM puzzle")
    puzzles = [dict(row) for row in old_cursor.fetchall()]
    print(f"Found {len(puzzles)} puzzles")
    
    old_conn.close()
    
    # Create new database with sqlmodel schema
    new_db_path = old_db_path.with_suffix('.new.db')
    print(f"Creating new database: {new_db_path}")
    
    new_conn = sqlite3.connect(new_db_path)
    new_cursor = new_conn.cursor()
    
    # Create tables with new schema
    print("Creating new schema...")
    new_cursor.execute("""
        CREATE TABLE IF NOT EXISTS puzzlereport (
            zulip_message_id TEXT PRIMARY KEY NOT NULL,
            reporter TEXT NOT NULL,
            puzzle_id TEXT NOT NULL,
            report_version INTEGER NOT NULL,
            sf_version TEXT NOT NULL,
            move INTEGER NOT NULL,
            details TEXT NOT NULL,
            checked INTEGER NOT NULL DEFAULT 0,
            local_evaluation TEXT NOT NULL,
            issues INTEGER NOT NULL DEFAULT 0
        )
    """)
    
    new_cursor.execute("""
        CREATE TABLE IF NOT EXISTS puzzle (
            _id TEXT PRIMARY KEY NOT NULL,
            initialPly INTEGER,
            solution TEXT,
            themes TEXT,
            game_pgn TEXT,
            status INTEGER NOT NULL DEFAULT 0
        )
    """)
    
    # Migrate PuzzleReport data
    print("Migrating puzzle reports...")
    for report in puzzle_reports:
        # Convert zulip_message_id to string if it's not already
        zulip_id = str(report['zulip_message_id'])
        
        new_cursor.execute("""
            INSERT INTO puzzlereport (
                zulip_message_id, reporter, puzzle_id, report_version,
                sf_version, move, details, checked, local_evaluation, issues
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            zulip_id,
            report['reporter'],
            report['puzzle_id'],
            report['report_version'],
            report.get('sf_version', ''),
            report['move'],
            report['details'],
            1 if report['checked'] else 0,
            report['local_evaluation'],
            report['issues']
        ))
    
    # Migrate Puzzle data
    print("Migrating puzzles...")
    for puzzle in puzzles:
        new_cursor.execute("""
            INSERT INTO puzzle (
                _id, initialPly, solution, themes, game_pgn, status
            ) VALUES (?, ?, ?, ?, ?, ?)
        """, (
            puzzle['_id'],
            puzzle['initialPly'],
            puzzle['solution'],
            puzzle['themes'],
            puzzle['game_pgn'],
            puzzle['status']
        ))
    
    new_conn.commit()
    new_conn.close()
    
    # Replace old database with new one
    print(f"Replacing old database with new schema...")
    old_db_path.unlink()
    new_db_path.rename(old_db_path)
    
    print(f"Migration complete!")
    print(f"Original database backed up to: {backup_path}")
    print(f"New database: {old_db_path}")


def main():
    if len(sys.argv) != 2:
        print("Usage: python migrate_peewee_to_sqlmodel.py <path_to_database>")
        print("Example: python migrate_peewee_to_sqlmodel.py puzzle_reports.db")
        sys.exit(1)
    
    db_path = sys.argv[1]
    migrate_database(db_path)


if __name__ == "__main__":
    main()
