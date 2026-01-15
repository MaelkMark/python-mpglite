from unittest.mock import MagicMock
from mpglite.client import Client, Room, User
from mpglite.server import Server
from mpglite.message import ErrorMessage
from testingutils import *
from conftest import PORT


def test_on_room_list(temp_client: Client, temp_client2: Client):
    temp_client2.on_room_list = MagicMock()

    temp_client.create_room("TempRoom")

    assert wait_for_mock(temp_client2.on_room_list)
    _, kwargs = temp_client2.on_room_list.call_args
    assert kwargs["client"] == temp_client2
    assert len(kwargs["rooms"]) == 1
    assert all(isinstance(room, Room) for room in kwargs["rooms"])


def test_on_user_list(temp_client: Client):
    temp_client.on_user_list = MagicMock()

    new_client = Client("localhost", PORT)
    new_client.connect()

    assert wait_for_mock(temp_client.on_user_list)
    _, kwargs = temp_client.on_user_list.call_args
    assert kwargs["client"] == temp_client
    assert len(kwargs["users"]) == 2
    assert all(isinstance(user, User) for user in kwargs["users"])


def test_private_message(client_a: Client, client_b: Client):
    # Test string message
    client_b.on_message = MagicMock()

    client_a.get_user_by_id(client_b.user_id).send("TestMessage")

    assert wait_for_mock(
        client_b.on_message
    ), "Callback was never called within timeout"
    _, kwargs = client_b.on_message.call_args
    assert kwargs["message"] == "TestMessage", "Message is not correct"
    assert kwargs["sender"].user_id == client_a.user_id, "Sender is not correct"
    assert kwargs["client"].user_id == client_b.user_id, "Client is not correct"

    # Test dict message
    client_b.on_message = MagicMock()

    client_a.get_user_by_id(client_b.user_id).send({"a": 1, "b": 2})

    assert wait_for_mock(
        client_b.on_message
    ), "Callback was never called within timeout"
    _, kwargs = client_b.on_message.call_args
    assert kwargs["message"] == {"a": 1, "b": 2}, "Dict message is not correct"


def test_private_question(client_a: Client, client_b: Client):
    # Test string question
    client_b.on_question = MagicMock(return_value="TestAnswer")

    answer = client_a.get_user_by_id(client_b.user_id).ask("TestQuestion")

    assert wait_for_mock(
        client_b.on_question
    ), "Callback was never called within timeout"
    _, kwargs = client_b.on_question.call_args
    assert kwargs["question"] == "TestQuestion", "Question is not correct"
    assert kwargs["sender"].user_id == client_a.user_id, "Sender is not correct"
    assert kwargs["client"].user_id == client_b.user_id, "Client is not correct"
    assert answer == "TestAnswer", "Answer is not correct"

    # Test dict question
    client_b.on_question = MagicMock(return_value={"result": "ok"})

    answer = client_a.get_user_by_id(client_b.user_id).ask({"cmd": "test"})

    assert wait_for_mock(
        client_b.on_question
    ), "Callback was never called within timeout"
    _, kwargs = client_b.on_question.call_args
    assert kwargs["question"] == {"cmd": "test"}, "Dict question is not correct"
    assert answer == {"result": "ok"}, "Dict answer is not correct"


def test_client_send_message(temp_client: Client, server: Server):
    """Test the Client.send() method and verify that the server receives the message"""
    server.on_message = MagicMock()

    temp_client.send("TestMessage")

    assert wait_for_mock(server.on_message), "Callback was never called within timeout"
    _, kwargs = server.on_message.call_args
    assert kwargs["message"] == "TestMessage", "Message is not correct"
    assert kwargs["user"].user_id == temp_client.user_id, "Sender is not correct"
    assert kwargs["server"] == server, "Client is not correct"


def test_client_ask_question(temp_client: Client, server: Server):
    """Test the Client.ask() method and verify that the server receives the question and answers"""
    server.on_question = MagicMock(return_value="TestAnswer")

    answer = temp_client.ask("TestQuestion")

    assert wait_for_mock(server.on_question), "Callback was never called within timeout"
    _, kwargs = server.on_question.call_args
    assert kwargs["question"] == "TestQuestion", "Question is not correct"
    assert kwargs["user"].user_id == temp_client.user_id, "Sender is not correct"
    assert kwargs["server"] == server, "Client is not correct"

    assert answer == "TestAnswer"


def test_server_user_send(temp_client: Client, server: Server):
    """Test the server User.send() method and verify that the client receives the message"""
    temp_client.on_message = MagicMock()

    server.users[temp_client.user_id].send("TestMessage")

    assert wait_for_mock(
        temp_client.on_message
    ), "Callback was never called within timeout"
    _, kwargs = temp_client.on_message.call_args
    assert kwargs["message"] == "TestMessage", "Message is not correct"
    assert kwargs["sender"] is None, "Sender is not correct"
    assert kwargs["client"] == temp_client, "Client is not correct"


def test_server_send_to_player_id(temp_client: Client, server: Server):
    """Test the server Server.send_to_player(user_id) method and verify that the client receives the message"""
    temp_client.on_message = MagicMock()

    server.send_to_player(temp_client.user_id, "TestMessage")

    assert wait_for_mock(
        temp_client.on_message
    ), "Callback was never called within timeout"
    _, kwargs = temp_client.on_message.call_args
    assert kwargs["message"] == "TestMessage", "Message is not correct"


def test_server_send_to_player_user(temp_client: Client, server: Server):
    """Test the server Server.send_to_player(user) method and verify that the client receives the message"""
    temp_client.on_message = MagicMock()

    server.send_to_player(server.users[temp_client.user_id], "TestMessage")

    assert wait_for_mock(
        temp_client.on_message
    ), "Callback was never called within timeout"
    _, kwargs = temp_client.on_message.call_args
    assert kwargs["message"] == "TestMessage", "Message is not correct"


def test_server_user_ask(temp_client: Client, server: Server):
    """Test the server User.ask() method and verify that the client receives the message and responds"""
    temp_client.on_question = MagicMock(return_value="TestAnswer")

    answer = server.users[temp_client.user_id].ask("TestQuestion")

    assert wait_for_mock(
        temp_client.on_question
    ), "Callback was never called within timeout"
    _, kwargs = temp_client.on_question.call_args
    assert kwargs["question"] == "TestQuestion", "Question is not correct"
    assert kwargs["sender"] is None, "Sender is not correct"
    assert kwargs["client"] == temp_client, "Client is not correct"

    assert answer == "TestAnswer", "Answer is not correct"


def test_server_ask_player_id(temp_client: Client, server: Server):
    """Test the server Server.ask_player(user_id) method and verify that the client receives the message and responds"""
    temp_client.on_question = MagicMock(return_value="TestAnswer")

    answer = server.ask_player(temp_client.user_id, "TestQuestion")

    assert wait_for_mock(
        temp_client.on_question
    ), "Callback was never called within timeout"
    _, kwargs = temp_client.on_question.call_args
    assert kwargs["question"] == "TestQuestion", "Question is not correct"

    assert answer == "TestAnswer", "Answer is not correct"


def test_server_ask_player_user(temp_client: Client, server: Server):
    """Test the server Server.ask_player(user_id) method and verify that the client receives the message and responds"""
    temp_client.on_question = MagicMock(return_value="TestAnswer")

    answer = server.ask_player(server.users[temp_client.user_id], "TestQuestion")

    assert wait_for_mock(
        temp_client.on_question
    ), "Callback was never called within timeout"
    _, kwargs = temp_client.on_question.call_args
    assert kwargs["question"] == "TestQuestion", "Question is not correct"

    assert answer == "TestAnswer", "Answer is not correct"


def test_join_room(
    client_a: Client, client_b: Client, client_c: Client, client_d: Client
):
    """This function creates a room and joins all clients to it. It is necessary for the following tests to work"""
    client_a.create_room("TestRoom")

    for client in [client_a, client_b, client_c, client_d]:
        client.join_room("TestRoom")
        assert client.room.name == "TestRoom"


def test_room_broadcast(client_a: Client, client_b: Client, client_c: Client):
    client_a.on_message = MagicMock()
    client_b.on_message = MagicMock()
    client_c.on_message = MagicMock()

    assert client_a.room.broadcast("TestMessage").ok

    assert wait_for_mock(
        client_b.on_message
    ), "Callback was never called within timeout"
    _, kwargs = client_b.on_message.call_args
    assert kwargs["message"] == "TestMessage", "Message is not correct"

    assert wait_for_mock(
        client_c.on_message
    ), "Callback was never called within timeout"
    _, kwargs = client_c.on_message.call_args
    assert kwargs["message"] == "TestMessage", "Message is not correct"

    assert_mock_not_called(client_a.on_message)


def test_room_broadcast_excluded(
    client_a: Client, client_b: Client, client_c: Client, client_d: Client
):
    client_b.on_message = MagicMock()
    client_c.on_message = MagicMock()
    client_d.on_message = MagicMock()

    assert client_a.room.broadcast(
        "TestMessage",
        excluded_users=[
            client_b.user_id,  # User ID (int)
            client_a.get_user_by_id(client_c.user_id),  # User object
        ],
    ).ok

    assert_mock_not_called(client_b.on_message)
    assert_mock_not_called(client_c.on_message)

    assert wait_for_mock(
        client_d.on_message
    ), "Callback was never called within timeout"
    _, kwargs = client_d.on_message.call_args
    assert kwargs["message"] == "TestMessage", "Message is not correct"


def test_room_broadcast_included(
    client_a: Client, client_b: Client, temp_client: Client, temp_client2: Client
):
    client_b.on_message = MagicMock()
    temp_client.on_message = MagicMock()
    temp_client2.on_message = MagicMock()

    assert client_a.room.broadcast(
        "TestMessage",
        included_users=[
            temp_client.user_id,  # User ID (int),
            client_a.get_user_by_id(temp_client2.user_id),  # User object
        ],
    ).ok

    assert wait_for_mock(
        client_b.on_message
    ), "Callback was never called within timeout"
    _, kwargs = client_b.on_message.call_args
    assert kwargs["message"] == "TestMessage", "Message is not correct"

    assert wait_for_mock(
        temp_client.on_message
    ), "Callback was never called within timeout"
    _, kwargs = temp_client.on_message.call_args
    assert kwargs["message"] == "TestMessage", "Message is not correct"

    assert wait_for_mock(
        temp_client2.on_message
    ), "Callback was never called within timeout"
    _, kwargs = temp_client2.on_message.call_args
    assert kwargs["message"] == "TestMessage", "Message is not correct"


def test_room_broadcast_include_self(client_a: Client, client_b: Client):
    client_a.on_message = MagicMock()
    client_b.on_message = MagicMock()

    assert client_a.room.broadcast("TestMessage", exclude_self=False).ok

    assert wait_for_mock(
        client_a.on_message
    ), "Callback was never called within timeout"
    _, kwargs = client_a.on_message.call_args
    assert kwargs["message"] == "TestMessage", "Message is not correct"

    assert wait_for_mock(
        client_b.on_message
    ), "Callback was never called within timeout"
    _, kwargs = client_b.on_message.call_args
    assert kwargs["message"] == "TestMessage", "Message is not correct"


def test_send_room_message(client_a: Client, client_b: Client):
    client_b.on_message = MagicMock()

    client_a.send_room_message("TestMessage")

    assert wait_for_mock(
        client_b.on_message
    ), "Callback was never called within timeout"
    _, kwargs = client_b.on_message.call_args
    assert kwargs["message"] == "TestMessage", "Message is not correct"


def test_send_room_message_not_in_room(temp_client: Client):
    response = temp_client.send_room_message("TestMessage")
    assert isinstance(response, ErrorMessage)
    assert response.error_code == "ERR_NOT_IN_ROOM"


def test_room_ask_everybody(
    client_a: Client, client_b: Client, client_c: Client, client_d: Client
):
    client_a.on_question = MagicMock(return_value="TestAnswer")
    client_b.on_question = MagicMock(return_value="TestAnswer")
    client_c.on_question = MagicMock(return_value="TestAnswer")
    client_d.on_question = MagicMock(return_value="TestAnswer")

    answer = client_a.room.ask_everybody("TestQuestion")

    assert wait_for_mock(
        client_b.on_question
    ), "Callback was never called within timeout"
    _, kwargs = client_b.on_question.call_args
    assert kwargs["question"] == "TestQuestion", "Question is not correct"

    assert wait_for_mock(
        client_c.on_question
    ), "Callback was never called within timeout"
    _, kwargs = client_c.on_question.call_args
    assert kwargs["question"] == "TestQuestion", "Question is not correct"

    assert wait_for_mock(
        client_d.on_question
    ), "Callback was never called within timeout"
    _, kwargs = client_d.on_question.call_args
    assert kwargs["question"] == "TestQuestion", "Question is not correct"

    answer_with_ids = {user.user_id: response for user, response in answer.items()}
    expected_answer = {
        client.user_id: "TestAnswer" for client in [client_b, client_c, client_d]
    }
    assert answer_with_ids == expected_answer, "Answer is not correct"

    assert_mock_not_called(client_a.on_question)


def test_room_ask_everybody_excluded(
    client_a: Client, client_b: Client, client_c: Client, client_d: Client
):
    client_b.on_question = MagicMock(return_value="TestAnswer")
    client_c.on_question = MagicMock(return_value="TestAnswer")
    client_d.on_question = MagicMock(return_value="TestAnswer")

    answer = client_a.room.ask_everybody(
        "TestQuestion",
        excluded_users=[
            client_b.user_id,  # User ID (int)
            client_a.get_user_by_id(client_c.user_id),  # User object
        ],
    )

    assert wait_for_mock(
        client_d.on_question
    ), "Callback was never called within timeout"
    _, kwargs = client_d.on_question.call_args
    assert kwargs["question"] == "TestQuestion", "Question is not correct"

    assert_mock_not_called(client_b.on_question)
    assert_mock_not_called(client_c.on_question)

    answer_with_ids = {user.user_id: response for user, response in answer.items()}
    expected_answer = {client_d.user_id: "TestAnswer"}
    assert answer_with_ids == expected_answer, "Answer is not correct"


def test_room_ask_everybody_included(
    client_a: Client,
    client_b: Client,
    client_c: Client,
    client_d: Client,
    temp_client: Client,
    temp_client2: Client,
):
    client_b.on_question = MagicMock(return_value="TestAnswer")
    client_c.on_question = MagicMock(return_value="TestAnswer")
    client_d.on_question = MagicMock(return_value="TestAnswer")
    temp_client.on_question = MagicMock(return_value="TestAnswer")
    temp_client2.on_question = MagicMock(return_value="TestAnswer")

    answer = client_a.room.ask_everybody(
        "TestQuestion",
        included_users=[
            temp_client.user_id,  # User ID (int)
            client_a.get_user_by_id(temp_client2.user_id),  # User object
        ],
    )

    assert wait_for_mock(
        client_b.on_question
    ), "Callback was never called within timeout"
    _, kwargs = client_b.on_question.call_args
    assert kwargs["question"] == "TestQuestion", "Question is not correct"

    assert wait_for_mock(
        temp_client.on_question
    ), "Callback was never called within timeout"
    _, kwargs = temp_client.on_question.call_args
    assert kwargs["question"] == "TestQuestion", "Question is not correct"

    assert wait_for_mock(
        temp_client2.on_question
    ), "Callback was never called within timeout"
    _, kwargs = temp_client2.on_question.call_args
    assert kwargs["question"] == "TestQuestion", "Question is not correct"

    answer_with_ids = {user.user_id: response for user, response in answer.items()}
    expected_answer = {
        client.user_id: "TestAnswer"
        for client in [client_b, client_c, client_d, temp_client, temp_client2]
    }
    assert answer_with_ids == expected_answer, "Answer is not correct"


def test_room_ask_everybody_include_self(
    client_a: Client, client_b: Client, client_c: Client, client_d: Client
):
    answer = client_a.room.ask_everybody(
        "TestQuestion",
        exclude_self=False,
    )

    assert wait_for_mock(
        client_a.on_question
    ), "Callback was never called within timeout"
    _, kwargs = client_a.on_question.call_args
    assert kwargs["question"] == "TestQuestion", "Question is not correct"

    answer_with_ids = {user.user_id: response for user, response in answer.items()}
    expected_answer = {
        client.user_id: "TestAnswer"
        for client in [client_a, client_b, client_c, client_d]
    }
    assert answer_with_ids == expected_answer, "Answer is not correct"


def test_ask_room_question(
    client_a: Client, client_b: Client, client_c: Client, client_d: Client
):
    client_a.on_question = MagicMock(return_value="TestAnswer")
    client_b.on_question = MagicMock(return_value="TestAnswer")
    client_c.on_question = MagicMock(return_value="TestAnswer")
    client_d.on_question = MagicMock(return_value="TestAnswer")

    answer = client_a.ask_room_question("TestQuestion")

    assert wait_for_mock(
        client_b.on_question
    ), "Callback was never called within timeout"
    _, kwargs = client_b.on_question.call_args
    assert kwargs["question"] == "TestQuestion", "Question is not correct"

    assert wait_for_mock(
        client_c.on_question
    ), "Callback was never called within timeout"
    _, kwargs = client_c.on_question.call_args
    assert kwargs["question"] == "TestQuestion", "Question is not correct"

    assert wait_for_mock(
        client_d.on_question
    ), "Callback was never called within timeout"
    _, kwargs = client_d.on_question.call_args
    assert kwargs["question"] == "TestQuestion", "Question is not correct"

    answer_with_ids = {user.user_id: response for user, response in answer.items()}
    expected_answer = {
        client.user_id: "TestAnswer" for client in [client_b, client_c, client_d]
    }
    assert answer_with_ids == expected_answer, "Answer is not correct"

    assert_mock_not_called(client_a.on_question)


def test_ask_room_question_not_in_room(temp_client):
    response = temp_client.ask_room_question("TestQuestion")
    assert isinstance(response, ErrorMessage)
    assert response.error_code == "ERR_NOT_IN_ROOM"
