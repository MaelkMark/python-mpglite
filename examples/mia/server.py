from mpglite.server import Server, Room, User
from mpglite.exceptions import UserLeftError
from mpglite.logger import Loglevel


def room_started(room: Room):
    print(f'ROOM "{room.name}" STARTED!')

    players = {player: {"player": player, "lives": 3} for player in room.players}

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
            try:
                player: dict = players[player]

                believes: bool = True
                if prev_roll and prev_roll["roll"] != 21:
                    print("Previous roll:", prev_roll)
                    believes = player["player"].ask(
                        {
                            "type": "believe",
                            "previous_roll": prev_roll["announced_roll"],
                            "previous_username": prev_roll["player"].username,
                        }
                    )
                    print("believes:", believes)

                if believes and (prev_roll is None or prev_roll["roll"] != 21):
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
                    print(
                        "Prev:",
                        prev_roll,
                        prev_roll["announced_roll"] == prev_roll["roll"],
                    )
                    user_lost: User | None = None
                    if prev_roll["announced_roll"] == prev_roll["roll"] or prev_roll["roll"] == 21:
                        user_lost = player["player"]
                    else:
                        user_lost = players[prev_roll["player"]]["player"]

                    players[user_lost]["lives"] -= 1
                    print(f"{user_lost.username} lost a life!")
                    room.broadcast(
                        {
                            "type": "lives",
                            "lost": user_lost.username,
                            "lives": {
                                player["player"].username: player["lives"]
                                for player in players.values()
                            },
                        }
                    )

                    if players[user_lost]["lives"] == 0:
                        room.broadcast(
                            {"type": "player_died", "username": user_lost.username}
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
        loglevel=Loglevel.DEBUG,
        on_room_start=room_started,
        on_room_left=room_left,
    )
    # server.on_room_start = room_started
    server.start()
