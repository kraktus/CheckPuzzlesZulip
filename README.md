# Check-puzzles-zulip

A small zulip bot that checks if the puzzles reported by WASM SF from lichess clients have multiple solutions.


## How to run

1. Install `uv` (can do `pip install uv`)
2. `uv sync`
3. `uv run -m check-puzzles-zulip`

## How to use

check `.env.base`, create `.env` with the same variables, and fill them with the correct values.

run: `uv run -m check_puzzles_zulip run <command>`

test `uv run -m unittest tests/test.py`

format `uv run black .`

typecheck: `uv run pyright .`