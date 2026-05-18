import json
import pytest
from unittest.mock import MagicMock
from mpglite.message import (
    Message,
    OKMessage,
    ErrorMessage,
    MessageBundle,
    Question,
    Answer,
)


@pytest.fixture(autouse=True)
def clear_pending_questions():
    """Ensures the pending questions list is empty before and after each test."""
    Question.pending.clear()
    yield
    Question.pending.clear()


def test_message_basic_properties():
    """Test base Message creation, properties, and JSON serialization."""
    props = {"key1": "value1", "key2": 42}
    msg = Message("test_type", "Test Description", **props)

    assert msg.type == "test_type", "Message type should be 'test_type'"
    assert msg.description == "Test Description", "Message description mismatch"
    assert msg.key1 == "value1", "Custom property 'key1' was not set correctly"
    assert msg.key2 == 42, "Custom property 'key2' was not set correctly"
    assert msg.ok is True, "Standard Message should have ok=True"
    assert msg.error is False, "Standard Message should have error=False"

    # Check JSON
    expected_dict = {"type": "test_type", "key1": "value1", "key2": 42}
    assert (
        json.loads(msg.json) == expected_dict
    ), "JSON output does not match expected dictionary"


def test_message_parsing_dict():
    """Test the static parse method for strings."""
    data_dict = {"type": "ok", "foo": "bar"}
    msg_from_dict = Message.parse(data_dict)
    assert isinstance(
        msg_from_dict, OKMessage
    ), "Parsing 'ok' type dict should return OKMessage instance"
    assert msg_from_dict.foo == "bar", "Parsed message missing extra properties"

def test_message_parsing_str():
    """Test the static parse method for dictionaries."""
    data_str = '{"type": "error", "error_code": "404", "error_message": "Not Found"}'
    msg_from_str = Message.parse(data_str)
    assert isinstance(
        msg_from_str, ErrorMessage
    ), "Parsing 'error' type string should return ErrorMessage instance"
    assert (
        msg_from_str.error_code == "404"
    ), "Parsed ErrorMessage has incorrect error_code"

def test_message_parsing_msg():
    """Test the static parse method for messages."""
    msg_from_msg = Message.parse(OKMessage(foo="bar"))
    assert isinstance(
        msg_from_msg, OKMessage
    ), "Parsing 'ok' type dict should return OKMessage instance"
    assert msg_from_msg.foo == "bar", "Parsed message missing extra properties"


def test_ok_messages():
    """Test properties unique to OKMessage."""
    ok_msg = OKMessage(extra="info")
    assert ok_msg.type == "ok", "OKMessage should have type 'ok'"
    assert ok_msg.ok is True, "OKMessage.ok should be True"


def test_error_messages():
    """Test properties unique to ErrorMessage."""
    err_msg = ErrorMessage("ERR_CODE", "Something went wrong", severity="critical")
    assert err_msg.type == "error", "ErrorMessage should have type 'error'"
    assert err_msg.ok is False, "ErrorMessage.ok should be False"
    assert err_msg.error is True, "ErrorMessage.error should be True"
    assert err_msg.error_code == "ERR_CODE", "ErrorMessage code mismatch"
    assert err_msg.severity == "critical", "ErrorMessage severity mismatch"


def test_message_bundle():
    """Test packing and unpacking multiple messages in a MessageBundle."""
    m1 = OKMessage(id=1)
    m2 = Message("custom", "desc", id=2)
    bundle = MessageBundle([m1, m2])

    assert bundle.type == "message_bundle", "Bundle type should be 'message_bundle'"
    assert len(bundle.messages) == 2, "Bundle should contain 2 serialized messages"

    parsed = bundle.parsed_messages
    assert len(parsed) == 2, "Parsed messages list should have length 2"
    assert isinstance(parsed[0], OKMessage), "First bundled message should be OKMessage"
    assert parsed[1].type == "custom", "Second bundled message type mismatch"
    assert parsed[1].id == 2, "Second bundled message property mismatch"


def test_question_id_generation():
    """Test the logic for generating question IDs."""
    # UUID generation
    q1 = Question(Message("ping"))
    assert len(q1.question_id) > 0, "Question should have a generated ID"

    # Sender ID based generation
    q2 = Question(Message("ping"), sender_id=101)
    assert (
        "101#" in q2.question_id
    ), "Question ID should include sender_id when provided"

    # Manual ID
    q3 = Question(Message("ping"), question_id="manual_id")
    assert (
        q3.question_id == "manual_id"
    ), "Question ID should match provided question_id"


def test_question_answering_flow():
    """Test that Question.answer() triggers the callback and removes from pending."""
    callback = MagicMock()
    q = Question(Message("request"), callback=callback)

    assert q in Question.pending, "Question with callback should be in Question.pending"

    ans_msg = OKMessage(result="success")
    q.answer(ans_msg)

    assert callback.called, "Callback was not executed when question was answered"
    # smart_call handles the args, we check the response passed to callback
    args, kwargs = callback.call_args
    assert kwargs["response"] == ans_msg, "Callback received the wrong response message"
    assert (
        q not in Question.pending
    ), "Question should be removed from pending after being answered"


def test_answer_side_effect():
    """Test that creating an Answer object automatically answers the corresponding Question."""
    callback = MagicMock()
    q_id = "test_q_123"
    q = Question(Message("ask"), callback=callback, question_id=q_id)

    assert q in Question.pending, "Question should be pending"

    # Instantiate Answer - this should trigger Question.answer_question via __init__
    ans_payload = OKMessage(data="payload")
    Answer(question_id=q_id, message=ans_payload)

    assert (
        callback.called
    ), "Answer instantiation should have triggered the Question callback"
    assert q not in Question.pending, "Question should no longer be pending"


def test_question_answer_question_classmethod():
    """Test the class method Question.answer_question."""
    callback = MagicMock()
    q_id = "find_me"
    Question(Message("ping"), callback=callback, question_id=q_id)

    ans_msg = Message("pong")
    found = Question.answer_question(q_id, ans_msg)

    assert found is True, "answer_question should return True when ID is found"
    assert callback.called, "Callback should be triggered by answer_question"

    # Test non-existent ID
    found_none = Question.answer_question("non_existent", ans_msg)
    assert found_none is False, "answer_question should return False for unknown IDs"


def test_answer_processing_logic():
    """Test that Answer with process=True does NOT automatically answer the question."""
    callback = MagicMock()
    q_id = "proc_test"
    q = Question(Message("ask"), callback=callback, question_id=q_id)

    # If process=True, Answer __init__ should NOT call Question.answer_question
    Answer(question_id=q_id, message=OKMessage(), process=True)

    assert (
        not callback.called
    ), "Callback should not be called yet when Answer.process is True"
    assert (
        q in Question.pending
    ), "Question should still be pending when Answer.process is True"

    # Manual trigger
    q.answer(OKMessage())
    assert (
        callback.called
    ), "Manual answer should work even if Answer was created with process=True"


def test_question_parsed_message_property():
    """Test that Question.parsed_message correctly reconstructs the inner message."""
    inner = OKMessage(val=10)
    q = Question(inner)

    parsed = q.parsed_message
    assert isinstance(parsed, OKMessage), "parsed_message should be an OKMessage"
    assert parsed.val == 10, "Inner property mismatch in parsed_message"
