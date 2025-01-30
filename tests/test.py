from chess.engine import Score, Cp, Mate, PovScore

from check_puzzles_zulip.parser import parse_report_v5_onward
from check_puzzles_zulip.models import PuzzleReport
from check_puzzles_zulip.lichess import _fetch_puzzle
from check_puzzles_zulip.check import _similar_eval, Checker
from check_puzzles_zulip.models import setup_db

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
        self.assertEqual(
            puzzle_report.details,
            "f6, at depth 21, multiple solutions, pvs g5g3: 229, g5h6: 81, g5h4: -10, f4e6: -396, f4g6: -484",
        )
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
        self.assertEqual(
            puzzle_report.details,
            "Bf8, at depth 31, multiple solutions, pvs c5c6: #14, e3f5: 828",
        )
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
    @unittest.skip("no need for request each time, todo mock")
    def test_fetch_puzzle(self):
        puzzle = _fetch_puzzle("3z2st")
        self.assertEqual(puzzle._id, "3z2st")
        self.assertEqual(puzzle.initialPly, 11)
        self.assertEqual(puzzle.solution, "d5c6 e4c3 c6b7 c3b5 c1d2")
        self.assertEqual(
            puzzle.themes,
            "advancedPawn advantage long sacrifice opening discoveredAttack",
        )
        self.assertEqual(
            puzzle.game_pgn, "e4 c5 Nf3 Nc6 Bb5 d6 d4 Nf6 d5 Qa5+ Nc3 Nxe4"
        )

    # describe('similarEvals', () => {
    #   // taken from https://github.com/lichess-org/tactics/issues/101
    #   test.each<[Color, number, number]>([
    #     ['black', -9600, -3500],
    #     ['white', 400, 350],
    #     ['black', -650, -630],
    #     ['black', -560, -460],
    #     ['black', -850, -640],
    #     ['black', -6500, -600],
    #     ['white', 400, 350],
    #     ['black', -6500, -6300],
    #     ['black', -560, -460],
    #     ['black', -850, -640],
    #     ['black', -6510, -600],
    #   ])('be similar', (color, bestEval, secondBestEval) => {
    #     expect(similarEvalsCp(color, bestEval, secondBestEval)).toBe(true);
    #   });

    # from lila/ui/ceval/tests/winningChances.test.ts
    def test_similar_eval(self):
        self.assertTrue(_similar_eval(Cp(9600), Cp(3500)))
        self.assertTrue(_similar_eval(Cp(400), Cp(350)))
        self.assertTrue(_similar_eval(Cp(650), Cp(630)))
        self.assertTrue(_similar_eval(Cp(560), Cp(460)))
        self.assertTrue(_similar_eval(Cp(850), Cp(640)))
        self.assertTrue(_similar_eval(Cp(6500), Cp(600)))
        self.assertTrue(_similar_eval(Cp(400), Cp(350)))
        self.assertTrue(_similar_eval(Cp(6500), Cp(6300)))
        self.assertTrue(_similar_eval(Cp(560), Cp(460)))
        self.assertTrue(_similar_eval(Cp(850), Cp(640)))
        self.assertTrue(_similar_eval(Cp(6510), Cp(600)))

    # from lila/ui/ceval/tests/winningChances.test.ts
    def test_diff_evals(self):
        #   // taken from the list of reported puzzles on zulip, and subjectively considered
        #   // false positives
        #   test.each<[Color, number, number]>([
        #     ['white', 265, -3],
        #     ['white', 269, 0],
        #     ['white', 322, -6],
        #     ['white', 778, 169],
        #     ['black', -293, -9],
        #     ['black', -179, 61],
        #     ['black', -816, -357],
        #     ['black', -225, -51],
        #   ])('be different', (color, bestEval, secondBestEval) => {
        #     expect(similarEvalsCp(color, bestEval, secondBestEval)).toBe(false);
        #   });

        #   // https://lichess.org/training/ZIRBc
        #   // It is unclear if this should be a false positive, but discussing with a few members
        #   // seems to be good enough to be considered a fp for now.
        #   test.each<[Color, EvalScore, EvalScore]>([
        #     ['black', { cp: undefined, mate: -16 }, { cp: -420, mate: undefined }],
        #   ])('be different mate/cp', (color, bestEval, secondBestEval) => {
        #     expect(winningChances.areSimilarEvals(color, bestEval, secondBestEval)).toBe(false);
        #   });
        # });

        # convert to python
        self.assertFalse(_similar_eval(Cp(265), Cp(-3)))
        self.assertFalse(_similar_eval(Cp(269), Cp(0)))
        self.assertFalse(_similar_eval(Cp(322), Cp(-6)))
        self.assertFalse(_similar_eval(Cp(778), Cp(169)))
        self.assertFalse(_similar_eval(Cp(293), Cp(9)))
        self.assertFalse(_similar_eval(Cp(179), Cp(-61)))
        self.assertFalse(_similar_eval(Cp(816), Cp(357)))
        self.assertFalse(_similar_eval(Cp(225), Cp(51)))

        self.assertFalse(_similar_eval(Mate(16), Cp(420)))

    def test_cheker(self):
        # reported XGeME because (v6, SF 17 · 79MB) after move 44. Kg6, at depth 21, multiple solutions, pvs a7a4: 507, b5b6: 434, a7a8: 58, a7a5: 51, a7a6: 50
        db = setup_db(":memory:")
        report = PuzzleReport(
            reporter="xxx",
            puzzle_id="XGeME",
            report_version=6,
            sf_version="SF 17 · 79MB",
            move=44,
            details="Kg6, at depth 21, multiple solutions, pvs a7a4: 507, b5b6: 434, a7a8: 58, a7a5: 51, a7a6: 50",
            issues="",
            local_evaluation="",
            zulip_message_id=1,
        )

        dict_info_mock = [
            {
                "string": "NNUE evaluation using nn-37f18f62d772.nnue (6MiB, (22528, 128, 15, 32, 1))",
                "depth": 29,
                "seldepth": 41,
                "multipv": 1,
                "score": PovScore(Cp(512), True),
                "nodes": 25000243,
                "nps": 827521,
                "hashfull": 998,
                "tbhits": 0,
                "time": 30.211,
                "currmove": {
                    "from_square": 34,
                    "to_square": 42,
                    "promotion": None,
                    "drop": None,
                },
                "currmovenumber": 4,
            },
            {
                "depth": 29,
                "seldepth": 56,
                "multipv": 2,
                "score": PovScore(Cp(458), True),
                "nodes": 25000243,
                "nps": 827521,
                "hashfull": 998,
                "tbhits": 0,
                "time": 30.211,
            },
            {
                "depth": 29,
                "seldepth": 52,
                "multipv": 3,
                "score": PovScore(Cp(48), True),
                "nodes": 25000243,
                "nps": 827521,
                "hashfull": 998,
                "tbhits": 0,
                "time": 30.211,
            },
            {
                "depth": 29,
                "seldepth": 11,
                "multipv": 4,
                "score": PovScore(Cp(34), True),
                "nodes": 25000243,
                "nps": 827521,
                "hashfull": 998,
                "tbhits": 0,
                "time": 30.211,
                "upperbound": True,
            },
            {
                "depth": 28,
                "seldepth": 49,
                "multipv": 5,
                "score": PovScore(Cp(33), True),
                "nodes": 25000243,
                "nps": 827521,
                "hashfull": 998,
                "tbhits": 0,
                "time": 30.211,
            },
        ]

        checker = Checker()
        # mock checker.engine.analyse and return dict_info instead
        checker.engine.analyse = lambda board, multipv, limit: dict_info_mock # type: ignore
        report2 = checker.check_report(report)
        assert isinstance(report2, PuzzleReport)
        self.assertTrue(report2.has_multiple_solutions)
        # self.assertEqual(
        #     report2.local_evaluation,
        #     "a7a4: 507, b5b6: 434, a7a8: 58, a7a5: 51, a7a6: 50",
        # )
        db.close()


if __name__ == "__main__":
    unittest.main()
