import chess

from typing import Optional, TypedDict
from sqlmodel import SQLModel, Field, create_engine, Session, select


# TypedDict for bulk insert operations
class PuzzleReportDict(TypedDict):
    reporter: str
    puzzle_id: str
    report_version: int
    sf_version: str
    zulip_message_id: int
    move: int
    details: str
    local_evaluation: str
    issues: str


class PuzzleReport(SQLModel, table=True):
    __tablename__ = "puzzlereport"  # type: ignore

    zulip_message_id: str = Field(primary_key=True)
    reporter: str
    puzzle_id: str = Field(max_length=5)
    report_version: int
    sf_version: str = ""
    move: int  # move, not plies, starting from 1
    details: str  # for future compatibility and debugging

    # if the report has been checked
    # not necessarily equal to `local_evaluation == ""`
    # in case the report is a duplicate, or deleted
    checked: bool = False
    # cache for local sf eval at the end, to inspect
    # if empty, has not been analyzed
    local_evaluation: str = ""

    # Bitfield flags stored as integer
    issues: int = 0

    @property
    def has_multiple_solutions(self) -> bool:
        return bool(self.issues & 1)

    @has_multiple_solutions.setter
    def has_multiple_solutions(self, value: bool) -> None:
        if value:
            self.issues |= 1
        else:
            self.issues &= ~1

    @property
    def has_missing_mate_theme(self) -> bool:
        return bool(self.issues & 2)

    @has_missing_mate_theme.setter
    def has_missing_mate_theme(self, value: bool) -> None:
        if value:
            self.issues |= 2
        else:
            self.issues &= ~2

    @property
    def is_deleted_from_lichess(self) -> bool:
        return bool(self.issues & 4)

    @is_deleted_from_lichess.setter
    def is_deleted_from_lichess(self, value: bool) -> None:
        if value:
            self.issues |= 4
        else:
            self.issues &= ~4

    def debug_str(self) -> str:
        return f"PuzzleReport({self.zulip_message_id}, {self.reporter}, {self.puzzle_id}, {self.move}, is_deleted_from_lichess={self.is_deleted_from_lichess})"


class Puzzle(SQLModel, table=True):
    __tablename__ = "puzzle"  # type: ignore

    _id: str = Field(primary_key=True, max_length=5)
    initialPly: Optional[int] = None
    solution: Optional[str] = None
    themes: Optional[str] = None  # themes, separated by spaces
    game_pgn: Optional[str] = None  # moves, separated by spaces

    # Bitfield flags stored as integer
    status: int = 0

    @property
    def is_deleted(self) -> bool:
        return bool(self.status & 1)

    @is_deleted.setter
    def is_deleted(self, value: bool) -> None:
        if value:
            self.status |= 1
        else:
            self.status &= ~1

    def color_to_win(self) -> chess.Color:
        return chess.WHITE if self.initialPly % 2 == 1 else chess.BLACK  # type: ignore


# Global engine - will be initialized by setup_db
engine = None


def setup_db(name: str):
    global engine
    engine = create_engine(f"sqlite:///{name}")
    SQLModel.metadata.create_all(engine)
    return engine


def get_session() -> Session:
    """Get a new database session"""
    if engine is None:
        raise RuntimeError("Database not initialized. Call setup_db() first.")
    return Session(engine)
