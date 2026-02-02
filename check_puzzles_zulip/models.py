import chess

from datetime import datetime
from typing import Optional, TypedDict
from sqlmodel import SQLModel, Field, create_engine, Session, select
from sqlalchemy.engine import Engine


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

    def get_issues(self) -> list[str]:
        """Get list of detected issues"""
        issues = []
        if self.is_multiple_solutions_detected():
            issues.append("multiple_solutions")
        if self.is_missing_mate_theme_detected():
            issues.append("missing_mate_theme")
        if self.is_deleted_detected():
            issues.append("deleted_from_lichess")
        return issues

    def debug_str(self) -> str:
        return f"PuzzleReport({self.zulip_message_id}, {self.reporter}, {self.puzzle_id}, {self.move}, is_deleted_from_lichess={self.is_deleted_from_lichess})"


class Puzzle(SQLModel, table=True):
    __tablename__ = "puzzle"  # type: ignore

    lichess_id: str = Field(primary_key=True, max_length=5)
    initialPly: Optional[int] = None
    solution: Optional[str] = None
    themes: Optional[str] = None  # themes, separated by spaces
    game_pgn: Optional[str] = None  # moves, separated by spaces

    # Datetime when puzzle was deleted from lichess (None if not deleted)
    deleted_at: Optional[datetime] = None

    def is_deleted(self) -> bool:
        """Check if puzzle is deleted"""
        return self.deleted_at is not None

    def color_to_win(self) -> chess.Color:
        return chess.WHITE if self.initialPly % 2 == 1 else chess.BLACK  # type: ignore


def setup_db(name: str) -> Engine:
    """Create and initialize database engine"""
    engine = create_engine(f"sqlite:///{name}")
    SQLModel.metadata.create_all(engine)
    return engine
