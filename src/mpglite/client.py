from logging import Logger

from .utils import *
from .message import *
from .exceptions import *
from .logger import get_logger, Loglevel

import math
import json
import threading
import concurrent.futures
import traceback
from websockets.sync.client import connect as ws_connect
from websockets.exceptions import ConnectionClosed, InvalidURI

from typing import Any, Union
from collections.abc import Callable
from websockets.sync.client import ClientConnection


class Client:
    def __init__(
        self,
        host: str,
        port: int,
        loglevel: int | None = None,
        *,
        on_message: Callable[[Any, Union["User", None], "Client"], None] | None = None,
        on_room_joined: Callable[["Room", "Client"], None] | None = None,
        on_room_started: Callable[["Room", "Client"], None] | None = None,
        on_room_ended: Callable[["Room", "Client"], None] | None = None,
        on_room_deleted: Callable[[str, "Client"], None] | None = None,
        on_room_left: Callable[[Union["User", None], Union["Room", None], "Client"], None] | None = None,
        on_room_list: Callable[[list["Room"], "Client"], None] | None = None,
        on_user_list: Callable[[list["User"], "Client"], None] | None = None,
        on_question: Callable[[Any, Union["User", None], "Client"], Any] | None = None,
    ):
        # * WebSocket properties
        self.uri: str = f"ws://{host}:{port}"
        self.__ws: ClientConnection = None
        self._running: bool = False

        # * User properties
        self.user_id: int | None = None
        self.username: str | None = None
        self.room: Room | None = None

        self.__logger: Logger = get_logger(loglevel=loglevel if loglevel else Loglevel.OFF)
        self._users: list[User] = []
        self._users_last: list[str] | None = None
        self._rooms: list[Room] = []
        self._rooms_last: list[str] | None = None

        # * Event handler callbacks
        # When the client receives a ServerMessage message from the server
        self.on_message: Callable[[Any, Union["User", None], "Client"], None] | None = on_message
        smart_kwargs(self.on_message, message=None, sender=None, client=None)

        # When the client receives a ServerMessage question from the server
        self.on_question: Callable[[Any, Union["User", None], "Client"], Any] | None = on_question
        smart_kwargs(self.on_question, question=None, sender=None, client=None)

        # When the client joins a room (room_joined)
        self.on_room_joined: Callable[["Room", "Client"], None] | None = on_room_joined
        smart_kwargs(self.on_room_joined, room=None, client=None)

        # When the client's room starts (room_started)
        self.on_room_started: Callable[["Room", "Client"], None] | None = on_room_started
        smart_kwargs(self.on_room_started, room=None, client=None)

        # When the client's room ends (room_ended)
        self.on_room_ended: Callable[["Room", "Client"], None] | None = on_room_ended
        smart_kwargs(self.on_room_ended, room=None, client=None)

        # When the client's room gets deleted (room_deleted)
        self.on_room_deleted: Callable[[str, "Client"], None] | None = on_room_deleted
        smart_kwargs(self.on_room_deleted, room_name=None, client=None)

        # When someone leaves the client's room (room_left)
        self.on_room_left: Callable[[Union["User", None], Union["Room", None], "Client"], None] | None = on_room_left
        smart_kwargs(self.on_room_left, user=None, room=None, client=None)

        # When the server sends a RoomListMessage
        self.on_room_list: Callable[[list["Room"], "Client"], None] | None = on_room_list
        smart_kwargs(self.on_room_list, rooms=None, client=None)

        # When the server sends a UserListMessage
        self.on_user_list: Callable[[list["User"], "Client"], None] | None = on_user_list
        smart_kwargs(self.on_user_list, users=None, client=None)

    @property
    def _users_filtered(self) -> list["User"]:
        return [user for user in self._users if not user.temp]
    
    @property
    def users(self) -> list["User"]:
        self._users_last = [repr(user) for user in self._users_filtered]
        return self._users_filtered

    @property
    def users_changed(self) -> bool:
        return [repr(user) for user in self._users_filtered] != self._users_last

    @property
    def _rooms_filtered(self) -> list["Room"]:
        return [room for room in self._rooms if not room.lobby]

    @property
    def rooms(self) -> list["Room"]:
        self._rooms_last = [repr(room) for room in self._rooms_filtered]
        return self._rooms_filtered

    @property
    def rooms_changed(self) -> bool:
        return [repr(room) for room in self._rooms_filtered] != self._rooms_last

    def _run_in_thread(self, func: Callable, **kwargs) -> None:
        if func:
            threading.Thread(
                target=smart_call, args=(func,), kwargs=kwargs, daemon=True
            ).start()

    def _listen(self) -> None:
        while self._running:
            try:
                message_json = self.__ws.recv()
                self.__logger.debug(f"Message received: {message_json}")
                message = Message.parse(message_json)

                payload = message
                question_id = None

                if message.type == "question":
                    payload = message.parsed_message
                    question_id = message.question_id
                    self._handle_question(message)
                    continue

                if message.type == "answer":
                    if not message.process:
                        continue
                    payload = message.parsed_message
                    question_id = message.question_id

                messages = (
                    payload.parsed_messages
                    if payload.type == "message_bundle"
                    else [payload]
                )

                for msg in messages:
                    self._handle_message(msg)

                if question_id:
                    Question.answer_question(question_id, payload)
            except ConnectionClosed:
                if self._running:
                    raise ConnectionLostError(
                        "The connection was dropped by the server."
                    )
                break
            except Exception as e:
                self.__logger.critical(f"Listener error: {e}")
                self.__logger.critical(traceback.format_exc())
                self._running = False
                break

    def _handle_message(self, message: Message) -> None:
        match message.type:
            case "init":
                self.user_id = message.user_id
                self.username = message.username

            case "username":
                self.username = message.username

            case "room_list":
                current_room_names = []
                for room_data in message.rooms:
                    room: Room = self._load_room(room_data)

                    room._update(room_data)
                    current_room_names.append(room.name)

                self._rooms = [r for r in self._rooms if r.name in current_room_names]

                self._run_in_thread(
                    self.on_room_list, rooms=self._rooms_filtered, client=self
                )

            case "user_list":
                current_ids = []
                for user_data in message.users:
                    if isinstance(user_data, str):
                        user_data: dict = json.loads(user_data)

                    user = self.get_user_by_id(user_data["user_id"])
                    if user is None:
                        user = User(
                            client=self,
                            logger=self.__logger,
                            user_id=user_data["user_id"],
                            username="Loading...",
                            temp=True,
                        )
                        self._users.append(user)

                    user.username = user_data["username"]
                    user.temp = False
                    current_ids.append(user.user_id)

                # Remove users that are no longer connected
                self._users = [u for u in self._users if u.user_id in current_ids]

                self._run_in_thread(self.on_user_list, users=self._users_filtered, client=self)

            case "room_joined":
                room = self._load_room(message.room)

                if self.room != room:
                    self.__logger.debug(f'Joined to room "{room.name}"')
                    self.room = room
                    self._run_in_thread(self.on_room_joined, room=room, client=self)

            case "room_left":
                self.room = None

            case "room_started":
                room = self.get_room_by_name(message.room)
                room.status = "started"
                self._run_in_thread(self.on_room_started, room=room, client=self)

            case "room_ended":
                room = self.get_room_by_name(message.room)
                if room.status != "ended":
                    room.status = "ended"
                    self._run_in_thread(self.on_room_ended, room=room, client=self)

            case "room_deleted":
                self._run_in_thread(
                    self.on_room_deleted, room_name=message.room, client=self
                )

            case "user_left":
                room = self.get_room_by_name(message.room)
                user = self.get_user_by_id(message.user_id)
                self._run_in_thread(
                    self.on_room_left, user=user, room=room, client=self
                )

            case "server_message" | "private_message" | "room_message":
                sender = None
                if message.type != "server_message":
                    sender = self.get_user_by_id(message.from_id)

                self._run_in_thread(
                    self.on_message,
                    message=message.message,
                    sender=sender,
                    client=self,
                )

    def _handle_question(self, question: Message) -> None:
        message = question.parsed_message
        answer_message = None
        match message.type:
            case "server_message":
                answer = smart_call(
                    self.on_question, question=message.message, sender=None, client=self
                )

                answer_message = ClientMessage(answer)

            case "private_question":
                sender = self.get_user_by_id(message.from_id)

                answer = smart_call(
                    self.on_question,
                    question=message.message,
                    sender=sender,
                    client=self,
                )
                answer_message = ClientMessage(answer)

        if answer_message is not None:
            self._send(
                Answer(question.question_id, answer_message, process=question.process)
            )

    def _load_room(self, room_data: str) -> "Room":
        if isinstance(room_data, str):
            room_data = json.loads(room_data)

        room = self.get_room_by_name(room_data["name"])
        if not room:
            room = Room.parse(self, room_data, self.__logger)
            self._rooms.append(room)

        return room

    def _send(self, message: Message) -> None:
        self.__ws.send(str(message))

    def _send_private_message(self, user_id: int, message: str) -> Message:
        return self._ask(
            PrivateMessage(from_id=self.user_id, to_id=user_id, message=message)
        )

    def _ask_private_question(self, user_id: int, message: str) -> Message:
        return self._ask(
            PrivateQuestion(from_id=self.user_id, to_id=user_id, message=message)
        )

    def send(self, message: Any) -> None:
        """Sends a message to the server."""
        self._send(ClientMessage(message))

    def _ask_async(
        self, message: Message, process: bool = False
    ) -> concurrent.futures.Future:
        """Sends a Question and returns a Future for the Answer."""
        future = concurrent.futures.Future()

        def callback(response):
            future.set_result(response)

        self._send(
            Question(
                message,
                callback,
                process=process,
                sender_id=self.user_id if self.user_id is not None else "client",
            )
        )
        return future

    def _ask(self, message: Message, process: bool = False) -> Any:
        """Sends a Question and waits for an Answer. Returns the answer Message object."""
        return self._ask_async(message, process=process).result()

    def ask(self, message: Any) -> Message:
        """Asks a question from the server and waits for an answer."""
        return self._ask(ClientMessage(message)).message

    def get_user_by_id(self, user_id: int) -> Union["User", None]:
        for user in self._users:
            if user.user_id == user_id:
                return user

        return None

    def get_user_by_username(self, username: str) -> Union["User", None]:
        for user in self._users:
            if user.username == username:
                return user
        return None

    def get_room_by_name(self, name: str) -> Union["Room", None]:
        for room in self._rooms:
            if room.name == name:
                return room
        return None

    def send_room_message(
        self,
        message: Any,
        excluded_users: list | None = None,
        included_users: list | None = None,
        exclude_self=True,
    ) -> Message:
        """Sends a message to all players in the current room."""
        if excluded_users is None:
            excluded_users = []
        if included_users is None:
            included_users = []

        if self.room is None or self.room.lobby:
            return ErrorMessage("ERR_NOT_IN_ROOM", "You are not in a room")

        return self.room.broadcast(
            message,
            excluded_users=excluded_users,
            included_users=included_users,
            exclude_self=exclude_self,
        )

    def ask_room_question(
        self,
        message: Any,
        excluded_users: list | None = None,
        included_users: list | None = None,
        exclude_self=True,
    ) -> dict:
        """Asks a question to all players in the current room."""
        if excluded_users is None:
            excluded_users = []
        if included_users is None:
            included_users = []

        if self.room is None or self.room.lobby:
            return ErrorMessage("ERR_NOT_IN_ROOM", "You are not in a room")

        return self.room.ask_everybody(
            message,
            excluded_users=excluded_users,
            included_users=included_users,
            exclude_self=exclude_self,
        )

    def create_room(
        self,
        room_name: str,
        max_players: int = math.inf,
        min_players: int = 2,
        auto_start: bool = True,
    ) -> Message:
        """Creates a new room and joins to it."""
        return self._ask(
            CreateRoomMessage(
                room=room_name,
                min_players=min_players,
                max_players=max_players,
                auto_start=auto_start,
            ),
            process=True,
        )

    def join_room(self, room_name: str) -> Message:
        """Joins room"""
        return self._ask(JoinRoomMessage(room_name), process=True)

    def leave_room(self) -> Message:
        """Leaves current room"""
        return self._ask(LeaveRoomMessage(), process=True)

    def rematch(self) -> Message:
        if self.room is None or self.room.lobby:
            return ErrorMessage(
                "ERR_NOT_IN_ROOM", "You are not in a room, can't rematch."
            )

        return self._ask(RematchMessage(), process=True)

    def set_username(self, username: str) -> Message:
        return self._ask(Message("set_username", username=username), process=True)

    def connect(self) -> bool:
        """Connects to the server and starts the listener thread"""

        try:
            self.__ws = ws_connect(self.uri)
        except (ConnectionRefusedError, OSError):
            raise ServerNotFoundError(
                f"Failed to connect: Could not reach server at {self.uri}. Is the server running?"
            )
        except ConnectionClosed:
            raise ConnectionLostError(
                "Failed to connect: The connection was dropped by the server."
            )

        self._running = True

        # Start listening in a background thread
        thread = threading.Thread(target=self._listen, daemon=True)
        thread.start()

        self._ask(
            Message("init_request"), process=True
        )  # Wait until the response arrives

        return True

    def disconnect(self) -> None:
        """Disconnects from the server."""
        self._running = False
        if self.__ws:
            self.__ws.close()


class User:
    def __init__(
        self, client: Client, logger: Logger, user_id: int, username: str, temp: bool = False
    ):
        self.__client: Client = client
        self.__logger: Logger = logger
        self.user_id: int = user_id
        self.username: str = username
        self.temp: bool = temp
        self.alive: bool = True

    def __str__(self) -> str:
        return (
            f"User#{self.user_id}({self.username}{' (dead)' if not self.alive else ''})"
        )

    def __repr__(self) -> str:
        json_data = json.dumps(
            {
                "user_id": self.user_id,
                "username": self.username,
                "temp": self.temp,
                "alive": self.alive,
            }
        )
        return f"User({json_data})"

    def send(self, message: str | dict) -> Message:
        return self.__client._send_private_message(self.user_id, message)

    def ask(self, message: Any) -> Any:
        response = self.__client._ask_private_question(self.user_id, message)
        return getattr(response, "message", response)


class Room:
    def __init__(
        self,
        client: Client,
        logger: Logger,
        name: str,
        players: list[User] = [],
        max_players: int = math.inf,
        min_players: int = 2,
        auto_start: bool = True,
        lobby: bool = False,
    ):
        self.__client: Client = client
        self.__logger: Logger = logger
        self.name: str = name
        self.players: dict[int, User] = players
        self.max_players: int = max_players
        self.min_players: int = min_players
        self.auto_start: bool = auto_start
        self.status: str = "open"
        self.lobby: bool = lobby

    @property
    def json(self):
        return json.dumps(
            {
                "name": self.name,
                "players": [str(player) for player in self.players],
                "max_players": self.max_players,
                "min_players": self.min_players,
                "auto_start": self.auto_start,
                "status": self.status,
                "lobby": self.lobby,
            }
        )

    def __str__(self) -> str:
        return f"Room({self.name}, {len(self.players)}/{self.max_players} players, {self.status})"

    def __repr__(self) -> str:
        return f"Room({self.json})"

    def _update(self, room_dict: str | dict) -> None:
        if isinstance(room_dict, str):
            room_dict = json.loads(room_dict)

        self.max_players = room_dict.get("max_players", self.max_players)
        self.min_players = room_dict.get("min_players", self.min_players)
        self.auto_start = room_dict.get("auto_start", self.auto_start)
        self.status = room_dict.get("status", self.status)

        if "users" in room_dict:
            self.players = [
                user
                for user_id in room_dict["users"]
                if (user := self.__client.get_user_by_id(user_id)) is not None
            ]

    def broadcast(
        self,
        message: dict,
        excluded_users: list | None = None,
        included_users: list | None = None,
        exclude_self=True,
    ) -> Message:
        """Send a message to everyone in this room."""

        if excluded_users is None:
            excluded_users = []
        if included_users is None:
            included_users = []

        if self.lobby:
            return ErrorMessage("ERR_ROOM_LOBBY", "Can't send room message to lobby")

        if exclude_self:
            excluded_users.append(self.__client.user_id)

        excluded_users = [
            user.user_id if isinstance(user, User) else user for user in excluded_users
        ]
        included_users = [
            user.user_id if isinstance(user, User) else user for user in included_users
        ]

        self.__logger.debug(f"Broadcasting to room {self.name}: {message}")

        return self.__client._ask(
            RoomMessage(
                message,
                self.__client.user_id,
                self.name,
                excluded_users=excluded_users,
                included_users=included_users,
            )
        )

    def ask_everybody(
        self,
        message: Any,
        timeout: int | None = None,
        excluded_users: list | None = None,
        included_users: list | None = None,
        exclude_self=True,
    ) -> dict[User, Any]:
        if excluded_users is None:
            excluded_users = []
        if included_users is None:
            included_users = []

        if self.lobby:
            return {}

        if exclude_self:
            excluded_users.append(self.__client.user_id)

        excluded_users: list[int] = [
            user.user_id if isinstance(user, User) else user for user in excluded_users
        ]
        included_users: list[int] = [
            user.user_id if isinstance(user, User) else user for user in included_users
        ]

        target_users: list[User] = [
            user
            for user in self.__client._users
            if (user in self.players and user.user_id not in excluded_users)
            or user.user_id in included_users
        ]

        futures = {}
        for user in target_users:
            question = PrivateQuestion(
                from_id=self.__client.user_id, to_id=user.user_id, message=message
            )
            futures[user] = self.__client._ask_async(question)

        done, _ = concurrent.futures.wait(futures.values(), timeout=timeout)

        results = {}
        for user, future in futures.items():
            if future in done:
                try:
                    response = future.result()
                    result = getattr(response, "message", response)
                    if result is not None:
                        results[user] = result
                except Exception:
                    pass

        return results

    def start(self) -> Message:
        if len(self.players) < self.min_players:
            return ErrorMessage(
                "ERR_NOT_ENOUGH_PLAYERS", "Not enough players to start room"
            )

        return self.__client._ask(StartRoomMessage(self.name), process=True)

    def end(self) -> Message:
        return self.__client._ask(EndRoomMessage(self.name), process=True)

    def join(self) -> Message:
        return self.__client.join_room(self.name)

    def leave(self) -> Message:
        return self.__client.leave_room()

    def rematch(self) -> Message:
        return self.__client.rematch()

    @staticmethod
    def parse(client: Client, room_dict: str | dict, logger: Logger):
        if isinstance(room_dict, str):
            room_dict = json.loads(room_dict)

        return Room(
            client=client,
            logger=logger,
            name=room_dict["name"],
            players=[
                user
                for user_id in room_dict["users"]
                if (user := client.get_user_by_id(user_id)) is not None
            ],
            max_players=room_dict["max_players"],
            min_players=room_dict["min_players"],
            auto_start=room_dict["auto_start"],
            lobby=room_dict["lobby"],
        )
