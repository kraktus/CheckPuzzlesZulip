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
    log.debug(f"Creating puzzle {puzzle}")
    puzzle.save(force_insert=True)
    return puzzle


def _fetch_puzzle(puzzle_id: str) -> Puzzle:
    """Fetch a puzzle from lichess"""
    url = f"https://lichess.org/api/puzzle/{puzzle_id}"
    resp = requests.get(url)
    log.debug(f"Fetching puzzle {puzzle_id}, status: {resp.status_code} {resp.text}")
    if resp.status_code == 404:
        puzzle = Puzzle(_id=puzzle_id)
        puzzle.is_deleted = True
        return puzzle
    json = resp.json()
    return Puzzle(
        _id=json["puzzle"]["id"],
        initialPly=json["puzzle"]["initialPly"],
        solution=" ".join(json["puzzle"]["solution"]),
        themes=" ".join(json["puzzle"]["themes"]),
        game_pgn=json["game"]["pgn"],
    )
