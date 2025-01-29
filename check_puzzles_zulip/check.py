import chess

from .models import PuzzleReport


def check_report(report: PuzzleReport) -> None:
    board = chess.Board()
    for move in board.legal_moves:
        board.push(move)
        if board.is_checkmate():
            print(f"Checkmate found: {board.fen()}")
        board.pop()
    print("Checkmate not found")
