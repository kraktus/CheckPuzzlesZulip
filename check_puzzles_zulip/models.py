import chess

from datetime import datetime
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

    # Issue tracking - datetime when each issue was detected (None if not detected)
    has_multiple_solutions: Optional[datetime] = None
    has_missing_mate_theme: Optional[datetime] = None
    is_deleted_from_lichess: Optional[datetime] = None

    def is_multiple_solutions_detected(self) -> bool:
        """Check if multiple solutions issue is set"""
        return self.has_multiple_solutions is not None

    def is_missing_mate_theme_detected(self) -> bool:
        """Check if missing mate theme issue is set"""
        return self.has_missing_mate_theme is not None

    def is_deleted_detected(self) -> bool:
        """Check if deleted from lichess issue is set"""
        return self.is_deleted_from_lichess is not None

    @property
    def issues(self) -> int:
        """Compatibility property that returns bitfield representation"""
        result = 0
        if self.has_multiple_solutions is not None:
            result |= 1
        if self.has_missing_mate_theme is not None:
            result |= 2
        if self.is_deleted_from_lichess is not None:
            result |= 4
        return result

    def debug_str(self) -> str:
        return f"PuzzleReport({self.zulip_message_id}, {self.reporter}, {self.puzzle_id}, {self.move}, is_deleted_from_lichess={self.is_deleted_from_lichess})"


class Puzzle(SQLModel, table=True):
    __tablename__ = "puzzle"  # type: ignore

    id: str = Field(primary_key=True, max_length=5, sa_column_kwargs={"name": "_id"})
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
