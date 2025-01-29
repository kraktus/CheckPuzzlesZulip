import zulip

from typing import Any, List

from .models import PuzzleReport
from .parser import parse_report_v5_onward
from .config import ZULIP_CHANNEL, ZULIP_TOPIC, ZULIP_REPORTER


SEARCH_PARAMETERS = {
    "anchor": "oldest",
    "narrow": [
        {"operator": "channel", "operand": ZULIP_CHANNEL},
        {"operator": "topic", "operand": ZULIP_TOPIC},
        {"operator": "sender", "operand": ZULIP_REPORTER},
    ],
}


class ZulipClient(zulip.Client):

    def get_puzzle_reports(self) -> List[PuzzleReport]:
        messages = self.get_messages(SEARCH_PARAMETERS).get("messages", [])
        reports = []
        for message in messages:
            puzzle_report = parse_report_v5_onward(message["content"], message["id"])
            if puzzle_report is not None:
                reports.append(puzzle_report)
        return reports
