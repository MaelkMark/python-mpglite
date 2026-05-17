from mpglite.client import Client
from mpglite.exceptions import UserLeftError
from mpglite.message import ErrorMessage
from mpglite.server import Server
from testingutils import *
from conftest import PORT
import mpglite

from unittest.mock import MagicMock
import pytest
import time
import threading


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
    assert (
        temp_client_a.room.status != "started"
    ), "Room started with auto_start disabled"


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


def test_room_start_server_not_enough_players(temp_client_a: Client):
    temp_client_a.create_room("TempRoom", min_players=2)
    result = temp_client_a._ask(mpglite.message.StartRoomMessage(temp_client_a.room.name), process=True)
    assert isinstance(result, mpglite.message.ErrorMessage)
    assert result.error_code == "ERR_NOT_ENOUGH_PLAYERS"
    assert temp_client_a.room.status == "open"


def test_client_room_end(server: Server, temp_client_a: Client):
    temp_client_a.create_room("TempRoom")
    temp_client_a.room.start()
    result = server.rooms["TempRoom"].end()
    assert isinstance(result, mpglite.message.RoomEndedMessage)
    assert server.rooms["TempRoom"].status == "ended"
    assert temp_client_a.room.status == "ended"


def test_server_room_end(temp_client_a: Client):
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


def test_on_room_left_abruptly(server: Server):
    server.on_room_left = MagicMock(return_value=False)
    
    temp_client = Client("localhost", PORT)
    temp_client.connect()
    temp_client.create_room("TempRoom")
    
    temp_client._Client__ws.socket.close()
    
    assert wait_for_mock(server.on_room_left, timeout=15.0)


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


def test_server_rematch_not_in_room(temp_client_a: Client):
    response = temp_client_a._ask(mpglite.message.RematchMessage(), process=True)
    assert isinstance(response, ErrorMessage)
    assert response.error_code == "ERR_REMATCH_NO_ROOM"


def test_room_rematch(temp_client_a: Client, temp_client_b: Client):
    temp_client_a.create_room("TempRoom")
    temp_client_b.join_room("TempRoom")
    temp_client_a.room.end()
    assert temp_client_a.room.status == "ended"

    temp_client_a.room.rematch()
    assert temp_client_a.room.status == "ended"

    temp_client_b.room.rematch()
    assert temp_client_b.room.status == "started"


def test_rematch_leave(server: Server, temp_client_a: Client, temp_client_b: Client):
    temp_client_a.create_room("TempRoom")
    temp_client_b.join_room("TempRoom")
    temp_client_a.room.end()
    temp_client_a.room.rematch()
    assert temp_client_a.user_id in server.rooms["TempRoom"].wants_rematch, "User not in rematch list"
    
    temp_client_a.leave_room()
    assert temp_client_a.user_id not in server.rooms["TempRoom"].wants_rematch, "User still in rematch list"


def test_user_disconnected(server: Server, temp_client_a: Client, temp_client_b: Client):
    server.on_room_left = MagicMock(return_value=False)
    temp_client_a.on_room_left = MagicMock()
    
    temp_client_a.create_room("TempRoom")
    temp_client_b.join_room("TempRoom")

    temp_client = Client("localhost", PORT)
    temp_client.connect()
    temp_client.room.start()
    temp_client.join_room("TempRoom")

    temp_client.disconnect()
    time.sleep(0.1)
    assert "TempRoom" in server.rooms
    room = server.rooms["TempRoom"]
    
    assert wait_for_mock(server.on_room_left)
    _, kwargs = server.on_room_left.call_args
    assert kwargs["room"] == room
    assert kwargs["user"] == room.users[temp_client.user_id]
    assert kwargs["server"] == server
    
    assert wait_for_mock(temp_client_a.on_room_left)
    _, kwargs = temp_client_a.on_room_left.call_args
    assert kwargs["user"] == temp_client_a.get_user_by_id(temp_client.user_id)
    assert kwargs["room"] == temp_client_a.room
    assert kwargs["client"] == temp_client_a
    
    assert len(room.users) == 3
    assert len(room.players) == 3
    assert len(room.current_players) == 2
    pytest.raises(
        mpglite.exceptions.UserLeftError,
        lambda: room.ask_player(temp_client.user_id, "TestQuestion"),
    )


def test_user_disconnected_delete_room(server: Server, temp_client_a: Client, temp_client_b: Client):
    server.on_room_left = MagicMock(return_value=True)
    temp_client_a.on_room_left = MagicMock()
    temp_client_a.on_room_deleted = MagicMock()
    
    temp_client_a.create_room("TempRoom")
    temp_client_b.join_room("TempRoom")

    temp_client = Client("localhost", PORT)
    temp_client.connect()
    temp_client.room.start()
    temp_client.join_room("TempRoom")

    temp_client.disconnect()
    time.sleep(0.1)
    assert "TempRoom" not in server.rooms
    
    assert wait_for_mock(temp_client_a.on_room_left)
    assert wait_for_mock(temp_client_a.on_room_deleted)
    _, kwargs = temp_client_a.on_room_deleted.call_args
    assert kwargs["room_name"] == "TempRoom"
    assert kwargs["client"] == temp_client_a


def test_user_disconnected_few_players(server: Server):
    server.on_room_left = MagicMock(return_value=False)

    temp_client = Client("localhost", PORT)
    temp_client.connect()
    temp_client.create_room("TempRoom")

    temp_client.disconnect()
    time.sleep(0.1)
    assert "TempRoom" not in server.rooms


def test_ask_user_disconnect(server: Server, temp_client_a: Client):
    """Test that UserLeftError is raised when asking a user who disconnects before answering."""
    temp_client_a.create_room("TempRoom")

    temp_client = Client("localhost", PORT)
    temp_client.connect()
    temp_client.join_room("TempRoom")

    # Set up a slow answer handler so the question stays pending
    def slow_answer(**kwargs):
        time.sleep(20)  # Long delay - disconnect will happen before this returns
        return "answer"

    temp_client.on_question = slow_answer

    exception_raised = None

    def ask_and_catch():
        nonlocal exception_raised
        try:
            server.users[temp_client.user_id].ask("TestQuestion")
        except Exception as e:
            exception_raised = e

    # Start asking in a background thread
    thread = threading.Thread(target=ask_and_catch)
    thread.start()

    # Wait for the question to be sent and pending on the server
    time.sleep(1)

    # Abruptly close the socket - this prevents the client from sending an answer
    temp_client._Client__ws.socket.close()

    # Wait for the ask thread to complete
    thread.join(timeout=15.0)

    assert isinstance(exception_raised, UserLeftError), "No UserLeftError was raised"


def test_client_abrupt_disconnect(server: Server):
    callback_received = threading.Event()
    
    def room_left(**kwargs):
        callback_received.set()
    
    server.on_room_left = room_left
    
    temp_client = Client("localhost", PORT)
    temp_client.connect()
    temp_client.create_room("TempRoom")
    
    temp_client._Client__ws.socket.close()
    
    assert callback_received.wait(timeout=15.0), "on_room_left wasn't called"

    time.sleep(0.5)
    assert temp_client.user_id not in server.users, "User still in server"
    assert "TempRoom" not in server.rooms, "Room still exists"
