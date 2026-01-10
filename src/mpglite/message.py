from typing import Any
from .utils import *

import json
from uuid import uuid4

from collections.abc import Callable


class Message:
    _message_types = {}

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        if "TYPE" in cls.__dict__:
            Message._message_types[cls.TYPE] = cls

    def __init__(
        self, message_type: str, description: str = "<no description>", **properties
    ):
        self.type = message_type
        self.description = description
        self.dict = {
            "type": message_type,
            **{
                key: str(value) if isinstance(value, Message) else value
                for key, value in properties.items()
            },
        }
        self.json = json.dumps(self.dict)

        for key, value in properties.items():
            setattr(self, key, value)

    def __str__(self):
        return self.json

    def __repr__(self):
        if self.description == "<no description>":
            return f"{self.__class__.__name__}({self.type}; json: {self.json})"
        else:
            return f"{self.__class__.__name__}({self.type}: {self.description}; json: {self.json})"

    @property
    def ok(self):
        return not isinstance(self, ErrorMessage)

    @property
    def error(self):
        return not self.ok

    @staticmethod
    def parse(message: str | dict):
        if isinstance(message, Message):
            return message

        if isinstance(message, dict):
            dictionary = message
        else:
            dictionary = json.loads(message)

        message_type = dictionary["type"]
        properties = {key: value for key, value in dictionary.items() if key != "type"}

        if message_type in Message._message_types:
            return Message._message_types[message_type](**properties)

        return Message(message_type, **properties)


class OKMessage(Message):
    TYPE = "ok"

    def __init__(self, **properties):
        super().__init__(
            self.TYPE, "Indicates that the request was successful", **properties
        )


class ServerMessage(Message):
    TYPE = "server_message"

    def __init__(self, message: Any, **properties):
        super().__init__(
            self.TYPE,
            "A question message from the server",
            message=message,
            **properties,
        )


class ClientMessage(Message):
    TYPE = "client_message"

    def __init__(self, message: Any, **properties):
        super().__init__(
            self.TYPE,
            "An answer to a ServerMessage from the server",
            message=message,
            **properties,
        )


class PrivateMessage(Message):
    TYPE = "private_message"

    def __init__(self, from_id: int, to_id: int, message: Any, **properties):
        super().__init__(
            self.TYPE,
            "send a message to a specific user",
            from_id=from_id,
            to_id=to_id,
            message=message,
            **properties,
        )


class PrivateQuestion(Message):
    TYPE = "private_question"

    def __init__(self, from_id: int, to_id: int, message: Any, **properties):
        super().__init__(
            self.TYPE,
            "send a question to a specific user",
            from_id=from_id,
            to_id=to_id,
            message=message,
            **properties,
        )


class InitMessage(Message):
    TYPE = "init"

    def __init__(self, user_id: int, username: str, **properties):
        super().__init__(
            self.TYPE,
            "Initial connection message from server to the connected client",
            user_id=user_id,
            username=username,
            **properties,
        )


class RoomMessage(Message):
    TYPE = "room_message"

    def __init__(
        self,
        message: str,
        from_id: int,
        room_name: str,
        excluded_users: list[int] = [],
        included_users: list[int] = [],
        **properties,
    ):
        super().__init__(
            self.TYPE,
            "send a message to the current room",
            message=message,
            from_id=from_id,
            excluded_users=excluded_users,
            included_users=included_users,
            room_name=room_name,
            **properties,
        )


class JoinRoomMessage(Message):
    TYPE = "join_room"

    def __init__(self, room: str, **properties):
        super().__init__(
            self.TYPE, "join a room with the given name", room=room, **properties
        )


class LeaveRoomMessage(Message):
    TYPE = "leave_room"

    def __init__(self, **properties):
        super().__init__(self.TYPE, "leave the current room", **properties)


class RematchMessage(Message):
    TYPE = "rematch"

    def __init__(self, **properties):
        super().__init__(self.TYPE, "play a rematch in the current room", **properties)


class RoomJoinedMessage(Message):
    TYPE = "room_joined"

    def __init__(self, room, **properties):
        super().__init__(
            self.TYPE,
            "sent to a client when they join a room",
            room=str(room),
            **properties,
        )


class RoomLeftMessage(Message):
    TYPE = "room_left"

    def __init__(self, room: str, **properties):
        super().__init__(
            self.TYPE,
            "sent to a client when they leave a room",
            room=room,
            **properties,
        )


class UserLeftMessage(Message):
    TYPE = "user_left"

    def __init__(self, user_id: int, room: str, **properties):
        super().__init__(
            self.TYPE,
            "user {user_id} left the room",
            user_id=user_id,
            room=room,
            **properties,
        )


class StartRoomMessage(Message):
    TYPE = "start_room"

    def __init__(self, room: str, **properties):
        super().__init__(self.TYPE, "request to start a room", room=room, **properties)


class RoomStartedMessage(Message):
    TYPE = "room_started"

    def __init__(self, room: str, **properties):
        super().__init__(self.TYPE, "room started", room=room, **properties)


class RoomEndedMessage(Message):
    TYPE = "room_ended"

    def __init__(self, room: str, **properties):
        super().__init__(
            self.TYPE,
            "sent when a room ends",
            room=room,
            **properties,
        )


class RoomDeletedMessage(Message):
    TYPE = "room_deleted"

    def __init__(self, room: str, **properties):
        super().__init__(
            self.TYPE,
            "sent when a room gets deleted by the server, or when every client leaves the room",
            room=room,
            **properties,
        )


class CreateRoomMessage(Message):
    TYPE = "create_room"

    def __init__(
        self,
        room: str,
        max_players: int,
        min_players: int = 2,
        auto_start: bool = True,
        **properties,
    ):
        super().__init__(
            self.TYPE,
            "create a room with the given name and properties",
            room=room,
            max_players=max_players,
            min_players=min_players,
            auto_start=auto_start,
            **properties,
        )


class RoomListMessage(Message):
    TYPE = "room_list"

    def __init__(self, rooms: list[str], **properties):
        super().__init__(
            self.TYPE,
            "list of all rooms",
            rooms=rooms,
            **properties,
        )


class UserListMessage(Message):
    TYPE = "user_list"

    def __init__(self, users: list[str], **properties):
        super().__init__(
            self.TYPE,
            "list of all users",
            users=users,
            **properties,
        )


class ErrorMessage(Message):
    TYPE = "error"

    def __init__(self, error_code, error_message, severity="error", **properties):
        super().__init__(
            self.TYPE,
            error_message,
            **{
                "error_code": error_code,
                "error_message": error_message,
                "severity": severity,
                **properties,
            },
        )
        self.error_code = error_code
        self.error_message = error_message
        self.severity = severity

    def __repr__(self):
        return f"ErrorMessage({self.error_code}: {self.error_message}, {self.json}"


class MessageBundle(Message):
    TYPE = "message_bundle"

    def __init__(self, messages: list[Message], **properties):
        super().__init__(
            self.TYPE,
            "bundle of multiple messages",
            messages=[str(message) for message in messages],
            **properties,
        )

    @property
    def parsed_messages(self):
        return [Message.parse(message) for message in self.messages]


class Question(Message):
    TYPE = "question"
    id_counter: int = 0
    pending: list = []

    def __init__(
        self,
        message: Message,
        callback: Callable = None,
        question_id: str = None,
        sender_id: int | str | None = None,
        process: bool = False,
        **properties,
    ):
        # Serialize message content if it's an object
        if question_id:
            q_id = question_id
        elif sender_id is not None:
            Question.id_counter += 1
            q_id = f"{sender_id}#{Question.id_counter}"
        else:
            q_id = str(uuid4())

        super().__init__(
            self.TYPE,
            "send a message and wait for a response",
            message=str(message),
            question_id=q_id,
            process=process,
            **properties,
        )

        self.message = str(message)
        self.question_id = q_id
        self.callback = callback
        self.process = process

        if self.callback:
            Question.pending.append(self)

    @property
    def parsed_message(self):
        return Message.parse(self.message)

    def answer(self, message: Message | None = None):
        if self not in Question.pending:
            return

        # print(f"Message {self.question_id} got answered: {repr(message)}")
        Question.pending.remove(self)
        if self.callback:
            # Pass question_id, if the callback is interested
            smart_call(self.callback, response=message, question_id=self.question_id)
            # self.callback(message)

    @classmethod
    def answer_question(cls, question_id: str, message: Message | None = None):
        for question in cls.pending:
            if question.question_id == question_id:
                question.answer(message)
                return True

        return False


class Answer(Message):
    TYPE = "answer"

    def __init__(
        self,
        question_id: str,
        message: Message | str | dict,
        process: bool = False,
        **properties,
    ):
        if not isinstance(message, Message):
            message = Message.parse(message)

        super().__init__(
            self.TYPE,
            f"answer to question #{question_id}",
            question_id=question_id,
            process=process,
            message=str(message),
            **properties,
        )

        if not self.process:
            Question.answer_question(self.question_id, message)

    @property
    def parsed_message(self):
        return Message.parse(self.message)
