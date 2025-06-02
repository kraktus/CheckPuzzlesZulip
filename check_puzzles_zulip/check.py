import json
import math
import logging
import datetime

import chess
import chess.engine

from typing import Tuple, List

from chess.engine import Score, Limit, Protocol

from .lichess import get_puzzle
from .models import PuzzleReport, Puzzle
from .config import STOCKFISH, setup_logger

log = setup_logger(__file__)


class Checker:

    def __init__(self, engine: Protocol):
        self.engine = engine

    async def check_report(self, report: PuzzleReport) -> PuzzleReport:
        puzzle = self._get_puzzle(str(report.puzzle_id))
        if puzzle.is_deleted:
            report.is_deleted_from_lichess = True
        else:
            board = chess.Board()
            moves = str(puzzle.game_pgn).split()
            log.info(f"Checking puzzle {puzzle._id}")
            for move in moves:
                board.push_san(move)
            for move in str(puzzle.solution).split():
                log.debug(f"Checking move {board.ply()}, {board.fen()}")
                # report.move says that "after move {report.move}"
                # while `fullmove_number` consider the current move, hence the disparity
                if (
                    board.fullmove_number
                    == (
                        report.move + 1
                        if puzzle.color_to_win() == chess.WHITE
                        else report.move
                    )
                    and board.turn == puzzle.color_to_win()
                ):
                    log.debug(f"Checking move {board.ply()}, {board.fen()}")
                    [has_multi_sol, eval_dump] = (
                        await self.position_has_multiple_solutions(board)
                    )
                    report.has_multiple_solutions = has_multi_sol
                    report.local_evaluation = eval_dump  # type: ignore
                board.push_uci(move)
            if board.is_checkmate() and not " mate " in puzzle.themes:
                report.has_missing_mate_theme = True

        report.checked = True  # type: ignore
        return report

    async def position_has_multiple_solutions(
        self, board: chess.Board
    ) -> Tuple[bool, str]:
        log.debug(f"Analyzing position {board.fen()}")
        infos = await self.analyse_position(board)
        eval_dump = json.dumps(infos, default=default_converter)
        log.debug(f"eval_dump {infos}")
        # sort by score descending
        turn = board.turn
        infos.sort(key=lambda info: info["score"].pov(turn), reverse=True)  # type: ignore
        bestEval, secondBestEval = _get_score(infos[0], turn), _get_score(
            infos[1], turn
        )
        assert (
            bestEval is not None and secondBestEval is not None
        ), "bestEval and secondBestEval should not be None"
        return _multiple_solutions(bestEval, secondBestEval), eval_dump

    async def analyse_position(self, board: chess.Board) -> List[chess.engine.InfoDict]:
        log.debug(f"Analyzing position {board.fen()}")
        infos = await self.engine.analyse(
            board, multipv=5, limit=Limit(depth=50, nodes=25_000_000)
        )
        return infos

    # only defined to allow for override in tests
    def _get_puzzle(self, puzzle_id: str) -> Puzzle:
        return get_puzzle(puzzle_id)


def default_converter(obj):
    if isinstance(obj, datetime.datetime):
        return obj.isoformat()
    elif hasattr(obj, "__dict__"):
        return obj.__dict__
    else:
        return str(obj)  # Fallback to string representation


def _get_score(info: chess.engine.InfoDict, turn: chess.Color) -> Score | None:
    score = info.get("score")
    if score is not None:
        return score.pov(turn)


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


# multiple mates in one are allowed, because the lichess client check them and send success regardless
def _multiple_solutions(score1: Score, score2: Score) -> bool:
    return (score2.score() or 0) >= 200 or (
        _similar_eval(score1, score2)
        and not (score1.mate() == 1 and score2.mate() == 1)
    )


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
