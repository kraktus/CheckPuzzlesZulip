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


import peewee
import chess
import chess.engine

from peewee import fn
from argparse import RawTextHelpFormatter
from playhouse.shortcuts import model_to_dict
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
from .models import setup_db, PuzzleReport, Puzzle
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


def fetch_reports(db) -> None:

    client = ZulipClient(ZULIPRC)
    reports = client.get_puzzle_reports()
    with db.atomic():
        inserted_rows = (
            PuzzleReport.insert_many(reports)
            .on_conflict_ignore()
            .as_rowcount()
            .execute()
        )
        log.info(f"{inserted_rows} new reports")


def mark_duplicate_reports(db, zulip: ZulipClient) -> None:
    """Mark duplicate reports as checked"""
    query = PuzzleReport.select()
    # do everything in python for now
    reports = [report for report in query.execute()]
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
                with db.atomic():
                    PuzzleReport.update(checked=True).where(
                        PuzzleReport.zulip_message_id.in_(unchecked_duplicates)  # type: ignore
                    ).execute()


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
            if checked_report.issues == 0:
                zulip.react(checked_report.zulip_message_id, "cross_mark")
            checked_report.save()
        finally:
            await engine.quit()


async def async_check_reports(db, max_sf: int = 4) -> None:
    """Check the reports in the database"""

    zulip = ZulipClient(ZULIPRC)
    mark_duplicate_reports(db, zulip)
    query = PuzzleReport.select().where(PuzzleReport.checked == False)
    log.info(f"Checking {query.count()} reports")
    unchecked_reports = list(query.execute())
    semaphore = asyncio.Semaphore(max_sf)
    tasks = [
        asyncio.create_task(check_one_report(report, zulip, semaphore))
        for report in unchecked_reports
    ]
    await asyncio.gather(*tasks)
    log.info("All reports checked")


def check_reports(db) -> None:
    asyncio.run(async_check_reports(db))


def export_reports(db) -> None:
    """Export the puzzle ids with multiple solutions to a file"""
    query = PuzzleReport.select().where(
        (PuzzleReport.has_multiple_solutions == True)
        & (PuzzleReport.is_deleted_from_lichess == False)
    )
    reports = query.execute()
    with open("multiple_solutions.txt", "w") as f:
        for report in reports:
            print(report.debug_str())
            f.write(f"{report.puzzle_id}\n")
    log.info(f"Exported {len(reports)} reports to multiple_solutions.txt")


def reset_argparse(args) -> None:
    """Reset all reports to unchecked"""
    nb_reports = PuzzleReport.select().where(PuzzleReport.checked == True).count()
    confirm = input(f"Are you sure you want to reset {args}? [y/N] ")
    if confirm.lower() == "y":
        if args.reports_checked:
            PuzzleReport.update(checked=False).execute()
            log.info("All reports unchecked")
        if args.reactions:
            zu = ZulipClient(ZULIPRC)
            zu.unreact_all()


def stats(db) -> None:
    """Print statistics about the reports in the database"""
    # most reporters
    reporter_limit = 20
    query = (
        PuzzleReport.select(
            PuzzleReport.reporter, fn.COUNT(PuzzleReport.reporter).alias("count")
        )
        .group_by(PuzzleReport.reporter)
        .order_by(fn.COUNT(PuzzleReport.reporter).desc())
        .limit(reporter_limit)
    )
    top_reporters = query.execute()
    print("-" * 10)
    print(f"Top {reporter_limit} reporters:")
    for reporter in top_reporters:
        print(f"{reporter.reporter}: {reporter.count}")

    # most reported puzzles
    puzzle_limit = 20
    query = (
        PuzzleReport.select(
            PuzzleReport.puzzle_id, fn.COUNT(PuzzleReport.puzzle_id).alias("count")
        )
        .group_by(PuzzleReport.puzzle_id)
        .order_by(fn.COUNT(PuzzleReport.puzzle_id).desc())
        .limit(puzzle_limit)
    )
    top_puzzles = query.execute()
    print(f"Top {puzzle_limit} puzzles:")
    for puzzle in top_puzzles:
        print(f"{puzzle.puzzle_id}: {puzzle.count}")


def check_delete_puzzles(db) -> None:
    """Fetch puzzles from lichess and mark them as deleted if they do not exist"""

    # first, integrity check, make sure every report has an associated puzzle
    log.info("Integrity check: every report should have a puzzle")
    reports_without_puzzles = (
        PuzzleReport.select()
        .join(
            Puzzle,
            on=(PuzzleReport.puzzle_id == Puzzle._id),
            join_type=peewee.JOIN.LEFT_OUTER,
        )
        .where(Puzzle._id.is_null())
    )
    log.info(f"Found {reports_without_puzzles.count()} reports without puzzles")
    for report in reports_without_puzzles:
        puzzle = _fetch_puzzle(report.puzzle_id)
        puzzle.save(force_insert=True)
        time.sleep(0.4)  # avoid too many requests
    log.info("Integrity check done, all reports have a puzzle")

    # Only check puzzle reports with issues, to save on query time
    puzzles_reports_with_issues = PuzzleReport.select().where(PuzzleReport.issues != 0 & PuzzleReport.is_deleted_from_lichess == False)
    nb_deleted = 0
    for report in puzzles_reports_with_issues.execute():
        if is_puzzle_deleted(report.puzzle_id):
            nb_deleted += 1
            report.is_deleted_from_lichess = True
            report.save()
        time.sleep(0.4)  # avoid too many requests
    log.info(f"{nb_deleted} new puzzles deleted from lichess")
    query = (
        Puzzle.select(Puzzle, PuzzleReport)
        .join(PuzzleReport, on=(Puzzle._id == PuzzleReport.puzzle_id))
        .where((Puzzle.is_deleted == True))
    )
    for puzzle in query.execute():
        log.info(f"Marking report {puzzle._id} as deleted from lichess")
        puzzle.is_deleted = True
        puzzle.save()


def main() -> None:
    # zulip lib is sync, so use sync as well for python-chess
    # Sublime does not show *.db in sidebars
    db = setup_db("puzzle_reports.db")
    full_path = os.path.abspath(db.database)
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
    run_parser.set_defaults(func=lambda args: commands[args.command](db))

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
    db.close()
    log.info("Connection closed")


########
# Main #
########

if __name__ == "__main__":
    print("#" * 80)
    main()
