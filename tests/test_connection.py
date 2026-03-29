from mpglite.client import Client
from mpglite.server import Server
from mpglite.exceptions import *
from conftest import PORT, LOGLEVEL
from testingutils import wait_for_mock

import pytest
from unittest.mock import MagicMock


def test_connection_successful(temp_client_a: Client):
    """Verify the socket is actually open."""
    assert temp_client_a._Client__ws is not None
    assert temp_client_a._running is True


def test_user_id(temp_client_a):
    """Verify the server gave us a valid user ID."""
    assert isinstance(temp_client_a.user_id, int)
    assert temp_client_a.user_id > 0


def test_default_username(client_a: Client):
    """Verify the 'Player [user_id]' naming logic."""
    assert client_a.username == f"Player {client_a.user_id}"


def test_on_user_joined(server: Server):
    server.on_user_joined = MagicMock()
    
    temp_client: Client = Client("localhost", PORT)
    temp_client.connect()
    
    assert wait_for_mock(server.on_user_joined)


def test_server_not_found():
    with pytest.raises(ServerNotFoundError):
        c = Client(host="no-such-host", port=PORT, loglevel=LOGLEVEL)
        c.connect()