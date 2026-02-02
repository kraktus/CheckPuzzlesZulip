import logging
import re

from .models import PuzzleReport
from .config import setup_logger

log = setup_logger(__file__)

V5_ONWARD_PATTERN = re.compile(
    r".*/lichess.org/@/(\w+).* reported .*/training/(\w{5}).* because \(v(\d+),?(.*)\) after move (\d+)\.(.*)</p>"
)


# <p><a href="https://lichess.org/@/BOObOO?mod&amp;notes">booboo</a> reported <a href="https://lichess.org/training/12Qi4">12Qi4</a> because (v6, SF 16 · 7MB) after move 59. Ke8, at depth 23, multiple solutions, pvs f5e5: 588, b3b4: 382, f5g6: 203, f5g4: 2, f5g5: 1</p>
def parse_report_v5_onward(
    report_text: str, zulip_message_id: int
) -> PuzzleReport | None:
    match = V5_ONWARD_PATTERN.search(report_text)
    if match:
        # Extracting the matched groups
        reporter, puzzle_id, report_version, sf_version, move, details = match.groups()
        report_version = int(report_version)
        if report_version < 5:
            log.error(
                f"ignored a report of version {report_version} zulip id: {zulip_message_id}"
            )
            return None
        # Create a PuzzleReport
        return PuzzleReport(
            reporter=reporter.lower(),
            puzzle_id=puzzle_id,
            report_version=report_version,
            sf_version=sf_version.strip(),
            move=int(move),
            details=details.strip(),
            zulip_message_id=str(zulip_message_id),
        )
