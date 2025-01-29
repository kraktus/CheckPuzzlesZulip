import logging
import re

from .models import PuzzleReport

log = logging.getLogger(__file__)

V5_ONWARD_PATTERN = re.compile(r".*/lichess.org/@/(\w+).* reported \[(\w{5})\].* because \(v(\d+),?(.*)\) after move (\d+)\.(.*)")

# [xxx](https://lichess.org/@/xxx?mod&notes) reported [wfHlQ](https://lichess.org/training/wfHlQ) because (v6, SF 16 · 7MB) after move 17. f6, at depth 21, multiple solutions, pvs g5g3: 229, g5h6: 81, g5h4: -10, f4e6: -396, f4g6: -484
def parse_report_v5_onward(report_text: str, zulip_message_id: int) -> PuzzleReport | None:
    match = V5_ONWARD_PATTERN.search(report_text)
    if match:
        # Extracting the matched groups
        reporter, puzzle_id, report_version, sf_version, move, details = match.groups()
        report_version = int(report_version)
        if report_version < 5:
            log.error(f"successfully parsed a report with `parse_report_v5_onward` a report of version {report_version} text: {report_text}")
            return None
        # Create a PuzzleReport instance
        return PuzzleReport(
            reporter=reporter,
            puzzle_id=puzzle_id,
            report_version=report_version,
            sf_version=sf_version.strip(),
            move=int(move),
            details=details.strip(),
            issues="",
            local_evaluation="",
            zulip_message_id=zulip_message_id,
        )