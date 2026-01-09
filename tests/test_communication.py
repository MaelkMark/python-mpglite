from unittest.mock import MagicMock
from mpglite.client import Client
from mpglite.message import ErrorMessage, Message
import mpglite
import time


def wait_for_mock(mock: MagicMock, timeout: float = 2.0):
    start_time = time.time()
    while time.time() - start_time < timeout:
        if mock.called:
            return True
        time.sleep(0.05)
    return False


def test_private_message(client_a: Client, client_b: Client):
    # Test string message
    client_b.on_message = MagicMock()
    client_a.get_user_by_id(client_b.user_id).send("TestMessage")
    assert wait_for_mock(client_b.on_message), "Callback was never called within timeout"
    _, kwargs = client_b.on_message.call_args
    assert kwargs["message"] == "TestMessage", "Message is not correct"
    assert kwargs["sender"].user_id == client_a.user_id, "Sender is not correct"
    assert kwargs["client"].user_id == client_b.user_id, "Client is not correct"
    
    # Test dict message
    client_b.on_message = MagicMock()
    client_a.get_user_by_id(client_b.user_id).send({"a": 1, "b": 2})
    assert wait_for_mock(client_b.on_message), "Callback was never called within timeout"
    _, kwargs = client_b.on_message.call_args
    assert kwargs["message"] == {"a": 1, "b": 2}, "Dict message is not correct"


def test_private_question(client_a: Client, client_b: Client):
    # Test string question
    client_b.on_question = MagicMock(return_value="TestAnswer")
    answer = client_a.get_user_by_id(client_b.user_id).ask("TestQuestion")
    assert wait_for_mock(client_b.on_question), "Callback was never called within timeout"
    _, kwargs = client_b.on_question.call_args
    assert kwargs["question"] == "TestQuestion", "Question is not correct"
    assert kwargs["sender"].user_id == client_a.user_id, "Sender is not correct"
    assert kwargs["client"].user_id == client_b.user_id, "Client is not correct"
    assert answer == "TestAnswer", "Answer is not correct"
    
    # Test dict question
    client_b.on_question = MagicMock(return_value={"result": "ok"})
    answer = client_a.get_user_by_id(client_b.user_id).ask({"cmd": "test"})
    assert wait_for_mock(client_b.on_question), "Callback was never called within timeout"
    _, kwargs = client_b.on_question.call_args
    assert kwargs["question"] == {"cmd": "test"}, "Dict question is not correct"
    assert answer == {"result": "ok"}, "Dict answer is not correct"