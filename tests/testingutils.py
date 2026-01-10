import time
from unittest.mock import MagicMock


def wait_for_mock(mock: MagicMock, timeout: float = 2.0):
    start_time = time.time()
    while time.time() - start_time < timeout:
        if mock.called:
            return True
        time.sleep(0.05)
    return False


def assert_mock_not_called(mock: MagicMock, timeout: float = 0.3):
    time.sleep(timeout)
    assert not mock.called, f"Mock was called {mock.call_count} times, but expected 0."
