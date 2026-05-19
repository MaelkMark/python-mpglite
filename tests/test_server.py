import threading

from mpglite.server import Server, Room, User
from mpglite.logger import Loglevel
from mpglite.client import Client
from mpglite.message import Message, ErrorMessage
from testingutils import *
from conftest import LOGLEVEL, PORT


def test_room_user_or_id(server: Server, temp_client_a: Client):
    room: Room = server.rooms["lobby"]
    user: User = server.users[temp_client_a.user_id]
    assert room._user_or_id(user) == user, "Fails for User object"
    assert room._user_or_id(user.user_id) == user, "Fails for User ID"


def test_server_user_or_id(server: Server, temp_client_a: Client):
    user: User = server.users[temp_client_a.user_id]
    assert server._user_or_id(user) == user, "Fails for User object"
    assert server._user_or_id(user.user_id) == user, "Fails for User ID"


def test_room_user_in_room(server: Server, temp_client_a: Client):
    room: Room = server.rooms["lobby"]
    user: User = server.users[temp_client_a.user_id]
    assert room.user_in_room(user) == True, "Fails for User object"
    assert room.user_in_room(user.user_id) == True, "Fails for User ID"


def test_print_logo(capsys):
    # Test that the logo is printed when print_logo is True
    Server(host="localhost", port=PORT, print_logo=True, loglevel=Loglevel.OFF)
    captured = capsys.readouterr()
    assert captured.out != "", "Logo was expected to be printed to stdout."

    # Test that the logo is not printed when print_logo is False
    Server(host="localhost", port=PORT, print_logo=False, loglevel=Loglevel.OFF)
    captured = capsys.readouterr()
    assert captured.out == "", "Logo was not expected to be printed to stdout."


def test_server_room_delete_room(server: Server, temp_client_a: Client):
    ROOM_NAME = "TestRoom"
    temp_client_a.create_room(ROOM_NAME)
    room: Room = server.rooms[ROOM_NAME]
    response = room.delete()
    assert isinstance(response, Message), "Response is not a Message object"
    assert response.ok, "Response is not OK"
    assert response.type == "room_deleted", "Response type is not correct"
    assert ROOM_NAME not in server.rooms, "Room was not deleted"


def test_server_delete_room(server: Server, temp_client_a: Client):
    ROOM_NAME = "TestRoom"
    temp_client_a.create_room(ROOM_NAME)
    response = server._delete_room(ROOM_NAME)
    assert isinstance(response, Message), "Response is not a Message object"
    assert response.ok, "Response is not OK"
    assert response.type == "room_deleted", "Response type is not correct"
    assert ROOM_NAME not in server.rooms, "Room was not deleted"


def test_server_delete_lobby(server: Server):
    response = server._delete_room("lobby")
    assert isinstance(response, Message), "Response is not a Message object"
    assert isinstance(response, ErrorMessage), "Response is not an ErrorMessage"
    assert response.error_code == "ERR_LOBBY_CANNOT_BE_DELETED", "Error code is not correct"


def test_server_delete_nonexistent_room(server: Server):
    response = server._delete_room("NonexistentRoom")
    assert isinstance(response, Message), "Response is not a Message object"
    assert isinstance(response, ErrorMessage), "Response is not an ErrorMessage"
    assert response.error_code == "ERR_NO_SUCH_ROOM", "Error code is not correct"