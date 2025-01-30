import configparser

import requests
import zulip

from typing import Any, List, Dict

from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry # type: ignore

from .models import PuzzleReport
from .parser import parse_report_v5_onward
from .config import ZULIP_CHANNEL, ZULIP_TOPIC, ZULIP_REPORTER, setup_logger

from dataclasses import dataclass

log = setup_logger(__file__)


RETRY_STRAT = Retry(
    total=5,
    backoff_factor=1,
    status_forcelist=[429, 500, 502, 503, 504],
    allowed_methods=["GET"]
)
ADAPTER = HTTPAdapter(max_retries=RETRY_STRAT)


SEARCH_PARAMETERS = {
    "anchor": "oldest",
    "num_after": 5000,
    "narrow": [
        {"operator": "channel", "operand": ZULIP_CHANNEL},
        # {"operator": "topic", "operand": ZULIP_TOPIC},
        # {"operator": "sender", "operand": ZULIP_REPORTER},
    ],
}


class ZulipClient:

    def __init__(self, zuliprc_path: str):
        self.zulip = zulip.Client(config_file=zuliprc_path)


    def get_puzzle_reports(self) -> List[PuzzleReport]:
        messages = self.zulip.get_messages(SEARCH_PARAMETERS).get("messages", [])
        log.debug(f"Messages fetched: {messages}")
        reports = []
        for message in messages:
            puzzle_report = parse_report_v5_onward(message["content"], message["id"])
            if puzzle_report is not None:
                reports.append(puzzle_report)
        return reports


    # def _get_messages(self, params: Dict[str, Any]) -> Dict[str, Any]:
    #     path = f"{self.config.site}/api/v1/messages"
    #     res = self.http.get(path, params=params).json()
    #     log.debug(f"Response to {path}: {res}")
    #     return res


@dataclass(frozen=True)
class ZulipConfig:
    
    # [api]
    #     email=zzz
    #     key=yyy
    #     site=xxx
    email: str
    key: str
    site: str


def parse_zuliprc(zuliprc_path: str) -> ZulipConfig:
    config = configparser.ConfigParser()
    try:
        config.read(zuliprc_path)
        return ZulipConfig(
            email=config["api"]["email"],
            key=config["api"]["key"],
            site=config["api"]["site"],
        )
    except Exception as e:
        log.error(f"Error reading zuliprc file: {e}, file: {zuliprc_path}")
        raise e



