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

from argparse import RawTextHelpFormatter
from sqlmodel import Session, select, func, and_, or_
from collections import deque
from dataclasses import dataclass
from datetime import datetime
from itertools import groupby
from operator import attrgetter
from pathlib import Path

from typing import Optional, List, Union, Tuple, Dict, Callable, Any

from .check import Checker
from .config import setup_logger, ZULIPRC, STOCKFISH
from .lichess import is_puzzle_deleted, _fetch_puzzle
from .models import setup_db, PuzzleReport, Puzzle, get_session
from .zulip import ZulipClient

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


def fetch_reports(engine) -> None:
    client = ZulipClient(ZULIPRC)
    reports = client.get_puzzle_reports()
    with get_session() as session:
        inserted_rows = 0
        for report_dict in reports:
            # Check if report already exists
            statement = select(PuzzleReport).where(PuzzleReport.zulip_message_id == str(report_dict["zulip_message_id"]))
            existing_report = session.exec(statement).first()
            if existing_report is None:
                # Convert dict to PuzzleReport object
                report = PuzzleReport(**report_dict)
                session.add(report)
                inserted_rows += 1
        session.commit()
        log.info(f"{inserted_rows} new reports")


def mark_duplicate_reports(engine, zulip: ZulipClient) -> None:
    """Mark duplicate reports as checked"""
    with get_session() as session:
        statement = select(PuzzleReport)
        reports = session.exec(statement).all()
        
        # Group reports by puzzle_id and move  
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
                    if not report.checked:
                        log.debug(f"Marking report {report.zulip_message_id} as checked")
                        unchecked_duplicates.append(report.zulip_message_id)
                if unchecked_duplicates:
                    log.debug(
                        f"Found {len(unchecked_duplicates)} duplicate reports for {key}"
                    )
                    for zulip_id in unchecked_duplicates:
                        zulip.react(zulip_id, "repeat")
                    
                    # Update reports as checked
                    for report in group_list[1:]:
                        if not report.checked:
                            report.checked = True
                    session.commit()


async def check_one_report(
    unchecked_report: PuzzleReport, zulip: ZulipClient, semaphore: asyncio.Semaphore
) -> None:
    async with semaphore:
        transport, engine = await chess.engine.popen_uci(STOCKFISH)
        try:
            checker = Checker(engine)
            log.info(
                f"Checking report {unchecked_report}, {unchecked_report.puzzle_id}"
            )
            checked_report = await checker.check_report(unchecked_report)
            log.debug(
                f"Issues of {unchecked_report}, training/{checked_report.puzzle_id}: {checked_report.issues}"
            )
            if checked_report.has_multiple_solutions:
                zulip.react(checked_report.zulip_message_id, "check")
            if checked_report.has_missing_mate_theme:
                zulip.react(checked_report.zulip_message_id, "price_tag")
            # no issue, it's a false positive
            if not (checked_report.has_multiple_solutions or checked_report.has_missing_mate_theme):
                zulip.react(checked_report.zulip_message_id, "cross_mark")
            
            # Save the updated report
            with get_session() as session:
                session.merge(checked_report)
                session.commit()
        finally:
            await engine.quit()


async def async_check_reports(engine, max_sf: int = 4) -> None:
    """Check the reports in the database"""

    zulip = ZulipClient(ZULIPRC)
    mark_duplicate_reports(engine, zulip)
    
    with get_session() as session:
        statement = select(PuzzleReport).where(PuzzleReport.checked == False)
        unchecked_reports = session.exec(statement).all()
        log.info(f"Checking {len(unchecked_reports)} reports")
        
        semaphore = asyncio.Semaphore(max_sf)
        tasks = [
            asyncio.create_task(check_one_report(report, zulip, semaphore))
            for report in unchecked_reports
        ]
        await asyncio.gather(*tasks)
        log.info("All reports checked")


def check_reports(engine) -> None:
    asyncio.run(async_check_reports(engine))


def export_reports(engine) -> None:
    """Export the puzzle ids with multiple solutions to a file"""
    with get_session() as session:
        statement = select(PuzzleReport).where(
            and_(
                PuzzleReport.has_multiple_solutions == True,
                PuzzleReport.is_deleted_from_lichess == False
            )
        )
        reports = session.exec(statement).all()
        
        with open("multiple_solutions.txt", "w") as f:
            for report in reports:
                print(report.debug_str())
                f.write(f"{report.puzzle_id}\n")
        log.info(f"Exported {len(reports)} reports to multiple_solutions.txt")


def reset_argparse(args) -> None:
    """Reset all reports to unchecked"""
    with get_session() as session:
        statement = select(PuzzleReport).where(PuzzleReport.checked == True)
        nb_reports = len(session.exec(statement).all())
        
        confirm = input(f"Are you sure you want to reset {nb_reports} reports? [y/N] ")
        if confirm.lower() == "y":
            if args.reports_checked:
                # Update all reports to unchecked
                reports = session.exec(select(PuzzleReport).where(PuzzleReport.checked == True)).all()
                for report in reports:
                    report.checked = False
                session.commit()
                log.info("All reports unchecked")
            if args.reactions:
                zu = ZulipClient(ZULIPRC)
                zu.unreact_all()


def stats(engine) -> None:
    """Print statistics about the reports in the database"""
    with get_session() as session:
        # most reporters
        reporter_limit = 20
        statement = (
            select(PuzzleReport.reporter, func.count(PuzzleReport.reporter).label("count"))
            .group_by(PuzzleReport.reporter)
            .order_by(func.count(PuzzleReport.reporter).desc())
            .limit(reporter_limit)
        )
        top_reporters = session.exec(statement).all()
        print("-" * 10)
        print(f"Top {reporter_limit} reporters:")
        for reporter, count in top_reporters:
            print(f"{reporter}: {count}")

        # most reported puzzles
        puzzle_limit = 20
        statement = (
            select(PuzzleReport.puzzle_id, func.count(PuzzleReport.puzzle_id).label("count"))
            .group_by(PuzzleReport.puzzle_id)
            .order_by(func.count(PuzzleReport.puzzle_id).desc())
            .limit(puzzle_limit)
        )
        top_puzzles = session.exec(statement).all()
        print(f"Top {puzzle_limit} puzzles:")
        for puzzle_id, count in top_puzzles:
            print(f"{puzzle_id}: {count}")


def check_delete_puzzles(engine) -> None:
    """Fetch puzzles from lichess and mark them as deleted if they do not exist"""

    # first, integrity check, make sure every report has an associated puzzle
    log.info("Integrity check: every report should have a puzzle")
    with get_session() as session:
        # Find reports without associated puzzles using a left outer join
        statement = (
            select(PuzzleReport)
            .outerjoin(Puzzle, PuzzleReport.puzzle_id == Puzzle._id)
            .where(Puzzle._id.is_(None))
        )
        reports_without_puzzles = session.exec(statement).all()
        log.info(f"Found {len(reports_without_puzzles)} reports without puzzles")
        
        for report in reports_without_puzzles:
            puzzle = _fetch_puzzle(report.puzzle_id)
            session.add(puzzle)
            session.commit()
            time.sleep(0.4)  # avoid too many requests
        log.info("Integrity check done, all reports have a puzzle")

        # Only check puzzle reports with issues, to save on query time
        statement = select(PuzzleReport).where(
            and_(
                or_(
                    PuzzleReport.has_multiple_solutions == True,
                    PuzzleReport.has_missing_mate_theme == True
                ),
                PuzzleReport.is_deleted_from_lichess == False
            )
        )
        puzzles_reports_with_issues = session.exec(statement).all()
        
        nb_deleted = 0
        for report in puzzles_reports_with_issues:
            if is_puzzle_deleted(report.puzzle_id):
                nb_deleted += 1
                report.is_deleted_from_lichess = True
                session.merge(report)
            time.sleep(0.4)  # avoid too many requests
        session.commit()
        log.info(f"{nb_deleted} new puzzles deleted from lichess")
        
        # Update puzzles marked as deleted
        statement = select(Puzzle).where(Puzzle.is_deleted == True)
        deleted_puzzles = session.exec(statement).all()
        for puzzle in deleted_puzzles:
            log.info(f"Puzzle {puzzle._id} is already marked as deleted")
            # Puzzle is already marked as deleted, no need to update


def main() -> None:
    # SQLModel lib is async-compatible, so use async as well for python-chess
    # Sublime does not show *.db in sidebars
    engine = setup_db("puzzle_reports.db")
    full_path = os.path.abspath("puzzle_reports.db")
    log.info(f"Using database {full_path}")
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

    # reset parser
    reset_parser = subparser.add_parser(
        "reset", help="Reset part of the database/state"
    )
    # add flag for unchecking all reports
    reset_parser.add_argument("--reports-checked", action="store_true")
    # zulip reactions
    reset_parser.add_argument("--reactions", action="store_true")
    reset_parser.set_defaults(func=reset_argparse)

    args = parser.parse_args()
    # log.handler_2.setLevel(logging.DEBUG if args.verbose else logging.INFO)
    log.debug(f"args: {args}")
    args.func(args)
    log.info("Connection closed")


########
# Main #
########

if __name__ == "__main__":
    print("#" * 80)
    main()
