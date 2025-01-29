from check_puzzles_zulip.parser import parse_report_v5_onward
from check_puzzles_zulip.models import PuzzleReport
from check_puzzles_zulip.lichess import _fetch_puzzle


import unittest
import datetime


class Test(unittest.TestCase):
    def __init__(self, *args, **kwargs):
        super(Test, self).__init__(*args, **kwargs)
        self.maxDiff = None

    def test_parse_v5_onward_on_v6(self):
        txt = "[xxx](https://lichess.org/@/xxx?mod&notes) reported [wfHlQ](https://lichess.org/training/wfHlQ) because (v6, SF 16 · 7MB) after move 17. f6, at depth 21, multiple solutions, pvs g5g3: 229, g5h6: 81, g5h4: -10, f4e6: -396, f4g6: -484"
        zulip_message_id = 1
        puzzle_report = parse_report_v5_onward(txt, zulip_message_id)
        assert isinstance(puzzle_report, PuzzleReport)
        self.assertEqual(puzzle_report.reporter, "xxx")
        self.assertEqual(puzzle_report.puzzle_id, "wfHlQ")
        self.assertEqual(puzzle_report.report_version, 6)
        self.assertEqual(puzzle_report.sf_version, "SF 16 · 7MB")
        self.assertEqual(puzzle_report.move, 17)
        self.assertEqual(puzzle_report.details, "f6, at depth 21, multiple solutions, pvs g5g3: 229, g5h6: 81, g5h4: -10, f4e6: -396, f4g6: -484")
        self.assertEqual(puzzle_report.issues, "")
        self.assertEqual(puzzle_report.local_evaluation, "")
        self.assertEqual(puzzle_report.zulip_message_id, zulip_message_id)

    def test_parse_v5_onward_on_v5(self):
        txt = "[yyy](https://lichess.org/@/yyy?mod&notes) reported [jTKok](https://lichess.org/training/jTKok) because (v5) after move 36. Bf8, at depth 31, multiple solutions, pvs c5c6: #14, e3f5: 828"
        zulip_message_id = 1
        puzzle_report = parse_report_v5_onward(txt, zulip_message_id)
        assert isinstance(puzzle_report, PuzzleReport)
        self.assertEqual(puzzle_report.reporter, "yyy")
        self.assertEqual(puzzle_report.puzzle_id, "jTKok")
        self.assertEqual(puzzle_report.report_version, 5)
        self.assertEqual(puzzle_report.sf_version, "")
        self.assertEqual(puzzle_report.move, 36)
        self.assertEqual(puzzle_report.details, "Bf8, at depth 31, multiple solutions, pvs c5c6: #14, e3f5: 828")
        self.assertEqual(puzzle_report.issues, "")
        self.assertEqual(puzzle_report.local_evaluation, "")
        self.assertEqual(puzzle_report.zulip_message_id, zulip_message_id)

# {
#     "game":
#     {
#         "id": "hxZj9l1g",
#         "perf":
#         {
#             "key": "rapid",
#             "name": "Rapid"
#         },
#         "rated": true,
#         "players":
#         [
#             {
#                 "name": "vmileslifestyle",
#                 "id": "vmileslifestyle",
#                 "color": "white",
#                 "rating": 1835
#             },
#             {
#                 "name": "saeedrousta",
#                 "id": "saeedrousta",
#                 "color": "black",
#                 "rating": 1844
#             }
#         ],
#         "pgn": "e4 c5 Nf3 Nc6 Bb5 d6 d4 Nf6 d5 Qa5+ Nc3 Nxe4",
#         "clock": "10+0"
#     },
#     "puzzle":
#     {
#         "id": "3z2st",
#         "rating": 1869,
#         "plays": 16599,
#         "solution":
#         [
#             "d5c6",
#             "e4c3",
#             "c6b7",
#             "c3b5",
#             "c1d2"
#         ],
#         "themes":
#         [
#             "advancedPawn",
#             "advantage",
#             "long",
#             "sacrifice",
#             "opening",
#             "discoveredAttack"
#         ],
#         "initialPly": 11
#     }
# }
    def test_fetch_puzzle(self):
        puzzle = _fetch_puzzle("3z2st")
        self.assertEqual(puzzle._id, "3z2st")
        self.assertEqual(puzzle.initialPly, 11)
        self.assertEqual(puzzle.solution, "d5c6 e4c3 c6b7 c3b5 c1d2")
        self.assertEqual(puzzle.themes, "advancedPawn advantage long sacrifice opening discoveredAttack")
        self.assertEqual(puzzle.game_pgn, "e4 c5 Nf3 Nc6 Bb5 d6 d4 Nf6 d5 Qa5+ Nc3 Nxe4")


if __name__ == "__main__":
    unittest.main()
