import asyncio
import inspect
import zlib

import chess

from pathlib import Path
from typing import List, Union, Dict, Any, Callable, Tuple

from chess import WHITE, BLACK, Move
from chess.engine import Score, Cp, Mate, PovScore, InfoDict, UciProtocol

from check_puzzles_zulip.config import STOCKFISH
from check_puzzles_zulip.parser import parse_report_v5_onward
from check_puzzles_zulip.models import PuzzleReport, PuzzleReportDict, Puzzle
from check_puzzles_zulip.lichess import _fetch_puzzle
from check_puzzles_zulip.check import _similar_eval, Checker
from check_puzzles_zulip.models import setup_db

import unittest
import datetime


def override_get_puzzle(p: Puzzle):
    def mock_get_puzzle(puzzle_id):
        if puzzle_id == p.id:
            return p
        else:
            raise ValueError("TEST: incorrect puzzle fetched")

    return mock_get_puzzle


ANALYSE_SIGN = inspect.signature(UciProtocol.analyse)


def get_checksum_args(*args, **kwargs) -> int:
    """
    Calculate a checksum for the given arguments.
    This is used to identify unique calls to the analyse method.
    """
    # `apply_defaults` does not seem necessary as it would be considered a breaking change?
    original_dict = ANALYSE_SIGN.bind(*args, **kwargs).arguments
    # remove self from the arguments, because it contains the pid changing every time
    # deepcopy is not possible, due to asyncio shenanigans
    checksum_dict = {k: v for k, v in original_dict.items() if k != "self"}
    return str(checksum_dict).encode("utf-8")


class CachedEngine(UciProtocol):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.__used_checksums = set()
        # named after cassettes in VCR
        self.__diskette_dir = Path("diskettes")
        self.__diskette_dir.mkdir(exist_ok=True)

    async def analyse(self, *args, **kwargs) -> Union[List[InfoDict], InfoDict]:
        checksum_arg = get_checksum_args(self, *args, **kwargs)
        checksum = zlib.adler32(checksum_arg)
        self.__used_checksums.add(checksum)
        path = self.__diskette_dir / f"{checksum}.py"
        if path.exists():
            with open(path) as f:
                return eval(f.read())
        res = await super().analyse(*args, **kwargs)
        with open(path, "w") as f:
            f.write(f"#{checksum_arg}\n")
            f.write(str(res))
        return res

    def list_unused_evals(self) -> List[int]:
        # list all files in the diskette directory
        return [
            int(x.stem)
            for x in self.__diskette_dir.iterdir()
            if int(x.stem) not in self.__used_checksums
        ]


# pasted from python-chess source code
async def popen_uci(
    command: Union[str, List[str]], *, setpgrp: bool = False, **popen_args: Any
) -> Tuple[asyncio.SubprocessTransport, CachedEngine]:
    transport, protocol = await CachedEngine.popen(
        command, setpgrp=setpgrp, **popen_args
    )
    try:
        await protocol.initialize()
    except:
        transport.close()
        raise
    return transport, protocol


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
        self.assertEqual(puzzle.id, "3z2st")
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
        # this necessitated to include a threshold for the 2nd mate score
        # self.assertTrue(_similar_eval(Cp(607), Cp(277)))

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


class TestChecker(unittest.IsolatedAsyncioTestCase):

    async def asyncSetUp(self):
        self.db_engine = setup_db(":memory:")
        transport, chess_engine = await popen_uci(STOCKFISH)
        self.transport = transport
        self.chess_engine = chess_engine
        self.checker = Checker(chess_engine, self.db_engine)

    async def asyncTearDown(self):
        await self.chess_engine.quit()
        # No need to close database with sqlmodel - connections are handled by sessions

    async def test_checker_multi_solution(self):
        # reported XGeME because (v6, SF 17 · 79MB) after move 44. Kg6, at depth 21, multiple solutions, pvs a7a4: 507, b5b6: 434, a7a8: 58, a7a5: 51, a7a6: 50
        report = PuzzleReport(
            reporter="xxx",
            puzzle_id="XGeME",
            report_version=6,
            sf_version="SF 17 · 79MB",
            move=44,
            details="Kg6, at depth 21, multiple solutions, pvs a7a4: 507, b5b6: 434, a7a8: 58, a7a5: 51, a7a6: 50",
            local_evaluation="",
            zulip_message_id="1",
        )
        # XGeME,8/R4p2/4pk2/1PK5/3P4/8/1r6/8 b - - 4 44,f6g6 a7a4,2520,102,90,1112,crushing defensiveMove endgame oneMove rookEndgame,https://lichess.org/EVh4X0N2/black#88,
        puzzle_mock = Puzzle(
            id="XGeME",
            initialPly=87,
            solution="f6g6 a7a4",
            themes="crushing defensiveMove endgame oneMove rookEndgame",
            game_pgn="e4 d5 exd5 Qxd5 Nc3 Qa5 Bc4 Nf6 Nf3 Bg4 h3 Bxf3 Qxf3 Nc6 Bb5 O-O-O Bxc6 bxc6 Qxc6 Qe5+ Ne2 e6 Qa8+ Kd7 Qxa7 Bc5 Qa4+ Ke7 Qf4 Qh5 Qxc7+ Rd7 Qf4 g5 Qf3 g4 Qf4 Bd6 Ng3 Bxf4 Nxh5 Nxh5 hxg4 Nf6 g3 Bc7 g5 Ne4 d3 Nd6 b3 Ba5+ Bd2 Bxd2+ Kxd2 Ne4+ Ke3 Nxg5 f4 Rg8 fxg5 Rxg5 Rxh7 Rxg3+ Kd2 Rg2+ Kc3 Rc7+ Kb4 Rgxc2 Rh5 R2c3 d4 R3c6 Rc5 Rb7+ Kc4 Rcb6 a4 Rxb3 Rb5 R7xb5 axb5 Rb2 Ra7+ Kf6 Kc5",
        )
        self.checker._get_puzzle = override_get_puzzle(puzzle_mock)
        report2 = await self.checker.check_report(report)
        assert isinstance(report2, PuzzleReport)
        self.assertTrue(report2.is_multiple_solutions_detected())
        self.assertTrue(report2.checked)

    async def test_checker_multi_solution2(self):
        # reported NtcHj because (v5) after move 50. Re1, at depth 20, multiple solutions, pvs c2a2: -597, c2f2: -345, c2b2: -32, c2e2: -10, c2d2: -3
        report = PuzzleReport(
            reporter="xxx",
            puzzle_id="NtcHj",
            report_version=5,
            sf_version="",
            move=50,
            details="Re1, at depth 20, multiple solutions, pvs c2a2: -597, c2f2: -345, c2b2: -32, c2e2: -10, c2d2: -3",
            local_evaluation="",
            zulip_message_id="1",
        )
        mock_puzzle = Puzzle(
            id="NtcHj",
            initialPly=98,
            solution="e4e1 c2a2 a4b3 a2f2 e1g1 f2f3",
            themes="crushing endgame long master rookEndgame",
            game_pgn="d4 g6 c4 Bg7 Nc3 d6 e4 e5 d5 f5 Bd3 Nf6 f3 O-O Nge2 a5 Be3 f4 Bf2 g5 h3 h5 a3 b6 b4 g4 hxg4 hxg4 bxa5 Rxa5 Kd2 g3 Be1 Kf7 Nc1 Rh8 Rxh8 Qxh8 Nb3 Ra8 Kc2 Bd7 Bd2 Na6 Nb5 Bxb5 cxb5 Nc5 Bc4 Kg6 Nxc5 dxc5 a4 Ne8 a5 Nd6 Kb3 Qe8 Qe2 Qd7 Ra2 bxa5 Rxa5 Rh8 Qf1 Rh2 Qg1 Bf8 Bf1 Nb7 Ra6+ Kf7 Rc6 Bd6 Bc4 Nd8 Qf1 Qc8 Qc1 Rxg2 Bxf4 exf4 e5 Qf5 exd6 cxd6 Rxd6 Nb7 Re6 Na5+ Ka4 Nxc4 Qxc4 Qc2+ Qxc2 Rxc2 Re4 g2",
        )
        self.checker._get_puzzle = override_get_puzzle(mock_puzzle)
        report2 = await self.checker.check_report(report)
        assert isinstance(report2, PuzzleReport)
        self.assertTrue(report2.is_multiple_solutions_detected())
        self.assertTrue(report2.checked)

    async def test_checker_multi_solution3(self):
        #   reported 5YpsY because (v5) after move 31. e4, at depth 22, multiple solutions, pvs g2g3: 477, h8g8: 289, h8f8: 0, d8f8: 0, a2a3: -51
        report = PuzzleReport(
            reporter="xxx",
            puzzle_id="5YpsY",
            report_version=5,
            sf_version="",
            move=31,
            details="e4, at depth 22, multiple solutions, pvs g2g3: 477, h8g8: 289, h8f8: 0, d8f8: 0, a2a3: -51",
            local_evaluation="",
            zulip_message_id="1",
        )
        puzzle_mock = Puzzle(
            id="5YpsY",
            initialPly=61,
            solution="e5e4 g2g3 h4h6 h8g8 f7f6 d8d6 f6g5 g8d8",
            themes="clearance crushing endgame master pin veryLong",
            game_pgn="e4 d5 exd5 Qxd5 Nf3 Bg4 Be2 Nf6 O-O Nc6 h3 Bh5 c4 Qd7 Nc3 O-O-O d4 Bxf3 Bxf3 Nxd4 Be3 e5 Nd5 Nxf3+ Qxf3 Nxd5 cxd5 Qxd5 Qe2 Bc5 Rfd1 Bd4 Rac1 g6 Qg4+ f5 Qe2 Rhe8 Qc2 Re7 Qa4 a6 b4 Qb5 Qb3 Bxe3 Rxd8+ Kxd8 Qxe3 Qxb4 Qa7 c6 Qb8+ Kd7 Rd1+ Ke6 Qc8+ Kf7 Qh8 Qh4 Rd8",
        )
        self.checker._get_puzzle = override_get_puzzle(puzzle_mock)
        report2 = await self.checker.check_report(report)
        assert isinstance(report2, PuzzleReport)
        self.assertTrue(report2.is_multiple_solutions_detected())
        self.assertTrue(report2.checked)

    async def test_checker_missing_mate_theme(self):
        # fff reported 2F0QF because (v6, SF 16 · 7MB) after move 38. Kh4, at depth 99, multiple solutions, pvs d4f3: #-1, f1h1: #-1
        report = PuzzleReport(
            reporter="fff",
            puzzle_id="2F0QF",
            report_version=6,
            sf_version="SF 16 · 7MB",
            move=38,
            details="Kh4, at depth 99, multiple solutions, pvs d4f3: #-1, f1h1: #-1",
            local_evaluation="",
            zulip_message_id="1",
        )

        puzzle_mock = Puzzle(
            id="2F0QF",
            initialPly=68,
            solution="c8c7 a3f3 g2h2 f3f2 h2h3 f2f1 h3h4 f1h1",
            themes="endgame",
            game_pgn="e4 c6 c3 d5 exd5 cxd5 d4 Nf6 Nf3 Nc6 Be3 Bg4 Qd2 e6 Na3 Bxa3 bxa3 O-O c4 dxc4 Bxc4 Rc8 Bb3 Bxf3 gxf3 Nd5 O-O Qh4 Bg5 Qh3 Rae1 h6 Bf4 Qxf3 Bg3 Nce7 Rc1 Rxc1 Rxc1 Nf5 Bd1 Qe4 Be5 f6 Bc2 Qg4+ Bg3 Qxd4 Qa5 Nxg3 hxg3 Rc8 Qe1 Qb2 Bh7+ Kxh7 Rxc8 Nc3 Qxe6 Ne2+ Kg2 Nd4 Qe4+ f5 Qe8 Qxa3 Qg8+ Kg6",
        )
        self.checker._get_puzzle = override_get_puzzle(puzzle_mock)
        report2 = await self.checker.check_report(report)
        assert isinstance(report2, PuzzleReport)
        self.assertFalse(report2.is_multiple_solutions_detected())
        self.assertTrue(report2.is_missing_mate_theme_detected())
        self.assertTrue(report2.checked)


if __name__ == "__main__":
    print("#" * 80)
    try:
        unittest.main()
    except Exit as e:
        print(f"Exiting with code {e.code}")
        print(
            "In case of import failure, try `uv run -m unittest tests/test.py` instead"
        )

    # asyncio.run(test())
