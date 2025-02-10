def debug_get_puzzle():
    import chess
    import requests

    # from puzzle db
    input_ = "2F0QF,2R3Q1/pp4p1/6kp/5p2/3n4/q5P1/P4PK1/8 w - - 2 35,c8c7 a3f3 g2h2 f3f2 h2h3 f2f1 h3h4 f1h1,1506,75,99,2040,endgame,https://lichess.org/jVY3OWGP#69".split(
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
