import chess

from .models import PuzzleReportDb


def check_report(report: PuzzleReportDb) -> None:
    board = chess.Board()
    for move in board.legal_moves:
        board.push(move)
        if board.is_checkmate():
            print(f"Checkmate found: {board.fen()}")
        board.pop()
    print("Checkmate not found")
