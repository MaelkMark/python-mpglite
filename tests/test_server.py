from mpglite.server import Server, Room, User
from mpglite.client import Client
from testingutils import *


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