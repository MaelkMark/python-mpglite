from mpge.server import Server, Room, User


def room_started(room: Room):
    print(f'ROOM "{room.name}" STARTED!')

    players = {
        player.user_id: {"username": player.username, "score": 0}
        for player in room.players
    }
    player_ids = list(players.keys())

    options = ["K", "P", "O"]

    for round_idx in range(5):
        result = room.ask_everybody({"type": "move"})
        print("result:", result)
        a_player: User = room.users[player_ids[0]]
        b_player: User = room.users[player_ids[1]]
        a: str = result[player_ids[0]].upper()
        b: str = result[player_ids[1]].upper()

        # a: str = room.players[0].ask("Kő/papír/olló? (K/P/O) ").upper()
        # b: str = room.players[1].ask("Kő/papír/olló? (K/P/O) ").upper()

        print(a, b)

        a_index = options.index(a)
        b_index = options.index(b)

        if a_index == b_index:
            print("Draw!")
            a_player.send(
                {
                    "type": "round_result",
                    "move": a,
                    "opponent_move": b,
                    "result": "draw",
                    "score": players[player_ids[0]]["score"],
                }
            )
            b_player.send(
                {
                    "type": "round_result",
                    "move": b,
                    "opponent_move": a,
                    "result": "draw",
                    "score": players[player_ids[1]]["score"],
                }
            )
        elif (a_index - b_index) % 3 == 1:
            print(f"{players[player_ids[0]]['username']} wins!")
            players[player_ids[0]]["score"] += 1

            a_player.send(
                {
                    "type": "round_result",
                    "move": a,
                    "opponent_move": b,
                    "result": "win",
                    "score": players[player_ids[0]]["score"],
                }
            )
            b_player.send(
                {
                    "type": "round_result",
                    "move": b,
                    "opponent_move": a,
                    "result": "lose",
                    "score": players[player_ids[1]]["score"],
                }
            )
        else:
            print(f"{players[player_ids[1]]['username']} wins!")
            players[player_ids[1]]["score"] += 1
            a_player.send(
                {
                    "type": "round_result",
                    "move": a,
                    "opponent_move": b,
                    "result": "lose",
                    "score": players[player_ids[0]]["score"],
                }
            )
            b_player.send(
                {
                    "type": "round_result",
                    "move": b,
                    "opponent_move": a,
                    "result": "win",
                    "score": players[player_ids[1]]["score"],
                }
            )

    a_player.send(
        {
            "type": "game_result",
            "score": players[player_ids[0]]["score"],
            "opponent_score": players[player_ids[1]]["score"],
        }
    )
    b_player.send(
        {
            "type": "game_result",
            "score": players[player_ids[1]]["score"],
            "opponent_score": players[player_ids[0]]["score"],
        }
    )


if __name__ == "__main__":
    server = Server(
        "0.0.0.0",
        8767,
        logging=False,
        on_room_start=room_started,
    )
    # server.on_room_start = room_started
    server.start()
