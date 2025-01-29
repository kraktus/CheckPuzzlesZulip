from peewee import *

db = SqliteDatabase("check-puzzles-zulip.db")


class BaseModel(Model):
    class Meta:
        database = db


# xxx reported wfHlQ because (v6, SF 16 · 7MB) after move 17. f6, at depth 21, multiple solutions, pvs g5g3: 229, g5h6: 81, g5h4: -10, f4e6: -396, f4g6: -484
class PuzzleReport(BaseModel):
    _id = AutoField(primary_key=True)
    puzzle_id = FixedCharField(5) # maybe multiple reports about the same puzzle but not for the same move
    sf_version = CharField()
    zulip_message_id = CharField()
    move = IntegerField()  # move, not plies, starting from 1
    # for future compatibility and debugging
    report_text = TextField()
    issues = TextField()
    checked = BooleanField()


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


