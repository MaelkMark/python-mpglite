import threading

from mpglite.server import Server, Room, User
from mpglite.logger import Loglevel
from mpglite.client import Client
from testingutils import *
from tests.conftest import LOGLEVEL, PORT


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