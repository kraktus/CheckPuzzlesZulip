from check_puzzles_zulip.parser import parse_report_v5_onward
from check_puzzles_zulip.models import PuzzleReport

import unittest
import datetime


class Test(unittest.TestCase):
    def __init__(self, *args, **kwargs):
        super(Test, self).__init__(*args, **kwargs)
        self.maxDiff = None

    def test_parse_v5_onward_on_v6(self):
        txt = "xxx reported wfHlQ because (v6, SF 16 · 7MB) after move 17. f6, at depth 21, multiple solutions, pvs g5g3: 229, g5h6: 81, g5h4: -10, f4e6: -396, f4g6: -484"
        zulip_message_id = 1
        expected = PuzzleReport(
            reporter="xxx",
            puzzle_id="wfHlQ",
            report_version=6,
            sf_version="SF 16 · 7MB",
            move=17,
            details="f6, at depth 21, multiple solutions, pvs g5g3: 229, g5h6: 81, g5h4: -10, f4e6: -396, f4g6: -484",
            issues="",
            local_evaluation="",
            zulip_message_id=zulip_message_id,
        )
        self.assertEqual(parse_report_v5_onward(txt, zulip_message_id), expected)

    def test_parse_v5_onward_on_v5(self):
        txt = "yyy reported jTKok because (v5) after move 36. Bf8, at depth 31, multiple solutions, pvs c5c6: #14, e3f5: 828"
        zulip_message_id = 1
        expected = PuzzleReport(
            reporter="yyy",
            puzzle_id="jTKok",
            report_version=5,
            sf_version="",
            move=36,
            details="Bf8, at depth 31, multiple solutions, pvs c5c6: #14, e3f5: 828",
            issues="",
            local_evaluation="",
            zulip_message_id=zulip_message_id,
        )
        self.assertEqual(parse_report_v5_onward(txt, zulip_message_id), expected)


if __name__ == "__main__":
    unittest.main()
