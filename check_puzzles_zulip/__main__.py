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
import time
import multiprocessing as mp
import concurrent.futures
from concurrent.futures import ProcessPoolExecutor
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
        inserted_rows = (
            PuzzleReport.insert_many(reports)
            .on_conflict_ignore()
            .as_rowcount()
            .execute()
        )
        log.info(f"{inserted_rows} new reports")


def check_reports(db, workers: Optional[int] = None) -> None:
    """Check the reports in the database using multiple processes, processing results as they arrive"""
    checker = Checker()
    client = ZulipClient(ZULIPRC)
    unchecked_reports = list(PuzzleReport.select().where(PuzzleReport.checked == False))

    if not unchecked_reports:
        log.info("No unchecked reports found")
        return

    # Process duplicates first
    for report in unchecked_reports[:]:
        if original := PuzzleReport.get_or_none(
            PuzzleReport.puzzle_id == report.puzzle_id,
            PuzzleReport.move == report.move,
            PuzzleReport.checked == True,
        ):
            log.debug(f"Found duplicate at {original.zulip_message_id}")
            client.react(report.zulip_message_id, "repeat")
            report.checked = True
            report.save()
            unchecked_reports.remove(report)

    if not unchecked_reports:
        log.info("All reports were duplicates")
        return

    # Use process pool for remaining reports
    max_workers = workers or mp.process_cpu_count()
    log.info(f"Processing {len(unchecked_reports)} reports with {max_workers} workers")
    processed_count = 0

    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        # Submit all tasks and get futures
        future_to_report = {
            executor.submit(checker.check_report, report): report 
            for report in unchecked_reports
        }
        
        # Process results as they complete
        for future in concurrent.futures.as_completed(future_to_report):
            try:
                checked_report = future.result()
                processed_count += 1
                
                log.debug(
                    f"[{processed_count}/{len(unchecked_reports)}] Issues of puzzle "
                    f"training/{checked_report.puzzle_id}: {checked_report.issues}"
                )
                
                if checked_report.has_multiple_solutions:
                    client.react(checked_report.zulip_message_id, "check")
                if checked_report.has_missing_mate_theme:
                    client.react(checked_report.zulip_message_id, "price_tag")
                if checked_report.issues == 0:
                    client.react(checked_report.zulip_message_id, "cross_mark")
                checked_report.save()
                
            except Exception as e:
                report = future_to_report[future]
                log.error(f"Error processing report {report.puzzle_id}: {str(e)}")

    log.info("All reports checked")


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
    parser.add_argument(
        "-w",
        "--workers",
        type=int,
        help="number of worker processes (default: CPU count)",
        default=None,
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
        "export": "todo",
    }

    run_parser.add_argument("command", choices=commands.keys(), help=doc(commands))
    run_parser.set_defaults(func=lambda args: commands[args.command](db))

    # check parser
    check_parser = subparser.add_parser(
        "check", help="Check puzzle reports"
    )
    check_parser.set_defaults(func=lambda args: check_reports(db, args.workers))

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
