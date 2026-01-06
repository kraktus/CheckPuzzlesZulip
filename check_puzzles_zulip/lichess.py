import logging
import requests

from sqlmodel import select

from .models import Puzzle, get_session
from .config import setup_logger

log = setup_logger(__file__)


def get_puzzle(puzzle_id: str) -> Puzzle:
    with get_session() as session:
        statement = select(Puzzle).where(Puzzle.id == puzzle_id)
        puzzle = session.exec(statement).first()
        if puzzle is not None:
            return puzzle
    puzzle = _fetch_puzzle(puzzle_id)
    log.debug(f"Creating puzzle {puzzle}")
    with get_session() as session:
        session.add(puzzle)
        session.commit()
        session.refresh(puzzle)
    return puzzle


def _fetch_puzzle(puzzle_id: str) -> Puzzle:
    """Fetch a puzzle from lichess"""
    resp = _internal_fetch_puzzle(puzzle_id)
    if resp.status_code == 404:
        puzzle = Puzzle(id=puzzle_id)
        puzzle.is_deleted = True
        return puzzle
    json = resp.json()
    return Puzzle(
        id=json["puzzle"]["id"],
        initialPly=json["puzzle"]["initialPly"],
        solution=" ".join(json["puzzle"]["solution"]),
        themes=" ".join(json["puzzle"]["themes"]),
        game_pgn=json["game"]["pgn"],
    )


# only return the request response object
def _internal_fetch_puzzle(puzzle_id: str) -> requests.Response:
    url = f"https://lichess.org/api/puzzle/{puzzle_id}"
    resp = requests.get(url)
    log.debug(f"Fetching puzzle {puzzle_id}, status: {resp.status_code} {resp.text}")
    return resp


def is_puzzle_deleted(puzzle_id: str) -> bool:
    """Update a puzzle in the database, if deleted from lichess. return `True` if deleted"""
    resp = _internal_fetch_puzzle(puzzle_id)  # type: ignore
    return resp.status_code == 404
