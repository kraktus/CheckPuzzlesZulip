import json
import math
import logging
import datetime

import chess
import chess.engine

from typing import Tuple

from chess.engine import Score, Limit

from .lichess import get_puzzle
from .models import PuzzleReport
from .config import STOCKFISH, setup_logger

log = setup_logger(__file__)


class Checker:

    def __init__(self):
        self.engine = chess.engine.SimpleEngine.popen_uci(STOCKFISH)

    def check_report(self, report: PuzzleReport) -> PuzzleReport | None:
        puzzle = get_puzzle(str(report.puzzle_id))
        board = chess.Board()
        moves = str(puzzle.game_pgn).split()
        for move in moves:
            board.push_san(move)
        print("sol ", str(puzzle.solution).split())
        for move in str(puzzle.solution).split():
            log.debug(f"Checking move {board.ply()}, {board.fen()}")
            # check if ply is the reported one
            if board.ply() == (int(report.move) * 2):  # type: ignore
                log.debug(f"Checking move {board.ply()}, {board.fen()}")
                [has_multi_sol, eval_dump] = self.position_has_multiple_solutions(board)
                report.has_multiple_solutions = has_multi_sol
                report.local_evaluation = eval_dump  # type: ignore
                log.debug(f"Reported: {eval_dump}")
                return report
            board.push_uci(move)

    # return HasMultipleSolutions if the position has multiple solutions
    def position_has_multiple_solutions(self, board: chess.Board) -> Tuple[bool, str]:
        log.debug(f"Analyzing position {board.fen()}")
        infos = self.engine.analyse(
            board, multipv=5, limit=Limit(depth=50, nodes=25_000_000)
        )
        eval_dump = json.dumps(infos, default=default_converter)
        log.debug("eval_dump", eval_dump)
        # sort by score descending
        color = board.turn
        infos.sort(key=lambda info: info["score"].pov(color), reverse=True)  # type: ignore
        # chechking both scores from white should be enough to know if the position has multiple solutions
        # even if the puzzle is from black perspective
        bestEval, secondBestEval = _get_white_score(infos[0]), _get_white_score(
            infos[1]
        )
        assert (
            bestEval is not None and secondBestEval is not None
        ), "bestEval and secondBestEval should not be None"
        return _similar_eval(bestEval, secondBestEval), eval_dump


def default_converter(obj):
    if isinstance(obj, datetime.datetime):
        return obj.isoformat()
    elif hasattr(obj, "__dict__"):
        return obj.__dict__
    else:
        return str(obj)  # Fallback to string representation


def _get_white_score(info: chess.engine.InfoDict) -> Score | None:
    pov = info.get("score")
    if pov is not None:
        return pov.white()


# from lichess-puzzler / utils.py
def _win_chances(score: Score) -> float:
    """
    winning chances from -1 to 1 https://graphsketch.com/?eqn1_color=1&eqn1_eqn=100+*+%282+%2F+%281+%2B+exp%28-0.004+*+x%29%29+-+1%29&eqn2_color=2&eqn2_eqn=&eqn3_color=3&eqn3_eqn=&eqn4_color=4&eqn4_eqn=&eqn5_color=5&eqn5_eqn=&eqn6_color=6&eqn6_eqn=&x_min=-1000&x_max=1000&y_min=-100&y_max=100&x_tick=100&y_tick=10&x_label_freq=2&y_label_freq=2&do_grid=0&do_grid=1&bold_labeled_lines=0&bold_labeled_lines=1&line_width=4&image_w=850&image_h=525
    """
    mate = score.mate()
    if mate is not None:
        return 1 if mate > 0 else -1

    cp = score.score()
    MULTIPLIER = -0.00368208  # https://github.com/lichess-org/lila/pull/11148
    return 2 / (1 + math.exp(MULTIPLIER * cp)) - 1 if cp is not None else 0


def _win_diff(score1: Score, score2: Score) -> float:
    return (_win_chances(score1) - _win_chances(score2)) / 2


# lila/ui/puzzle/src/WinningChances.ts
def _similar_eval(score1: Score, score2: Score) -> bool:
    win_diff = _win_diff(score1, score2)
    return win_diff < 0.14


#         export const povDiff = (color: Color, e1: EvalScore, e2: EvalScore): number =>
#   (povChances(color, e1) - povChances(color, e2)) / 2;

# // used to check if two evaluations are similar enough
# // to report puzzles as faulty
# //
# // stricter than lichess-puzzler v49 check
# // to avoid false positives and only report really faulty puzzles
# export const areSimilarEvals = (pov: Color, bestEval: EvalScore, secondBestEval: EvalScore): boolean => {
#   return povDiff(pov, bestEval, secondBestEval) < 0.14;
# };
