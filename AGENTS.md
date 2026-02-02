# AGENTS.md

## Build, Lint, and Test Commands

This project uses `uv` for dependency management and running commands, though standard `python` commands work if dependencies are installed.

### Dependencies
- **Install dependencies:** `uv sync` (or `pip install -r requirements.txt` if not using uv)
- **Add dependency:** `uv add <package>` (or `pip install <package>`)

### Testing
- **Run all tests:** `uv run -m unittest discover tests`
- **Run a single test file:** `uv run -m unittest tests/test.py`
- **Run a specific test case:** `uv run -m unittest tests.test.Test.test_parse_v5_onward_on_v6`
- **Run async tests:** `uv run -m unittest tests.test.TestChecker`

### Linting & Formatting
- **Format code:** `uv run black .`
- **Type check:** `uv run pyright`
- **Lint:** The project currently uses `pyright` for static analysis.

## Code Style Guidelines

### Imports
- Group imports: standard library, third-party libraries, local application.
- Use absolute imports for local modules where possible (e.g., `from check_puzzles_zulip.models import ...`).
- Avoid `*` imports.

### Formatting
- Follow PEP 8 guidelines.
- Use `black` for consistent code formatting.
- Indent using 4 spaces.
- Maximum line length is handled by black (default 88 characters).

### Typing
- Use type hints for function arguments and return values.
- Use `typing` module for complex types (`List`, `Dict`, `Optional`, `Union`, `Any`).
- Use `type: ignore` sparingly and only when necessary, preferably with a comment explaining why.

### Naming Conventions
- **Classes:** PascalCase (e.g., `PuzzleReport`, `ZulipClient`).
- **Functions/Methods:** snake_case (e.g., `parse_report_v5_onward`, `get_env_variable`).
- **Variables:** snake_case.
- **Constants:** UPPER_CASE (e.g., `STOCKFISH`, `ZULIP_CHANNEL`).
- **Private members:** Prefix with underscore (e.g., `_fetch_puzzle`, `__diskette_dir`).

### Error Handling
- Use `try...except` blocks for external operations (network requests, file I/O).
- Raise specific exceptions where appropriate.
- Log errors using the configured logger (`log.error(...)`).

### Database (SQLModel)
- Define models using `SQLModel` and `table=True`.
- Use `Field` for column definitions (primary keys, max lengths).
- Use `Session` for database interactions.
- Engine creation is handled by `setup_db`.

### Logging
- Use the project's logging setup from `check_puzzles_zulip.config`.
- Import logger: `from .config import setup_logger; log = setup_logger(__file__)`.
- Log levels: `DEBUG` for detailed info, `INFO` for general status.

### Testing
- Use `unittest` framework.
- Use `unittest.IsolatedAsyncioTestCase` for async tests.
- Mock external services (Zulip, Lichess API) where possible to avoid network dependency.
- Use `override_get_puzzle` for mocking puzzle data in checkers.
