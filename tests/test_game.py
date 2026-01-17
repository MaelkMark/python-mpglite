from unittest.mock import MagicMock
from mpglite.client import Client
from mpglite.message import ErrorMessage
from mpglite.server import Server
from testingutils import *
import mpglite


def test_room_auto_start(temp_client_a: Client, temp_client_b: Client):
    temp_client_a.create_room("TempRoom", max_players=2, auto_start=True)
    assert temp_client_a.room.name == "TempRoom"
    assert (
        temp_client_a.room.status != "started"
    ), "Room started without reaching max players"

    temp_client_b.join_room("TempRoom")
    assert temp_client_b.room.name == "TempRoom"
    assert temp_client_a.room.status == "started", "Room did not start"


def test_room_auto_start_disabled(temp_client_a: Client, temp_client_b: Client):
    temp_client_a.create_room("TempRoom", max_players=2, auto_start=False)
    temp_client_b.join_room("TempRoom")
    assert temp_client_a.room.name == "TempRoom"
    assert temp_client_b.room.name == "TempRoom"
    assert temp_client_a.room.status != "started", "Room started with auto_start disabled"


def test_room_deletion(temp_client_a: Client):
    temp_client_a.create_room("TempRoom")
    assert isinstance(temp_client_a.leave_room(), mpglite.message.RoomLeftMessage)
    assert temp_client_a.get_room_by_name("TempRoom") is None
    assert temp_client_a.room is None


def test_room_start(temp_client_a: Client):
    temp_client_a.create_room("TempRoom", min_players=1)
    result = temp_client_a.room.start()
    assert isinstance(result, mpglite.message.RoomStartedMessage)
    assert temp_client_a.room.status == "started"


def test_room_start_not_enough_players(temp_client_a: Client):
    temp_client_a.create_room("TempRoom", min_players=2)
    result = temp_client_a.room.start()
    assert isinstance(result, mpglite.message.ErrorMessage)
    assert result.error_code == "ERR_NOT_ENOUGH_PLAYERS"
    assert temp_client_a.room.status == "open"


def test_room_end(temp_client_a: Client):
    temp_client_a.create_room("TempRoom", min_players=1)
    temp_client_a.room.start()
    result = temp_client_a.room.end()
    assert isinstance(result, mpglite.message.RoomEndedMessage)
    assert temp_client_a.room.status == "ended"


def test_on_room_joined(temp_client_a: Client):
    temp_client_a.on_room_joined = MagicMock()

    temp_client_a.create_room("TempRoom")

    temp_client_a.on_room_joined.assert_called_once()
    temp_client_a.on_room_joined.assert_called_once()
    _, kwargs = temp_client_a.on_room_joined.call_args
    assert kwargs["room"] == temp_client_a.room
    assert kwargs["client"] == temp_client_a


def test_on_room_left(temp_client_a: Client):
    """Test that a user remaining in the room gets notified when it's deleted."""
    temp_client_a.on_room_left = MagicMock()

    temp_client_a.create_room("TempRoom")
    room = temp_client_a.room
    temp_client_a.leave_room()

    assert wait_for_mock(temp_client_a.on_room_left)
    _, kwargs = temp_client_a.on_room_left.call_args
    assert kwargs["room"] == room
    assert kwargs["client"] == temp_client_a


def test_on_room_started(temp_client_a: Client):
    temp_client_a.on_room_started = MagicMock()

    temp_client_a.create_room("TempRoom", min_players=1)
    assert isinstance(temp_client_a.room.start(), mpglite.message.RoomStartedMessage)

    assert wait_for_mock(temp_client_a.on_room_started)
    _, kwargs = temp_client_a.on_room_started.call_args
    assert kwargs["room"] == temp_client_a.room
    assert kwargs["client"] == temp_client_a


def test_on_room_ended(temp_client_a: Client):
    temp_client_a.on_room_ended = MagicMock()

    temp_client_a.create_room("TempRoom", min_players=1)
    room = temp_client_a.room
    temp_client_a.room.start()
    temp_client_a.room.end()

    assert wait_for_mock(temp_client_a.on_room_ended)
    _, kwargs = temp_client_a.on_room_ended.call_args
    assert kwargs["room"] == room
    assert kwargs["client"] == temp_client_a


def test_on_room_deleted(temp_client_a: Client):
    """Test that a user remaining in the room gets notified when it's deleted."""
    temp_client_a.on_room_deleted = MagicMock()

    temp_client_a.create_room("TempRoom")
    temp_client_a.leave_room()

    assert wait_for_mock(temp_client_a.on_room_deleted)
    _, kwargs = temp_client_a.on_room_deleted.call_args
    assert kwargs["room_name"] == "TempRoom"
    assert kwargs["client"] == temp_client_a


def test_client_rematch(temp_client_a: Client, temp_client_b: Client):
    temp_client_a.on_room_started = MagicMock()
    temp_client_b.on_room_started = MagicMock()
    
    temp_client_a.create_room("TempRoom")
    temp_client_b.join_room("TempRoom")
    temp_client_a.room.end()
    assert temp_client_a.room.status == "ended"
    
    temp_client_a.rematch()
    assert temp_client_a.room.status == "ended"
    
    temp_client_b.rematch()
    assert temp_client_b.room.status == "started"
    
    assert wait_for_mock(temp_client_a.on_room_started)
    assert wait_for_mock(temp_client_b.on_room_started)


def test_client_rematch_not_in_room(temp_client_a: Client):
    response = temp_client_a.rematch()
    assert isinstance(response, ErrorMessage)
    assert response.error_code == "ERR_NOT_IN_ROOM"


def test_room_rematch(temp_client_a: Client, temp_client_b: Client):
    temp_client_a.create_room("TempRoom")
    temp_client_b.join_room("TempRoom")
    temp_client_a.room.end()
    assert temp_client_a.room.status == "ended"
    
    temp_client_a.room.rematch()
    assert temp_client_a.room.status == "ended"
    
    temp_client_b.room.rematch()
    assert temp_client_b.room.status == "started"


def test_join_room(
    client_a: Client, client_b: Client, client_c: Client, client_d: Client
):
    """This function creates a room and joins all clients to it. It is necessary for the following tests to work"""
    client_a.create_room("TestRoom")

    for client in [client_a, client_b, client_c, client_d]:
        client.join_room("TestRoom")
        assert client.room.name == "TestRoom"

