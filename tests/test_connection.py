from mpglite.client import Client

def test_connection_successful(temp_client: Client):
    """Verify the socket is actually open."""
    assert temp_client._Client__ws is not None
    assert temp_client._running is True


def test_user_id(temp_client):
    """Verify the server gave us a valid user ID."""
    assert isinstance(temp_client.user_id, int)
    assert temp_client.user_id > 0


def test_default_username(client_a: Client):
    """Verify the 'Player [user_id]' naming logic."""
    assert client_a.username == f"Player {client_a.user_id}"