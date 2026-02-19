#!/usr/local/bin/python3
# coding: utf-8
# Licence: GNU AGPLv3

""""""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import logging.handlers
import os
import sys
import time


import chess
import chess.engine

from sqlmodel import select, func, or_, Session, col
from sqlalchemy.engine import Engine
from argparse import RawTextHelpFormatter
from collections import deque
from dataclasses import dataclass
from datetime import datetime, timedelta
from itertools import groupby
from operator import attrgetter
from pathlib import Path

from typing import Optional, List, Union, Tuple, Dict, Callable, Any

from .check import Checker
from .config import setup_logger, ZULIPRC, STOCKFISH
from .lichess import is_puzzle_deleted, _fetch_puzzle
from .models import setup_db, PuzzleReport, Puzzle
from .zulip import ZulipClient
from .util import utc_now

log = setup_logger(__file__)

###########
# Classes #
###########


def doc(dic: Dict[str, Callable[..., Any]]) -> str:
    """Produce documentation for every command based on doc of each function"""
    doc_string = ""
    for name_cmd, func in dic.items():
        doc_string += f"{name_cmd}: {func.__doc__}\n\n"
    return doc_string


def fetch_reports(engine: Engine) -> None:

    client = ZulipClient(ZULIPRC)
    reports = client.get_puzzle_reports()

    inserted_count = 0
    with Session(engine) as session:
        for report in reports:
            # Check if report already exists
            statement = select(PuzzleReport).where(
                PuzzleReport.zulip_message_id == report.zulip_message_id
            )
            existing = session.exec(statement).first()
            if existing is None:
                session.add(report)
                inserted_count += 1
        session.commit()
    log.info(f"{inserted_count} new reports")


def mark_duplicate_reports(engine: Engine, zulip: ZulipClient) -> None:
    """Mark duplicate reports as checked"""
    with Session(engine) as session:
        statement = select(PuzzleReport)
        reports = list(session.exec(statement).all())

    # do everything in python for now
    grouped_reports = groupby(
        sorted(reports, key=attrgetter("puzzle_id", "move")),
        key=attrgetter("puzzle_id", "move"),
    )
    for key, group in grouped_reports:
        group_list = list(group)
        if len(group_list) > 1:
            unchecked_duplicates = []
            # mark all but the first as checked
            for report in group_list[1:]:
                if not report.is_checked():
                    log.debug(f"Marking report {report.zulip_message_id} as checked")
                    unchecked_duplicates.append(report.zulip_message_id)
            if unchecked_duplicates:
                log.debug(
                    f"Found {len(unchecked_duplicates)} duplicate reports for {key}"
                )
                for zulip_id in unchecked_duplicates:
                    zulip.react(zulip_id, "repeat")
                with Session(engine) as session:
                    for zulip_id in unchecked_duplicates:
                        statement = select(PuzzleReport).where(
                            PuzzleReport.zulip_message_id == zulip_id
                        )
                        report = session.exec(statement).first()
                        if report:
                            report.checked_at = utc_now()
                            session.add(report)
                    session.commit()


async def check_one_report(
    unchecked_report: PuzzleReport,
    zulip: ZulipClient,
    semaphore: asyncio.Semaphore,
    db_engine: Engine,
) -> None:
    async with semaphore:
        transport, chess_engine = await chess.engine.popen_uci(STOCKFISH)
        try:
            checker = Checker(chess_engine, db_engine)
            log.info(
                f"Checking report {unchecked_report}, {unchecked_report.puzzle_id}"
            )
            checked_report = await checker.check_report(unchecked_report)

            log.debug(
                f"Issues of {unchecked_report}, training/{checked_report.puzzle_id}: {checked_report.get_issues()}"
            )
            if checked_report.is_multiple_solutions_detected():
                zulip.react(checked_report.zulip_message_id, "check")
            if checked_report.is_missing_mate_theme_detected():
                zulip.react(checked_report.zulip_message_id, "price_tag")
            # no issue, it's a false positive
            if len(checked_report.get_issues()) == 0:
                zulip.react(checked_report.zulip_message_id, "cross_mark")

            # Save the report
            with Session(db_engine) as session:
                session.add(checked_report)
                session.commit()
        finally:
            await chess_engine.quit()


async def async_check_reports(engine: Engine, max_sf: int = 4) -> None:
    """Check the reports in the database"""

    zulip = ZulipClient(ZULIPRC)
    mark_duplicate_reports(engine, zulip)

    with Session(engine) as session:
        statement = select(PuzzleReport).where(col(PuzzleReport.checked_at).is_(None))
        unchecked_reports = list(session.exec(statement).all())

    log.info(f"Checking {len(unchecked_reports)} reports")
    semaphore = asyncio.Semaphore(max_sf)
    tasks = [
        asyncio.create_task(check_one_report(report, zulip, semaphore, engine))
        for report in unchecked_reports
    ]
    await asyncio.gather(*tasks)
    log.info("All reports checked")


def check_reports(engine: Engine) -> None:
    asyncio.run(async_check_reports(engine))


def export_reports(engine: Engine) -> None:
    """Export the puzzle ids with multiple solutions to a file"""
    with Session(engine) as session:
        # Query for reports with multiple solutions that are not deleted
        statement = (
            select(PuzzleReport)
            .join(Puzzle, col(Puzzle.lichess_id) == col(PuzzleReport.puzzle_id))
            # we only care about multiple solutions for exporting
            .where(col(PuzzleReport.has_multiple_solutions).is_not(None))
            .where(col(Puzzle.deleted_at).is_(None))
        )
        reports = list(session.exec(statement).all())

    with open("multiple_solutions.txt", "w") as f:
        for report in reports:
            print(report.debug_str())
            f.write(f"{report.puzzle_id}\n")
    log.info(f"Exported {len(reports)} reports to multiple_solutions.txt")


def reset_argparse(args, engine: Engine) -> None:
    """Reset all reports to unchecked"""
    with Session(engine) as session:
        statement = select(PuzzleReport).where(
            col(PuzzleReport.checked_at).is_not(None)
        )
        nb_reports = len(list(session.exec(statement).all()))

    confirm = input(f"Are you sure you want to reset {nb_reports} reports? [y/N] ")
    if confirm.lower() == "y":
        if args.reports_checked:
            with Session(engine) as session:
                statement = select(PuzzleReport).where(
                    col(PuzzleReport.checked_at).is_not(None)
                )
                reports = session.exec(statement).all()
                for report in reports:
                    report.checked = False
                    session.add(report)
                session.commit()
            log.info("All reports unchecked")
        if args.reactions:
            zu = ZulipClient(ZULIPRC)
            zu.unreact_all()


def stats(engine: Engine) -> None:
    """Print statistics about the reports in the database"""
    # most reporters
    reporter_limit = 20
    with Session(engine) as session:
        statement = (
            select(PuzzleReport.reporter, func.count())
            .group_by(PuzzleReport.reporter)
            .order_by(func.count().desc())
            .limit(reporter_limit)
        )
        results = session.exec(statement).all()

    print("-" * 10)
    print(f"Top {reporter_limit} reporters:")
    for reporter, count in results:
        print(f"{reporter}: {count}")

    # most reported puzzles
    puzzle_limit = 20
    with Session(engine) as session:
        statement = (
            select(PuzzleReport.puzzle_id, func.count())
            .group_by(PuzzleReport.puzzle_id)
            .order_by(func.count().desc())
            .limit(puzzle_limit)
        )
        results = session.exec(statement).all()

    print(f"Top {puzzle_limit} puzzles:")
    for puzzle_id, count in results:
        print(f"{puzzle_id}: {count}")


def check_delete_puzzles(engine: Engine) -> None:
    """Fetch puzzles from lichess and mark them as deleted if they do not exist"""

    # first, integrity check, make sure every report has an associated puzzle
    log.info("Integrity check: every report should have a puzzle")

    with Session(engine) as session:
        # Get all puzzle IDs from reports
        statement = select(PuzzleReport.puzzle_id).distinct()
        report_puzzle_ids = set(session.exec(statement).all())

        # Get all puzzle IDs from puzzles table
        statement = select(Puzzle.lichess_id)
        existing_puzzle_ids = set(session.exec(statement).all())

        # Find missing puzzles
        missing_puzzle_ids = report_puzzle_ids - existing_puzzle_ids

    log.info(f"Found {len(missing_puzzle_ids)} reports without puzzles")
    for puzzle_id in missing_puzzle_ids:
        puzzle = _fetch_puzzle(puzzle_id)
        with Session(engine) as session:
            session.add(puzzle)
            session.commit()
        time.sleep(0.4)  # avoid too many requests
    log.info("Integrity check done, all reports have a puzzle")

    # Only check puzzle reports with issues, to save on query time
    # and puzzles checked more than 24hrs ago, to allow for interrupting
    with Session(engine) as session:
        twenty_four_hours_ago = utc_now() - timedelta(hours=24)

        statement = (
            select(Puzzle)
            .join(PuzzleReport, col(Puzzle.lichess_id) == col(PuzzleReport.puzzle_id))
            .where(
                or_(
                    col(PuzzleReport.has_multiple_solutions).is_not(None),
                    col(PuzzleReport.has_missing_mate_theme).is_not(None),
                )
            )
            .where(
                or_(
                    col(Puzzle.checked_at).is_(None),
                    col(Puzzle.checked_at) < twenty_four_hours_ago,
                )
            )
            .where(col(Puzzle.deleted_at).is_(None))
        )
        puzzles_with_issues = list(session.exec(statement).all())
        log.info(f"Checking {len(puzzles_with_issues)} puzzles for deletion")
        # keep in session to avoid https://docs.sqlalchemy.org/en/20/errors.html#error-bhk3
        nb_deleted = 0
        for puzzle in puzzles_with_issues:
            if is_puzzle_deleted(puzzle.lichess_id):
                nb_deleted += 1
                puzzle.deleted_at = utc_now()
            puzzle.checked_at = utc_now()
            session.add(puzzle)
            session.commit()

            time.sleep(0.4)  # avoid too many requests
        log.info(f"{nb_deleted} new puzzles deleted from lichess")


def main() -> None:
    # zulip lib is sync, so use sync as well for python-chess
    # Sublime does not show *.db in sidebars
    engine = setup_db("puzzle_reports2.db")
    parser = argparse.ArgumentParser()
    # verbose
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="increase output verbosity",
        default=False,
    )

    # add arguments to subcommand
    subparser = parser.add_subparsers(required=True)

    run_parser = subparser.add_parser(
        "run",
        help="Simple commands that need no arguments",
        formatter_class=RawTextHelpFormatter,
    )

    commands = {
        "fetch": fetch_reports,
        "check": check_reports,
        "export": export_reports,
        "stats": stats,
        "delete": check_delete_puzzles,
    }

    run_parser.add_argument("command", choices=commands.keys(), help=doc(commands))
    run_parser.set_defaults(func=lambda args: commands[args.command](engine))

    go_parser = subparser.add_parser(
        "go", help="Run sequentially combination of simple commands"
    )
    go_parser.add_argument(
        "commands",
        nargs="+",
        choices=commands.keys(),
        help="Commands to run sequentially\n" + doc(commands),
    )
    go_parser.set_defaults(
        func=lambda args: [commands[cmd](engine) for cmd in args.commands]
    )

    # reset parser
    reset_parser = subparser.add_parser(
        "reset", help="Reset part of the database/state"
    )
    # add flag for unchecking all reports
    reset_parser.add_argument("--reports-checked", action="store_true")
    # zulip reactions
    reset_parser.add_argument("--reactions", action="store_true")
    reset_parser.set_defaults(func=lambda args: reset_argparse(args, engine))

    args = parser.parse_args()
    # log.handler_2.setLevel(logging.DEBUG if args.verbose else logging.INFO)
    log.debug(f"args: {args}")
    args.func(args)
    # No need to close database with sqlmodel - connections are handled by sessions
    log.info("Finished")


########
# Main #
########

if __name__ == "__main__":
    print("#" * 80)
    main()
