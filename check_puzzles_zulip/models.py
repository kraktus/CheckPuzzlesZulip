import chess

from typing import TypedDict

from peewee import (
    Model,
    FixedCharField,
    CompositeKey,
    CharField,
    IntegerField,
    TextField,
    BooleanField,
    BitField,
    AutoField,
    SqliteDatabase,
)


db = SqliteDatabase(None)


class BaseModel(Model):
    class Meta:
        database = db


# needed to allow to use insert_many in db...
class PuzzleReportDict(TypedDict):
    reporter: str
    puzzle_id: str
    report_version: int
    sf_version: str
    zulip_message_id: int
    move: int
    details: str
    # Those should not be set otherwise than ""
    local_evaluation: str
    issues: str


class PuzzleReport(BaseModel):
    zulip_message_id = CharField(primary_key=True)
    reporter = CharField()
    puzzle_id = FixedCharField(
        5
    )  # maybe multiple reports about the same puzzle but not for the same move
    report_version = IntegerField()
    # not present before v5
    sf_version = CharField()
    move = IntegerField()  # move, not plies, starting from 1
    # for future compatibility and debugging
    details = TextField()

    # if the report has been checked
    # not necessarily equal to `local_evaluation == ""`
    # in case the report is a duplicate
    checked = BooleanField(default=False)
    # cache for local sf eval at the end, to inspect
    # if empty, has not been analyzed
    local_evaluation = TextField()

    issues = BitField()
    has_multiple_solutions = issues.flag(1)
    has_missing_mate_theme = issues.flag(2)


# taken from the lichess api
# https://lichess.org/api/puzzle/{id}
# {
# "game": {
# "clock": "3+0",
# "id": "AHGPPS44",
# "perf": {},
# "pgn": "d4 d5 Bf4 Bf5 Nf3 e6 c4 Nf6 Nc3 Bd6 Bg3 Nbd7 e3 O-O c5 Bxg3 hxg3 h6 Bd3 Ne4 Qc2 Ndf6 Nd2 Nxc3 Bxf5 exf5 bxc3 Ne4 Nxe4 fxe4 Rb1 b6 Rh5 bxc5 Rb5 cxd4 cxd4 c6 Qxc6 Rc8 Qxd5 Qf6 Qxe4 Rc1+ Ke2 Qa6 Qd5 Rc2+ Kf3 g6 Rxh6 Qf6+ Ke4",
# "players": [
# {},
# {}
# ],
# "rated": true
# },
# "puzzle": {
# "id": "PSjmf",
# "initialPly": 52,
# "plays": 566,
# "rating": 2705,
# "solution": [
# "g8g7",
# "d5e5",
# "f6e5"
# ],
# "themes": [
# "endgame",
# "master",
# "short",
# "masterVsMaster",
# "crushing"
# ]
# }
# }
class Puzzle(BaseModel):
    _id = FixedCharField(5, primary_key=True)
    initialPly = IntegerField()
    solution = CharField()
    # themes, separated by spaces
    themes = TextField()
    # moves, separated by spaces
    game_pgn = TextField()

    def color_to_win(self) -> chess.Color:
        return chess.WHITE if self.initialPly % 2 == 1 else chess.BLACK  # type: ignore


def setup_db(name: str = "check_puzzles_zulip.db"):
    db.init(name)
    db.connect()
    db.create_tables([PuzzleReport, Puzzle])
    # import time
    # time.sleep(15)
    return db
