from mpglite.server import Server, Room, User
from mpglite.exceptions import UserLeftError
import mpglite.logger


def room_started(room: Room):
    print(f'ROOM "{room.name}" STARTED!')

    players = {player: {"player": player, "lives": 6} for player in room.players}

    possible_rolls = [
        31,
        32,
        34,
        35,
        36,
        41,
        42,
        43,
        45,
        46,
        51,
        52,
        53,
        54,
        56,
        61,
        62,
        63,
        64,
        65,
        11,
        22,
        33,
        44,
        55,
        66,
        21,
    ]

    try:
        prev_roll: None | dict[str, int] = None

        while True:
            alive_players = [
                player["player"]
                for player in players.values()
                if player["lives"] > 0 and player["player"] in room.current_players
            ]

            if len(alive_players) < 2:
                break

            for player in alive_players:
                player: dict = players[player]

                believes: bool = True
                if prev_roll:
                    print("Previous roll:", prev_roll)
                    believes = player["player"].ask(
                        {
                            "type": "believe",
                            "previous_roll": prev_roll["announced_roll"],
                            "previous_username": prev_roll["player"].username,
                        }
                    )
                    print("believes:", believes)

                if believes:
                    roll = player["player"].ask(
                        {
                            "type": "roll",
                            "previous_roll": (
                                prev_roll["announced_roll"] if prev_roll else None
                            ),
                        }
                    )

                    print("roll:", roll)

                    prev_roll = {"player": player["player"], **roll}
                    print("prev_roll:", prev_roll)
                else:
                    if prev_roll["announced_roll"] == prev_roll["roll"]:
                        player["lives"] -= 1
                        print(f"{player['player'].username} lost a life!")
                        room.broadcast(
                            {
                                "type": "lives",
                                "lost": prev_roll['player'].username,
                                "lives": {
                                    player["player"].username: player["lives"]
                                    for player in players.values()
                                },
                            }
                        )
                    else:
                        players[prev_roll["player"]]["lives"] -= 1
                        print(f"{prev_roll['player'].username} lost a life!")
                        room.broadcast(
                            {
                                "type": "lives",
                                "lost": prev_roll['player'].username,
                                "lives": {
                                    player["player"].username: player["lives"]
                                    for player in players.values()
                                },
                            }
                        )

                    prev_roll = None
                    
                    roll = player["player"].ask(
                        {
                            "type": "roll",
                            "previous_roll": None,
                        }
                    )

                    print("roll:", roll)

                    prev_roll = {"player": player["player"], **roll}
                    print("prev_roll:", prev_roll)

        room.end()
    except UserLeftError:
        print("A user left the game")
        room.end()


def room_left(room: Room, user: User) -> bool:
    print(f'{user.username} left the room "{room.name}"')
    if len(room.current_players) < 2:
        print(f'Deleting room "{room.name}"')
        return True
    return False


if __name__ == "__main__":
    server = Server(
        "0.0.0.0",
        8767,
        log_level=mpglite.logger.DEBUG,
        on_room_start=room_started,
        on_room_left=room_left,
    )
    # server.on_room_start = room_started
    server.start()
