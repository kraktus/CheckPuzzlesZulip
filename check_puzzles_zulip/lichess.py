import requests

from .models import Puzzle


# class Puzzle(BaseModel):
#     _id = FixedCharField(5, primary_key=True)
#     fen = CharField()
#     # initial_move = CharField()
#     initialPly = IntegerField()
#     solution = CharField()
#     # rating = IntegerField()
#     # popularity = IntegerField()
#     themes = TextField()
#     # game_url = CharField()
#     # game_id = CharField()
#     game_pgn = TextField()


def get_puzzle(puzzle_id: str) -> Puzzle:
    puzzle = Puzzle.objects.get_or_none(Puzzle._id == puzzle_id) # type: ignore
    if puzzle is not None:
        return puzzle
    puzzle = _fetch_puzzle(puzzle_id)
    puzzle.save()
    return puzzle


def _fetch_puzzle(puzzle_id: str) -> Puzzle:
    """Fetch a puzzle from lichess"""
    url = f"https://lichess.org/api/{puzzle_id}"
    response = requests.get(url).json()
    return Puzzle(
        _id=response["puzzle"]["id"],
        fen=response["puzzle"]["fen"],
        initialPly=response["puzzle"]["initialPly"],
        solution=response["puzzle"]["solution"],
        themes=response["puzzle"]["themes"],
        game_pgn=response["game"]["pgn"],
    )
