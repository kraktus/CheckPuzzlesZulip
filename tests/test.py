from chess import WHITE, BLACK, Move
from chess.engine import Score, Cp, Mate, PovScore

from check_puzzles_zulip.parser import parse_report_v5_onward
from check_puzzles_zulip.models import PuzzleReport, PuzzleReportDict
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
        txt = '<p><a href="https://lichess.org/@/BOObOO?mod&amp;notes">booboo</a> reported <a href="https://lichess.org/training/12Qi4">12Qi4</a> because (v6, SF 16 · 7MB) after move 59. Ke8, at depth 23, multiple solutions, pvs f5e5: 588, b3b4: 382, f5g6: 203, f5g4: 2, f5g5: 1</p>'
        zulip_message_id = 1
        puzzle_report = parse_report_v5_onward(txt, zulip_message_id)
        assert puzzle_report is not None
        expected = {
            "reporter": "booboo",
            "puzzle_id": "12Qi4",
            "report_version": 6,
            "sf_version": "SF 16 · 7MB",
            "move": 59,
            "details": "Ke8, at depth 23, multiple solutions, pvs f5e5: 588, b3b4: 382, f5g6: 203, f5g4: 2, f5g5: 1",
            "zulip_message_id": zulip_message_id,
            "issues": "",
            "local_evaluation": "",
        }
        self.assertEqual(puzzle_report, expected)

    def test_parse_v5_onward_on_v5(self):
        txt = '<p><a href="https://lichess.org/@/zzz?mod&amp;notes">zzz</a> reported <a href="https://lichess.org/training/jTKok">jTKok</a> because (v5) after move 36. Bf8, at depth 31, multiple solutions, pvs c5c6: #14, e3f5: 828</p>'
        zulip_message_id = 1
        puzzle_report = parse_report_v5_onward(txt, zulip_message_id)
        assert puzzle_report is not None
        expected = {
            "reporter": "zzz",
            "puzzle_id": "jTKok",
            "report_version": 5,
            "sf_version": "",
            "move": 36,
            "details": "Bf8, at depth 31, multiple solutions, pvs c5c6: #14, e3f5: 828",
            "zulip_message_id": zulip_message_id,
            "issues": "",
            "local_evaluation": "",
        }
        self.assertEqual(puzzle_report, expected)

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

    def test_checker_multi_solution(self):
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
        checker.engine.analyse = lambda board, multipv, limit: dict_info_mock  # type: ignore
        report2 = checker.check_report(report)
        assert isinstance(report2, PuzzleReport)
        self.assertTrue(report2.has_multiple_solutions)
        db.close()

    def test_checker_missing_mate_theme(self):
        # fff reported 2F0QF because (v6, SF 16 · 7MB) after move 38. Kh4, at depth 99, multiple solutions, pvs d4f3: #-1, f1h1: #-1
        db = setup_db(":memory:")
        report = PuzzleReport(
            reporter="fff",
            puzzle_id="2F0QF",
            report_version=6,
            sf_version="SF 16 · 7MB",
            move=38,
            details="Kh4, at depth 99, multiple solutions, pvs d4f3: #-1, f1h1: #-1",
            issues="",
            local_evaluation="",
            zulip_message_id=1,
        )

        dict_info_mock = [
            {
                "string": "NNUE evaluation using nn-37f18f62d772.nnue (6MiB, (22528, 128, 15, 32, 1))",
                "depth": 32,
                "seldepth": 2,
                "multipv": 1,
                "score": PovScore(Mate(+1), BLACK),
                "nodes": 25000112,
                "nps": 825249,
                "hashfull": 1000,
                "tbhits": 0,
                "time": 30.294,
                "pv": [Move.from_uci("d4f3")],
                "currmove": Move.from_uci("d4e6"),
                "currmovenumber": 3,
            },
            {
                "depth": 32,
                "seldepth": 2,
                "multipv": 2,
                "score": PovScore(Mate(+1), BLACK),
                "nodes": 25000112,
                "nps": 825249,
                "hashfull": 1000,
                "tbhits": 0,
                "time": 30.294,
                "pv": [Move.from_uci("f1h1")],
            },
            {
                "depth": 31,
                "seldepth": 59,
                "multipv": 3,
                "score": PovScore(Cp(-516), BLACK),
                "nodes": 25000112,
                "nps": 825249,
                "hashfull": 1000,
                "tbhits": 0,
                "time": 30.294,
                "pv": [
                    Move.from_uci("d4e6"),
                    Move.from_uci("g8e6"),
                    Move.from_uci("g6h7"),
                    Move.from_uci("e6d5"),
                    Move.from_uci("f1f2"),
                    Move.from_uci("h4h3"),
                    Move.from_uci("f2f1"),
                    Move.from_uci("d5g2"),
                    Move.from_uci("f1d1"),
                    Move.from_uci("h3h2"),
                    Move.from_uci("d1h5"),
                    Move.from_uci("h2g1"),
                    Move.from_uci("b7b5"),
                    Move.from_uci("g2f1"),
                    Move.from_uci("h5g4"),
                    Move.from_uci("g1g2"),
                    Move.from_uci("g4e4"),
                    Move.from_uci("f1f3"),
                    Move.from_uci("e4e5"),
                    Move.from_uci("c7c2"),
                    Move.from_uci("a7a5"),
                    Move.from_uci("c2f2"),
                    Move.from_uci("h7g6"),
                    Move.from_uci("f2e2"),
                    Move.from_uci("e5c5"),
                    Move.from_uci("e2e6"),
                    Move.from_uci("g6h7"),
                    Move.from_uci("e6e3"),
                    Move.from_uci("c5c2"),
                    Move.from_uci("e3e2"),
                ],
            },
            {
                "depth": 31,
                "seldepth": 13,
                "multipv": 4,
                "score": PovScore(Mate(-6), BLACK),
                "nodes": 25000112,
                "nps": 825249,
                "hashfull": 1000,
                "tbhits": 0,
                "time": 30.294,
                "pv": [
                    Move.from_uci("f1f4"),
                    Move.from_uci("g3f4"),
                    Move.from_uci("d4f3"),
                    Move.from_uci("h4g3"),
                    Move.from_uci("f3g5"),
                    Move.from_uci("g8g7"),
                    Move.from_uci("g6h5"),
                    Move.from_uci("f4g5"),
                    Move.from_uci("f5f4"),
                    Move.from_uci("g3f4"),
                    Move.from_uci("h6g5"),
                    Move.from_uci("g7g5"),
                ],
            },
            {
                "depth": 31,
                "seldepth": 9,
                "multipv": 5,
                "score": PovScore(Mate(-4), BLACK),
                "nodes": 25000112,
                "nps": 825249,
                "hashfull": 1000,
                "tbhits": 0,
                "time": 30.294,
                "pv": [
                    Move.from_uci("f1h3"),
                    Move.from_uci("h4h3"),
                    Move.from_uci("g6f6"),
                    Move.from_uci("g8g7"),
                    Move.from_uci("f6e6"),
                    Move.from_uci("g7e7"),
                    Move.from_uci("e6d5"),
                    Move.from_uci("c7c5"),
                ],
            },
        ]

        checker = Checker()
        # mock checker.engine.analyse and return dict_info instead
        checker.engine.analyse = lambda board, multipv, limit: dict_info_mock  # type: ignore
        report2 = checker.check_report(report)
        assert isinstance(report2, PuzzleReport)
        self.assertFalse(report2.has_multiple_solutions)
        self.assertTrue(report2.has_missing_mate_theme)
        db.close()


if __name__ == "__main__":
    print("#" * 80)
    unittest.main()
