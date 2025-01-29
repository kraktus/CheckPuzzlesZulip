import logging
import requests

from .models import Puzzle
from .config import setup_logger

log = setup_logger(__file__)


def get_puzzle(puzzle_id: str) -> Puzzle:
    puzzle = Puzzle.get_or_none(Puzzle._id == puzzle_id)  # type: ignore
    if puzzle is not None:
        return puzzle
    puzzle = _fetch_puzzle(puzzle_id)
    puzzle.save()
    return puzzle


def _fetch_puzzle(puzzle_id: str) -> Puzzle:
    """Fetch a puzzle from lichess"""
    url = f"https://lichess.org/api/puzzle/{puzzle_id}"
    response = requests.get(url).json()
    return Puzzle(
        _id=response["puzzle"]["id"],
        initialPly=response["puzzle"]["initialPly"],
        solution=" ".join(response["puzzle"]["solution"]),
        themes=" ".join(response["puzzle"]["themes"]),
        game_pgn=response["game"]["pgn"],
    )
