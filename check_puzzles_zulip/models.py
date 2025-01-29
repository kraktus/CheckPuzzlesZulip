from peewee import (
    Model,
    FixedCharField,
    CompositeKey,
    CharField,
    IntegerField,
    TextField,
    BooleanField,
    AutoField,
    SqliteDatabase,
)

from dataclasses import dataclass

db = SqliteDatabase("check-puzzles-zulip.db")


class BaseModel(Model):
    class Meta:
        database = db


@dataclass(frozen=True)
class PuzzleReport:
    reporter: str
    puzzle_id: str
    report_version: int
    sf_version: str
    move: int
    details: str
    issues: str
    local_evaluation: str
    zulip_message_id: int

    def to_model(self):
        return PuzzleReportDb(
            reporter=self.reporter,
            puzzle_id=self.puzzle_id,
            report_version=self.report_version,
            sf_version=self.sf_version,
            move=self.move,
            details=self.details,
            issues=self.issues,
            local_evaluation=self.local_evaluation,
            zulip_message_id=self.zulip_message_id,
        )


class PuzzleReportDb(BaseModel):
    reporter = CharField()
    puzzle_id = FixedCharField(
        5
    )  # maybe multiple reports about the same puzzle but not for the same move
    report_version = IntegerField()
    # not present before v5
    sf_version = CharField()
    zulip_message_id = CharField()
    move = IntegerField()  # move, not plies, starting from 1
    # for future compatibility and debugging
    details = TextField()
    issues = TextField()
    # cache for local sf eval at the end, to inspect
    # if empty, has not been analyzed
    local_evaluation = TextField()

    class Meta:
        primary_key = CompositeKey("puzzle_id", "move")


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
    fen = CharField()
    # initial_move = CharField()
    initialPly = IntegerField()
    solution = CharField()
    # rating = IntegerField()
    # popularity = IntegerField()
    themes = TextField()
    # game_url = CharField()
    # game_id = CharField()
    game_pgn = TextField()
    # game_fen = CharField()
    # game_moves = IntegerField()
    # game_rating = IntegerField()
    # game_result = CharField()
    # game_date = DateTimeField()
    # game_turns = IntegerField()
    # game_speed = CharField()
    # game_perf = CharField()
    # game_opening = CharField()
    # game_eco = CharField()
    # game_analyzed = BooleanField()
    # game_annotated = BooleanField()
    # game_truncated = BooleanField()
    # game_moves_truncated = IntegerField()
    # game_moves_truncated_reason = CharField


def setup_db():
    db.create_tables([PuzzleReport, Puzzle])
