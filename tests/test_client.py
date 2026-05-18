from unittest.mock import MagicMock
from mpglite.client import Client
from mpglite.message import ErrorMessage, Message
import mpglite
from conftest import PORT
from testingutils import *


def test_username_modification(client_a: Client):
    """Verify the username can be changed."""
    response = client_a.set_username("TestUser")
    assert isinstance(response, Message), "Response is not a Message object"
    assert response.ok, "Response is not OK"
    assert client_a.username == "TestUser", "Username was not changed"


def test_username_taken(client_b: Client):
    """Verify multiple clients can't have the same username."""
    response = client_b.set_username("TestUser")
    assert isinstance(response, ErrorMessage), "Response is not an ErrorMessage object"
    assert response.error_code == "ERR_USERNAME_TAKEN", "Error code is not correct"


def test_room_list(client_a: Client):
    """Verify client.rooms is correct."""
    assert isinstance(client_a.rooms, list), "client.rooms is not a list"
    assert len(client_a.rooms) == 0, "client.rooms is not empty"


def test_rooms_changed(temp_client_a: Client, temp_client_b: Client):
    assert temp_client_a.rooms_changed == True

    assert len(temp_client_a.rooms) == 0
    assert temp_client_a.rooms_changed == False

    temp_client_b.create_room("TempRoom")
    assert temp_client_a.rooms_changed == True


def test_user_list(client_a: Client):
    """Verify client.users is correct."""
    assert isinstance(client_a.users, list), "client.users is not a list"
    assert len(client_a.users) > 1, "client.users is not correct length"
    assert all(
        isinstance(user, mpglite.client.User) for user in client_a.users
    ), "client.users contains non-User objects"


def test_users_changed(temp_client_a: Client):
    assert temp_client_a.users_changed == True

    assert len(temp_client_a.users) > 0
    assert temp_client_a.users_changed == False

    new_client = Client("localhost", PORT)
    new_client.connect()
    assert temp_client_a.users_changed == True


def test_create_room(client_a: Client):
    """Test room creation."""
    response = client_a.create_room("TestRoom")
    assert isinstance(response, Message), "Response is not a Message object"
    assert response.ok, "Response is not OK"
    assert isinstance(
        client_a.room, mpglite.client.Room
    ), "client.room is not a Room object"
    assert client_a.room.name == "TestRoom", "Room name is not correct"


def test_join_nonexistent_room(client_b: Client):
    """Verify joining a nonexistent room fails."""
    response = client_b.join_room("NonexistentRoom")
    assert isinstance(response, ErrorMessage), "Response is not an ErrorMessage object"
    assert response.error_code == "ERR_NO_SUCH_ROOM", "Error code is not correct"


def test_start_nonexistent_room(temp_client_a: Client):
    """Verify starting a nonexistent room fails."""
    response = temp_client_a._ask(mpglite.message.StartRoomMessage("NonexistentRoom"))
    assert isinstance(response, ErrorMessage), "Response is not an ErrorMessage object"
    assert response.error_code == "ERR_NO_SUCH_ROOM", "Error code is not correct"


def test_client_join_room(client_b: Client):
    """Test joining a room."""
    response = client_b.join_room("TestRoom")
    assert isinstance(response, Message), "Response is not a Message object"
    assert response.ok, "Response is not OK"
    assert isinstance(
        client_b.room, mpglite.client.Room
    ), "client.room is not a Room object"
    assert client_b.room.name == "TestRoom", "Room name is not correct"


def test_client_leave_room(client_b: Client):
    """Test leaving a room."""
    response = client_b.leave_room()
    assert isinstance(response, Message), "Response is not a Message object"
    assert response.ok, "Response is not OK"
    assert client_b.room is None, "client.room is not None"


def test_client_leave_lobby(temp_client_a: Client):
    """Test leaving a room."""
    response = temp_client_a.leave_room()
    assert isinstance(response, ErrorMessage), "Response is not an ErrorMessage object"
    assert response.error_code == "ERR_LOBBY_CANNOT_BE_LEFT", "Error code is not correct"


def test_room_join(client_b: Client):
    """Test joining a room."""
    response = client_b.get_room_by_name("TestRoom").join()
    assert isinstance(response, Message), "Response is not a Message object"
    assert response.ok, "Response is not OK"
    assert isinstance(
        client_b.room, mpglite.client.Room
    ), "client.room is not a Room object"
    assert client_b.room.name == "TestRoom", "Room name is not correct"


def test_room_leave(client_b: Client):
    """Test leaving a room."""
    response = client_b.room.leave()
    assert isinstance(response, Message), "Response is not a Message object"
    assert response.ok, "Response is not OK"
    assert client_b.room is None, "client.room is not None"


def test_get_room_by_name(temp_client_a: Client):
    """Test Client.get_room_by_name."""
    room = temp_client_a.get_room_by_name("TestRoom")
    assert isinstance(room, mpglite.client.Room), "Room is not a Room object"
    assert room.name == "TestRoom", "Room name is not correct"


def test_get_room_by_name_nonexistent(temp_client_a: Client):
    """Test Client.get_room_by_name."""
    room = temp_client_a.get_room_by_name("NonexistentRoom")
    assert room is None


def test_get_user_by_id(temp_client_a: Client):
    """Test Client.get_user_by_id."""
    user = temp_client_a.get_user_by_id(temp_client_a.user_id)
    assert isinstance(user, mpglite.client.User), "User is not a User object"
    assert user.user_id == temp_client_a.user_id, "User ID is not correct"


def test_get_user_by_id_nonexistent(temp_client_a: Client):
    """Test Client.get_user_by_id."""
    user = temp_client_a.get_user_by_id(123456789)
    assert user is None


def test_get_user_by_username(temp_client_a: Client):
    """Test Client.get_user_by_username."""
    user = temp_client_a.get_user_by_username(temp_client_a.username)
    assert isinstance(user, mpglite.client.User), "User is not a User object"
    assert user.username == temp_client_a.username, "Username is not correct"


def test_get_user_by_username_nonexistent(temp_client_a: Client):
    """Test Client.get_user_by_id."""
    user = temp_client_a.get_user_by_username(123456789)
    assert user is None
