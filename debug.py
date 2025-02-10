def debug_get_puzzle():
    import chess
    import requests

    # from puzzle db
    input_ = "5YpsY,3R3Q/1p2rk1p/p1p3p1/4pp2/7q/7P/P4PP1/6K1 b - - 9 31,e5e4 g2g3 h4h6 h8g8 f7f6 d8d6 f6g5 g8d8,2797,99,91,1555,clearance crushing endgame master pin veryLong,https://lichess.org/l0224RLL/black#62".split(
        ","
    )
    puzzle_id = input_[0]
    fen = input_[1]
    solutions = input_[2]
    themes = input_[7]
    game_id = input_[8].replace("/black", "").split("/")[-1].partition("#")[0]
    print("GAME ID", game_id)

    # with content type json header, GET https://lichess.org/game/export/{gameId}
    headers = {
        "Accept": "application/json",
    }
    req = requests.get(f"https://lichess.org/game/export/{game_id}", headers=headers)
    print("RAW REQ", req, req.text)
    json = req.json()
    board = chess.Board()
    game_pgn = []
    for san_move in json["moves"].split():
        board.push_san(san_move)
        game_pgn.append(san_move)
        if board.fen() == fen:
            print("BREAK")
            break

    # print all fields
    print(
        f"Puzzle(_id=\"{puzzle_id}\", initialPly={len(game_pgn)}, solution=\"{solutions}\", themes=\"{themes}\", game_pgn=\"{' '.join(game_pgn)}\")"
    )


if __name__ == "__main__":
    print("#" * 80)
    debug_get_puzzle()
