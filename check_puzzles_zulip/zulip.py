import zulip

from typing import Any

from .config import ZULIP_CHANNEL, ZULIP_TOPIC


SEARCH_PARAMETERS = {
    "anchor": "oldest",
    "narrow": [
        {"operator": "channel", "operand": ZULIP_CHANNEL},
        {"operator": "topic", "operand": ZULIP_TOPIC},

    ],
}

class ZulipClient(zulip.Client):

    def get_puzzle_reports(self):
        return self.get_messages(SEARCH_PARAMETERS)["messages"]

