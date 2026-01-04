from mpglite.client import Client
import mpglite.logger

from tabulate import tabulate
from time import sleep
import keyboard
from random import randint
from functools import reduce

status = "username"
dice_chars = {1: "⚀", 2: "⚁", 3: "⚂", 4: "⚃", 5: "⚄", 6: "⚅"}
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


def decision(question, options):
    while True:
        choice = input(f"{question} ({"/".join(options)}) ").strip().upper()
        if choice in [option.upper() for option in options]:
            return choice
        else:
            print("Invalid option")


def confirm(question):
    return decision(question, ["Y", "N"]) == "Y"


def on_room_joined(room, client):
    print(f"Now you are in {room.name} {client.room.name}")


def on_room_started(room):
    print(f"The game begins!")


def on_room_ended(client: Client):
    global status

    print(f"The game has ended!")
    if confirm("Do you want to rematch?"):
        client.rematch()
    else:
        client.leave_room()
        status = "room_list"


def on_room_left(user, room, client):
    print(f"{user.username} left {room.name}")


def on_room_deleted(room_name):
    global status

    print(f"{room_name} has been deleted")
    status = "room_list"


def roll_to_string(roll: int) -> str:
    return roll
    return "".join([dice_chars[int(char)] for char in str(roll)])


def on_question(question):
    print("Question:", question)
    match question["type"]:
        case "believe":
            print(
                f"The previous player rolled {roll_to_string(question["previous_roll"])}"
            )
            return confirm("Do you believe?")

        case "roll":
            roll: int = int(
                reduce(
                    lambda a, c: a + str(c),
                    list(sorted([randint(1, 6), randint(1, 6)], reverse=True)),
                    "",
                )
            )

            roll_str: str = roll_to_string(roll)
            print(f"You rolled {roll_str}.")

            announced_roll: int = roll
            if roll != 21:
                while True:
                    res: str = None
                    
                    if question[
                        "previous_roll"
                    ] is None or possible_rolls.index(
                        roll
                    ) > possible_rolls.index(
                        question["previous_roll"]
                    ):
                        res = input(
                            "What do you want to announce? (Leave empty to tell the truth) "
                        )
                        if res == "":
                            announced_roll = roll
                            break
                    else:
                        res = input(
                            "What do you want to announce? (You must bluff, because you rolled less than the previous player) "
                        )

                    if res.isnumeric():
                        announced_roll = int(res)

                        if announced_roll not in possible_rolls:
                            print("Invalid roll!")
                            continue

                        if announced_roll == 21:
                            print("You can't bluff 21!")
                            continue

                        if question[
                            "previous_roll"
                        ] is not None and possible_rolls.index(
                            announced_roll
                        ) < possible_rolls.index(
                            question["previous_roll"]
                        ):
                            previous_roll_str = roll_to_string(
                                question["previous_roll"]
                            )
                            print(
                                f"You should announce a higher value than the previous {previous_roll_str} roll!"
                            )
                            continue

                        break
                    else:
                        print("You should input only a 2-digit number!")

            return {"roll": roll, "announced_roll": announced_roll}


def on_message(message, client):
    print("Message:", message)
    match message["type"]:
        case "lives":
            if message["lost"] == client.username:
                print("You lost a life!")
            else:
                print(f"{message["lost"]} lost a life!")




def main():
    global status

    client = Client(
        "localhost",
        8767,
        log_level=mpglite.logger.INFO,
        on_question=on_question,
        on_message=on_message,
        on_room_joined=on_room_joined,
        on_room_started=on_room_started,
        on_room_ended=on_room_ended,
        on_room_left=on_room_left,
        on_room_deleted=on_room_deleted,
    )
    client.connect()

    while True:
        match status:
            case "username":
                result = client.set_username(input("Choose a username: "))
                if result.ok:
                    status = "room_list"
                else:
                    print("Username already taken")
            case "room_list":
                if client.rooms_changed and len(client.rooms) > 0:
                    print(
                        tabulate(
                            [
                                [
                                    room.name,
                                    ", ".join(
                                        [player.username for player in room.players]
                                    ),
                                    room.status,
                                ]
                                for room in client.rooms
                            ],
                            headers=["Room Name", "Players", "Status"],
                            tablefmt="rounded_grid",
                        )
                    )
                    if (
                        decision(
                            "Do you want to join, or create a new room", ["J", "C"]
                        )
                        == "J"
                    ):
                        status = "room_join"
                    else:
                        status = "room_create"
                else:
                    if confirm("No rooms available. Do you want to create a new room?"):
                        status = "room_create"
                    else:
                        print(
                            "Press [C] if you changed your mind. Waiting for a new room."
                        )
                        status = "wait_for_new_room"
            case "room_join":
                room_name = input("Room name: ")
                result = client.join_room(room_name)
                if result.ok:
                    status = "room_joined"
                else:
                    print(result.error_message)
            case "wait_for_new_room":
                if client.rooms_changed or keyboard.is_pressed("c"):
                    status = "room_list"
            case "room_create":
                name = input("Room name: ")
                result = client.create_room(name, max_players=2)
                if result.ok:
                    status = "room_joined"
                else:
                    print(result.error_message)
            case "room_joined":
                pass
            case _:
                print("Error: invalid status")

        sleep(0.1)


if __name__ == "__main__":
    main()
