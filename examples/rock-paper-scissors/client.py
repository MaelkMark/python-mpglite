from mpglite.client import Client
import mpglite.logger

from tabulate import tabulate
from time import sleep
import keyboard

status = "username"
moves = {"K": "🪨", "P": "📄", "O": "✂️"}

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
    print(repr(room))
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


def on_question(question, client: Client):
    match question["type"]:
        case "move":
            choice = decision("Kő/papír/olló?", ["K", "P", "O", "Q"])
            if choice == "Q":
                client.leave_room()
            else:
                return choice


def on_message(message):
    match message["type"]:
        case "round_result":
            if message["result"] == "win":
                print(f"{moves[message["move"]]}  vs {moves[message['opponent_move']]} : You won!")
            elif message["result"] == "lose":
                print(f"{moves[message["move"]]}  vs {moves[message['opponent_move']]} : You lost!")
            else:
                print(f"{moves[message["move"]]}  vs {moves[message['opponent_move']]} : Draw!")

            print(f"{message['score']} points!")
            
        case "game_result":
            print()
            print("Game over!")
            score = message["score"]
            opponent_score = message["opponent_score"]
            
            if score > opponent_score:
                print(f"You won the game!")
            elif score < opponent_score:
                print(f"You lost the game!")
            else:
                print(f"Draw!")
                
            print(f"Your score: {score}")
            print(f"Opponent's score: {opponent_score}")



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
        on_room_deleted=on_room_deleted
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
