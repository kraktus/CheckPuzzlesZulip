import chess
from typing import TypedDict, Optional
from sqlmodel import SQLModel, Field, create_engine, Session


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


class PuzzleReport(SQLModel, table=True):
    __tablename__ = "puzzlereport"
    
    zulip_message_id: str = Field(primary_key=True)
    reporter: str
    puzzle_id: str = Field(max_length=5)  # FixedCharField(5) equivalent
    report_version: int
    sf_version: str
    move: int  # move, not plies, starting from 1
    details: str  # TextField equivalent

    # if the report has been checked
    # not necessarily equal to `local_evaluation == ""`
    # in case the report is a duplicate, or deleted
    checked: bool = Field(default=False)
    
    # cache for local sf eval at the end, to inspect
    # if empty, has not been analyzed
    local_evaluation: str = Field(default="")
    
    # Converting BitField to separate boolean fields for better type safety
    has_multiple_solutions: bool = Field(default=False)
    has_missing_mate_theme: bool = Field(default=False)
    is_deleted_from_lichess: bool = Field(default=False)

    def debug_str(self) -> str:
        return f"PuzzleReport({self.zulip_message_id}, {self.reporter}, {self.puzzle_id}, {self.move}, is_deleted_from_lichess={self.is_deleted_from_lichess})"


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
class Puzzle(SQLModel, table=True):
    __tablename__ = "puzzle"
    
    _id: str = Field(primary_key=True, max_length=5)  # FixedCharField(5) equivalent
    initialPly: Optional[int] = Field(default=None)
    solution: Optional[str] = Field(default=None)
    themes: Optional[str] = Field(default=None)  # themes, separated by spaces
    game_pgn: Optional[str] = Field(default=None)  # moves, separated by spaces
    
    # Converting BitField to boolean field
    is_deleted: bool = Field(default=False)

    def color_to_win(self) -> chess.Color:
        return chess.WHITE if self.initialPly % 2 == 1 else chess.BLACK  # type: ignore


# Global engine variable
engine = None


def setup_db(name: str):
    global engine
    
    if name == ":memory:":
        database_url = "sqlite:///:memory:"
    else:
        database_url = f"sqlite:///{name}"
    
    engine = create_engine(database_url, echo=False)
    SQLModel.metadata.create_all(engine)
    return engine


def get_session() -> Session:
    global engine
    if engine is None:
        raise RuntimeError("Database not initialized. Call setup_db first.")
    return Session(engine)
