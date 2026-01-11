from unittest.mock import MagicMock
from mpglite.client import Client
from mpglite.message import ErrorMessage, Message
import mpglite


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


def test_user_list(client_a: Client):
    """Verify client.users is correct."""
    assert isinstance(client_a.users, list), "client.users is not a list"
    assert len(client_a.users) == 2, "client.users is not correct length"
    assert all(
        isinstance(user, mpglite.client.User) for user in client_a.users
    ), "client.users contains non-User objects"


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


def test_get_room_by_name(temp_client: Client):
    """Test Client.get_room_by_name."""
    room = temp_client.get_room_by_name("TestRoom")
    assert isinstance(room, mpglite.client.Room), "Room is not a Room object"
    assert room.name == "TestRoom", "Room name is not correct"


def test_get_room_by_name_nonexistent(temp_client: Client):
    """Test Client.get_room_by_name."""
    room = temp_client.get_room_by_name("NonexistentRoom")
    assert room is None


def test_get_user_by_id(temp_client: Client):
    """Test Client.get_user_by_id."""
    user = temp_client.get_user_by_id(temp_client.user_id)
    assert isinstance(user, mpglite.client.User), "User is not a User object"
    assert user.user_id == temp_client.user_id, "User ID is not correct"


def test_get_user_by_id_nonexistent(temp_client: Client):
    """Test Client.get_user_by_id."""
    user = temp_client.get_user_by_id(123456789)
    assert user is None


def test_get_user_by_username(temp_client: Client):
    """Test Client.get_user_by_username."""
    user = temp_client.get_user_by_username(temp_client.username)
    assert isinstance(user, mpglite.client.User), "User is not a User object"
    assert user.username == temp_client.username, "Username is not correct"


def test_get_user_by_username_nonexistent(temp_client: Client):
    """Test Client.get_user_by_id."""
    user = temp_client.get_user_by_username(123456789)
    assert user is None