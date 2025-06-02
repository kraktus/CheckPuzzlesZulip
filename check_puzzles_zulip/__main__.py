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
from collections import deque
from dataclasses import dataclass
from datetime import datetime
from itertools import groupby
from operator import attrgetter
from pathlib import Path

from typing import Optional, List, Union, Tuple, Dict, Callable, Any

from .check import Checker
from .models import setup_db, PuzzleReport
from .zulip import ZulipClient
from .config import setup_logger, ZULIPRC, STOCKFISH

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
            # no issue, cross
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
    query = PuzzleReport.select().where(PuzzleReport.has_multiple_solutions == True)
    reports = query.execute()
    with open("multiple_solutions.txt", "w") as f:
        for report in reports:
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
