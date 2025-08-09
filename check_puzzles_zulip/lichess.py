import logging
import requests

from .models import Puzzle, get_session
from .config import setup_logger
from sqlmodel import Session, select

log = setup_logger(__file__)


def get_puzzle(puzzle_id: str) -> Puzzle:
    with get_session() as session:
        # SQLModel equivalent of Puzzle.get_or_none(Puzzle._id == puzzle_id)
        statement = select(Puzzle).where(Puzzle._id == puzzle_id)
        puzzle = session.exec(statement).first()
        if puzzle is not None:
            return puzzle
        puzzle = _fetch_puzzle(puzzle_id)
        log.debug(f"Creating puzzle {puzzle}")
        session.add(puzzle)
        session.commit()
        session.refresh(puzzle)
        return puzzle


def _fetch_puzzle(puzzle_id: str) -> Puzzle:
    """Fetch a puzzle from lichess"""
    resp = _internal_fetch_puzzle(puzzle_id)
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


# only return the request response object
def _internal_fetch_puzzle(puzzle_id: str) -> requests.Response:
    url = f"https://lichess.org/api/puzzle/{puzzle_id}"
    resp = requests.get(url)
    log.debug(f"Fetching puzzle {puzzle_id}, status: {resp.status_code} {resp.text}")
    return resp


def is_puzzle_deleted(puzzle_id: str) -> bool:
    """Update a puzzle in the database, if deleted from lichess. return `True` if deleted"""
    resp = _internal_fetch_puzzle(puzzle_id) # type: ignore
    return resp.status_code == 404
