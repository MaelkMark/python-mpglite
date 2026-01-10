import pytest
import threading
import time
from mpglite.server import Server
from mpglite.client import Client
from mpglite.logger import Loglevel


LOGLEVEL = Loglevel.DEBUG

@pytest.fixture(scope="module")
def server():
    s = Server(host="localhost", port=8891, print_logo=False, loglevel=LOGLEVEL)
    server_thread = threading.Thread(target=s.start, daemon=True)
    server_thread.start()
    time.sleep(0.8)
    yield s
    s.stop()
    server_thread.join()


@pytest.fixture(scope="function")
def temp_client(server):  # Keep the "server" parameter or the server won't start
    c = Client(host="localhost", port=8891, loglevel=LOGLEVEL)
    c.connect()
    yield c
    c.disconnect()


@pytest.fixture(scope="function")
def temp_client2(server):  # Keep the "server" parameter or the server won't start
    c = Client(host="localhost", port=8891, loglevel=LOGLEVEL)
    c.connect()
    yield c
    c.disconnect()


@pytest.fixture(scope="module")
def client_a(server):  # Keep the "server" parameter or the server won't start
    c = Client(host="localhost", port=8891, loglevel=LOGLEVEL)
    c.connect()
    yield c
    c.disconnect()


@pytest.fixture(scope="module")
def client_b(server):  # Keep the "server" parameter or the server won't start
    c = Client(host="localhost", port=8891, loglevel=LOGLEVEL)
    c.connect()
    yield c
    c.disconnect()


@pytest.fixture(scope="module")
def client_c(server):  # Keep the "server" parameter or the server won't start
    c = Client(host="localhost", port=8891, loglevel=LOGLEVEL)
    c.connect()
    yield c
    c.disconnect()


@pytest.fixture(scope="module")
def client_d(server):  # Keep the "server" parameter or the server won't start
    c = Client(host="localhost", port=8891, loglevel=LOGLEVEL)
    c.connect()
    yield c
    c.disconnect()