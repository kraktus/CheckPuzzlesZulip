import configparser

import requests
import zulip

from typing import Any, List, Dict, Literal

from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry  # type: ignore

from .models import PuzzleReport
from .parser import parse_report_v5_onward
from .config import ZULIP_CHANNEL, ZULIP_TOPIC, ZULIP_REPORTER, setup_logger

from dataclasses import dataclass

log = setup_logger(__file__)


RETRY_STRAT = Retry(
    total=5,
    backoff_factor=1,
    status_forcelist=[429, 500, 502, 503, 504],
    allowed_methods=["GET"],
)
ADAPTER = HTTPAdapter(max_retries=RETRY_STRAT)


# TODO make it so it chunks by 5000 to be sure it gets all the messages
SEARCH_PARAMETERS = {
    "anchor": "oldest",
    "num_before": 0,
    "num_after": 5000,
    "narrow": [
        {"operator": "channel", "operand": ZULIP_CHANNEL},
        {"operator": "topic", "operand": ZULIP_TOPIC},
        {"operator": "sender", "operand": ZULIP_REPORTER},
    ],
}

Emojis = Literal["check", "cross_mark", "repeat", "price_tag"]


class ZulipClient:

    def __init__(self, zuliprc_path: str):
        self.zulip = zulip.Client(config_file=zuliprc_path)

    def get_puzzle_reports(self) -> List[PuzzleReport]:
        resp = self.zulip.get_messages(SEARCH_PARAMETERS)
        log.debug(f"get_messages response: {resp}")
        messages = resp.get("messages", [])
        log.debug(f"Messages fetched: {messages}")
        reports = []
        for message in messages:
            puzzle_report = parse_report_v5_onward(message["content"], message["id"])
            if puzzle_report is not None:
                reports.append(puzzle_report)
        log.debug(f"reports found: {len(reports)}")
        return reports

    #  {'result': 'success', 'msg': '', 'ignored_parameters_unsupported': ['message_id']}
    # but seems to be working fine
    def react(self, message_id: Any, emoji: Emojis) -> None:
        request = {
            "message_id": message_id,
            "emoji_name": emoji,
        }
        log.debug(f"Reacting to message {message_id} with {emoji}")
        resp = self.zulip.add_reaction(request)
        log.debug(f"React response: {resp}")

    def unreact(self, message_id: Any, emoji: Emojis) -> None:
        request = {
            "message_id": message_id,
            "emoji_name": emoji,
        }
        log.debug(f"Unreacting to message {message_id} with {emoji}")
        resp = self.zulip.remove_reaction(request)
        log.debug(f"Unreact response: {resp}")
