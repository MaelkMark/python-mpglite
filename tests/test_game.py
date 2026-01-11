from unittest.mock import MagicMock
from mpglite.client import Client
from mpglite.server import Server
from testingutils import *
import mpglite


def test_room_auto_start(temp_client: Client, temp_client2: Client):
    temp_client.create_room("TempRoom", max_players=2, auto_start=True)
    assert temp_client.room.name == "TempRoom"
    assert (
        temp_client.room.status != "started"
    ), "Room started without reaching max players"

    temp_client2.join_room("TempRoom")
    assert temp_client2.room.name == "TempRoom"
    assert temp_client.room.status == "started", "Room did not start"


def test_room_auto_start_disabled(temp_client: Client, temp_client2: Client):
    temp_client.create_room("TempRoom", max_players=2, auto_start=False)
    temp_client2.join_room("TempRoom")
    assert temp_client.room.name == "TempRoom"
    assert temp_client2.room.name == "TempRoom"
    assert temp_client.room.status != "started", "Room started with auto_start disabled"


def test_room_deletion(temp_client: Client):
    temp_client.create_room("TempRoom")
    assert isinstance(temp_client.leave_room(), mpglite.message.RoomLeftMessage)
    assert temp_client.get_room_by_name("TempRoom") is None
    assert temp_client.room is None


def test_room_start(temp_client: Client):
    temp_client.create_room("TempRoom", min_players=1)
    result = temp_client.room.start()
    assert isinstance(result, mpglite.message.RoomStartedMessage)
    assert temp_client.room.status == "started"


def test_room_start_not_enough_players(temp_client: Client):
    temp_client.create_room("TempRoom", min_players=2)
    result = temp_client.room.start()
    assert isinstance(result, mpglite.message.ErrorMessage)
    assert result.error_code == "ERR_NOT_ENOUGH_PLAYERS"
    assert temp_client.room.status == "open"


def test_room_end(temp_client: Client):
    temp_client.create_room("TempRoom", min_players=1)
    temp_client.room.start()
    result = temp_client.room.end()
    assert isinstance(result, mpglite.message.RoomEndedMessage)
    assert temp_client.room.status == "ended"




def test_on_room_joined(temp_client: Client):
    temp_client.on_room_joined = MagicMock()
    
    temp_client.create_room("TempRoom")
    
    temp_client.on_room_joined.assert_called_once()
    temp_client.on_room_joined.assert_called_once()
    _, kwargs = temp_client.on_room_joined.call_args
    assert kwargs["room"] == temp_client.room
    assert kwargs["client"] == temp_client


def test_on_room_left(temp_client: Client):
    """Test that a user remaining in the room gets notified when it's deleted."""
    temp_client.on_room_left = MagicMock()
    
    temp_client.create_room("TempRoom")
    room = temp_client.room
    temp_client.leave_room()
    
    assert wait_for_mock(temp_client.on_room_left)
    _, kwargs = temp_client.on_room_left.call_args
    assert kwargs["room"] == room
    assert kwargs["client"] == temp_client


def test_on_room_started(temp_client: Client):
    temp_client.on_room_started = MagicMock()
    
    temp_client.create_room("TempRoom", min_players=1)
    assert isinstance(temp_client.room.start(), mpglite.message.RoomStartedMessage)
    
    assert wait_for_mock(temp_client.on_room_started)
    _, kwargs = temp_client.on_room_started.call_args
    assert kwargs["room"] == temp_client.room
    assert kwargs["client"] == temp_client


def test_on_room_ended(temp_client: Client):
    temp_client.on_room_ended = MagicMock()
    
    temp_client.create_room("TempRoom", min_players=1)
    room = temp_client.room
    temp_client.room.start()
    temp_client.room.end()
    
    assert wait_for_mock(temp_client.on_room_ended)
    _, kwargs = temp_client.on_room_ended.call_args
    assert kwargs["room"] == room
    assert kwargs["client"] == temp_client


def test_on_room_deleted(temp_client: Client):
    """Test that a user remaining in the room gets notified when it's deleted."""
    temp_client.on_room_deleted = MagicMock()
    
    temp_client.create_room("TempRoom")
    temp_client.leave_room()
    
    assert wait_for_mock(temp_client.on_room_deleted)
    _, kwargs = temp_client.on_room_deleted.call_args
    assert kwargs["room_name"] == "TempRoom"
    assert kwargs["client"] == temp_client




def test_join_room(
    client_a: Client, client_b: Client, client_c: Client, client_d: Client
):
    """This function creates a room and joins all clients to it. It is necessary for the following tests to work"""
    client_a.create_room("TestRoom")

    for client in [client_a, client_b, client_c, client_d]:
        client.join_room("TestRoom")
        assert client.room.name == "TestRoom"