#!/usr/local/bin/python3
# coding: utf-8
# Licence: GNU AGPLv3

""""""

from __future__ import annotations

import argparse
import json
import logging
import logging.handlers
import os
import sys

from argparse import RawTextHelpFormatter
from collections import deque
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from typing import Optional, List, Union, Tuple, Dict, Callable, Any

from .check import Checker
from .models import setup_db, PuzzleReport
from .zulip import ZulipClient
from .config import setup_logger, ZULIPRC

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
        inserted_rows = PuzzleReport.insert_many(reports).on_conflict_ignore().as_rowcount().execute()
        log.info(f"{inserted_rows} new reports")


def check_reports(db) -> None:
    """Check the reports in the database"""
    checker = Checker()
    client = ZulipClient(ZULIPRC)
    unchecked_reports = PuzzleReport.select().where(PuzzleReport.checked == False)
    print("unchecked_reports", unchecked_reports)
    for unchecked_report in unchecked_reports:
        log.info(f"Checking report {unchecked_report}, {unchecked_report.puzzle_id}")
        # if a checked version exists with same puzzle id and move, skip
        if original := PuzzleReport.get_or_none(
            PuzzleReport.puzzle_id == unchecked_report.puzzle_id,
            PuzzleReport.move == unchecked_report.move,
            PuzzleReport.checked == True,
        ):
            log.debug(f"Found duplicate at {original.zulip_message_id}")
            client.react(unchecked_report.zulip_message_id, ":repeat:")
            unchecked_report.checked = True
            unchecked_report.save()
            continue

        checked_report = checker.check_report(unchecked_report)
        log.debug(f"Issues of {unchecked_report}, training/{checked_report.puzzle_id}: {checked_report.issues}")
        if checked_report.has_multiple_solutions:
            client.react(checked_report.zulip_message_id, ":check:")
        if checked_report.has_missing_mate_theme:
            client.react(checked_report.zulip_message_id, ":price_tag:")
        # no issue, cross
        if checked_report.issues == 0:
            client.react(checked_report.zulip_message_id, ":cross_mark:")
        checked_report.save()
    print("done")



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
        "export": "todo",
    }

    run_parser.add_argument("command", choices=commands.keys(), help=doc(commands))
    run_parser.set_defaults(func=lambda args: commands[args.command](db))
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
