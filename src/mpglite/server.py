from __future__ import annotations

from .utils import *
from .message import *
from .exceptions import *
from .logger import get_logger, Loglevel

import threading
import websockets
from websockets.exceptions import ConnectionClosed
import asyncio
import json
import math
from importlib.resources import files

from typing import Any
from collections.abc import Callable
from websockets.asyncio.server import ServerConnection


class User:
    id_counter: int = 0

    def __init__(self, logger, socket: ServerConnection, username: str | None = None):
        self.__logger = logger
        self._socket = socket

        User.id_counter += 1
        self.user_id: int = User.id_counter

        self.username: str = username if username else f"Player {self.user_id}"
        self.current_room: Room | None = None
        self.alive = True
        self._pending_questions: list[Question] = []

    def __str__(self):
        return json.dumps({"user_id": self.user_id, "username": self.username})

    async def _send(self, message: Message) -> bool:
        """Helper to send JSON data to this specific user."""
        try:
            # print(f"Sending {str(message)} to user {self.user_id}")

            await self._socket.send(str(message))
            return True
        except websockets.ConnectionClosed:
            return False

    def send(self, message: Any) -> None:
        """Sends data to this specific user."""
        loop = self._socket.loop
        asyncio.run_coroutine_threadsafe(self._send(ServerMessage(message)), loop)

    async def _ask(self, message: Message, process: bool = False) -> Message:
        """Sends a Question and waits for an Answer. Returns the answer Message object."""
        if not self.alive:
            raise UserLeftError(
                f"User #{self.user_id} ({self.username}) has already left the game."
            )

        loop = asyncio.get_running_loop()
        future = loop.create_future()

        def callback(response, question_id):
            if not future.done():
                if isinstance(response, Exception):
                    if question in self._pending_questions:
                        self._pending_questions.remove(question)
                    loop.call_soon_threadsafe(future.set_exception, response)
                    return

                self._pending_questions = [
                    question
                    for question in self._pending_questions
                    if question.question_id != question_id
                ]
                self.__logger.debug(
                    f"Answer received for question {question.question_id} from user #{self.user_id}"
                )
                loop.call_soon_threadsafe(future.set_result, response)

        question: Question = Question(message, callback, process=process, sender_id=0)
        self._pending_questions.append(question)
        self.__logger.debug(f"Sending question #{question.question_id} to user #{self.user_id}")
        await self._send(question)
        return await future

    def ask(self, message: Any, timeout: int | None = None) -> Any:
        loop = self._socket.loop

        try:
            # Check if we're being called from the event loop thread
            running_loop = asyncio.get_running_loop()
            if running_loop is loop:
                raise SyncNotAllowedError(
                    "User.ask() cannot be called from within the event loop thread."
                )
        except RuntimeError:
            # No running loop - we're in a different thread, safe to proceed
            pass

        message_object: ServerMessage = ServerMessage(message)

        future = asyncio.run_coroutine_threadsafe(self._ask(message_object), loop)

        try:
            # The response is a ClientMessage
            return future.result(timeout=timeout).message
        except TimeoutError:
            return None

    async def _disconnected(self):
        self.__logger.info(f"User {self.user_id} disconnected unexpectedly.")
        self.alive = False

        error = UserLeftError(
            f"User #{self.user_id} ({self.username}) has already left the game."
        )

        for question in list(self._pending_questions):
            if question in Question.pending:
                Question.pending.remove(question)
            if question.callback:
                question.callback(error, question.question_id)

        self._pending_questions.clear()

        if self.current_room is not None:
            await self.current_room._remove_user(self)

    def in_room(self, room: Room | str) -> bool:
        return (
            self.current_room == room
            if isinstance(room, Room)
            else self.current_room.name == room
        )


class Room:
    def __init__(
        self,
        server,
        logger,
        name,
        max_players=math.inf,
        min_players=2,
        auto_start=True,
        lobby=False,
    ):
        self.__server = server
        self.__logger = logger

        self.name = name
        self.users: dict[int, User] = {}
        self.wants_rematch: list[int] = []
        self.max_players = max_players
        self.min_players = min_players
        self.auto_start = auto_start
        self.status = "open"
        self.lobby = lobby

    @property
    def players(self):
        return list(self.users.values())

    @property
    def current_players(self):
        return [user for user in self.players if self.user_in_room(user)]

    def __str__(self):
        return json.dumps(
            {
                "name": self.name,
                "users": list(self.users.keys()),
                "status": self.status,
                "max_players": self.max_players,
                "min_players": self.min_players,
                "auto_start": self.auto_start,
                "lobby": self.lobby,
            }
        )
        
    def _user_or_id(self, user: User | int) -> User:
        if isinstance(user, int):
            return self.users[user]
        return user

    def user_in_room(self, user: User | int) -> bool:
        if not (
            user in self.users.values()
            if isinstance(user, User)
            else user in self.users
        ):
            return False

        return (
            user.current_room
            if isinstance(user, User)
            else self.users[user].current_room
        ) == self

    async def _broadcast(
        self,
        message: Message,
        excluded_users: list[int] | None = None,
        included_users: list[int] | None = None,
    ):
        """Send a message to everyone in this room."""
        if excluded_users is None:
            excluded_users = []
        if included_users is None:
            included_users = []

        target_users = [
            user
            for user_id, user in self.__server.users.items()
            if (user_id in self.users.keys() and user_id not in excluded_users)
            or user_id in included_users
        ]

        for user in target_users:
            await user._send(message)

    def _broadcast_sync(
        self,
        message: Message,
        excluded_users: list[int | User] | None = None,
        included_users: list[int | User] | None = None,
    ):
        """
        Synchronous version of _broadcast.
        """
        if excluded_users is None:
            excluded_users = []
        if included_users is None:
            included_users = []

        excluded_users = [
            user.user_id if isinstance(user, User) else user for user in excluded_users
        ]
        included_users = [
            user.user_id if isinstance(user, User) else user for user in included_users
        ]

        if not self.users:
            return

        loop = next(iter(self.users.values()))._socket.loop
        asyncio.run_coroutine_threadsafe(
            self._broadcast(message, excluded_users, included_users), loop
        )

    def broadcast(
        self,
        message: Any,
        excluded_users: list[int | User] | None = None,
        included_users: list[int | User] | None = None,
    ):
        """
        Send a message to everyone in this room.
        """
        if excluded_users is None:
            excluded_users = []
        if included_users is None:
            included_users = []

        excluded_users = [
            user.user_id if isinstance(user, User) else user for user in excluded_users
        ]
        included_users = [
            user.user_id if isinstance(user, User) else user for user in included_users
        ]

        if not self.users:
            return

        excluded_users: list[int] = [
            user.user_id if isinstance(user, User) else user for user in excluded_users
        ]
        included_users: list[int] = [
            user.user_id if isinstance(user, User) else user for user in included_users
        ]

        return self._broadcast_sync(
            ServerMessage(message),
            excluded_users=excluded_users,
            included_users=included_users,
        )

    async def _add_user(self, user: User) -> Message:
        if len(self.users) >= self.max_players:
            return ErrorMessage(
                "ERR_ROOM_FULL",
                f'Room "{self.name}" is full. Cannot add user #{user.user_id}.',
            )

        if self.status != "open":
            return ErrorMessage(
                "ERR_ROOM_NOT_OPEN",
                f'Room "{self.name}" is not open. Cannot add user #{user.user_id}.',
            )

        self.__logger.debug(f'Adding user #{user.user_id} to room "{self.name}"')
        self.users[user.user_id] = user

        await self.__server.users[user.user_id]._send(RoomJoinedMessage(self))

        if self.auto_start and len(self.users) == self.max_players:
            self.__logger.debug(f'Starting room "{self.name}" automatically...')
            self.start()

        return OKMessage()

    async def _remove_user(self, user: User):
        self.__logger.debug(f'Removing user #{user.user_id} from room "{self.name}"')

        user_id = user.user_id
        if user_id in self.users:
            user.current_room = None
            # del self.users[user_id]  # Do not delete the user from self.users, because the server user may need to reference it. Users who have left the room won't be included in self.current_players.

        if not self.lobby:
            if user_id in self.wants_rematch:
                self.wants_rematch.remove(user_id)

            delete = smart_call(
                self.__server.on_room_left, room=self, user=user, server=self.__server
            )

            await self._broadcast(UserLeftMessage(user_id, self.name))
            if len(self.current_players) == 0 or delete:
                self.__server._delete_room(self.name)

    def _wants_rematch(self, user: User) -> Message:
        if user.user_id not in self.users:
            return ErrorMessage(
                "ERR_REMATCH_USER_NOT_IN_ROOM",
                f'User #{user.user_id} is not in room "{self.name}".',
            )

        if user.user_id not in self.wants_rematch:
            self.wants_rematch.append(user.user_id)

        self.__logger.debug(
            f'Rematch requested by user #{user.user_id} in room "{self.name}" ({len(self.wants_rematch)}/{len(self.users)})'
        )

        if len(self.wants_rematch) == len(self.users):
            self.wants_rematch = []
            return self.rematch()

        return OKMessage()

    async def _ask_everybody_async(
        self,
        message: Message,
        process: bool = False,
        excluded_users: list[int | User] = None,
        included_users: list[int | User] = None,
    ) -> dict[User, Any]:
        """Internal async handler to ask everyone at the same time."""

        if excluded_users is None:
            excluded_users = []
        if included_users is None:
            included_users = []

        excluded_users = [
            user.user_id if isinstance(user, User) else user for user in excluded_users
        ]
        included_users = [
            user.user_id if isinstance(user, User) else user for user in included_users
        ]

        tasks = {
            user: (user._ask(message, process=process))
            for user in self.__server.users.values()
            if (user.in_room(self) and user.user_id not in excluded_users)
            or user.user_id in included_users
        }

        results: list[ClientMessage] = await asyncio.gather(*tasks.values())
        results: list[Any] = [message.message for message in results]

        return {
            user: result
            for user, result in zip(tasks.keys(), results)
            if result is not None
        }

    def ask_everybody(
        self,
        message: Any,
        timeout: int | None = None,
        excluded_users: list[int | User] = None,
        included_users: list[int | User] = None,
    ) -> dict[User, Any]:
        """
        Asks every player a question and returns a dict of {user_id: Message}.
        """
        self.__logger.debug(f'Asking everybody in room "{self.name}"', message)

        if excluded_users is None:
            excluded_users = []
        if included_users is None:
            included_users = []

        if not self.users:
            return {}

        loop = next(iter(self.users.values()))._socket.loop

        message_object: ServerMessage = ServerMessage(message)

        future = asyncio.run_coroutine_threadsafe(
            self._ask_everybody_async(
                message_object,
                process=False,
                excluded_users=excluded_users,
                included_users=included_users,
            ),
            loop,
        )

        try:
            return future.result(timeout=timeout)
        except TimeoutError:
            self.__logger.warning(f'Room "{self.name}": ask_everybody timed out!')
            return {}

    def ask_player(
        self, player: int | User, message: Any, timeout: int | None = None
    ) -> Any:
        """
        Asks a specific player a question and returns the answer as a string.
        If the player is not in the room, or if it times out, returns None.
        """
        if not self.user_in_room(player):
            user = self._user_or_id(player)
            raise UserLeftError(
                f"User #{user.user_id} ({user.username}) has already left the game."
            )

        return self.__server.ask_player(player, message, timeout=timeout)

    def start(self) -> Message:
        if self.lobby:
            return ErrorMessage(
                "ERR_LOBBY_CANNOT_BE_STARTED", "Lobby cannot be started."
            )
        if len(self.users) < self.min_players:
            return ErrorMessage("ERR_NOT_ENOUGH_PLAYERS", "Not enough players.")

        self.__logger.debug(f'Starting room "{self.name}"...')

        self.status = "started"

        self.__server._room_started(self)

        message = RoomStartedMessage(self.name)
        asyncio.create_task(self._broadcast(message))
        return message

    async def _end(self) -> Message:
        self.status = "ended"

        # Remove users who left the room earlier
        for user_id in [
            user_id for user_id, user in self.users.items() if user.current_room != self
        ]:
            del self.users[user_id]

        await self._broadcast(RoomEndedMessage(self.name))
        asyncio.create_task(self.__server._rooms_updated())
        return RoomEndedMessage(self.name)

    def end(self) -> Message:
        loop = next(iter(self.users.values()))._socket.loop
        future = asyncio.run_coroutine_threadsafe(self._end(), loop)
        return future.result()

    def rematch(self) -> Message:
        self.__logger.debug(f'Rematching room "{self.name}"...')
        return self.start()

    def delete(self) -> Message:
        return self.__server._delete_room(self.name)


class Lobby(Room):
    def __init__(self, server, logger):
        super().__init__(
            server=server,
            logger=logger,
            name="lobby",
            max_players=math.inf,
            min_players=0,
            auto_start=False,
            lobby=True,
        )


class Server:
    def __init__(
        self,
        host: str,
        port: int,
        loglevel: Loglevel = Loglevel.OFF,
        print_logo: bool = True,
        exception_when_user_leaves: bool = False,
        on_user_joined: Callable = None,
        on_room_start: Callable = None,
        on_room_left: Callable = None,
        on_message: Callable = None,
        on_question: Callable = None,
    ):
        # * Server properties
        self.host: str = host
        self.port: int = port
        self.__logger = get_logger(loglevel=(loglevel if loglevel else Loglevel.OFF))
        self.rooms: dict[str, Room] = {"lobby": Lobby(self, self.__logger)}
        self.users: dict[int, User] = {}
        self.__ws_server = None
        self.__stop_event = asyncio.Event()

        # * Options
        self.exception_when_user_leaves: bool = exception_when_user_leaves

        # * Event handler callbacks
        # smart_kwargs tests if the user passed proper properties to the callback functions.
        self.on_user_joined: Callable | None = on_user_joined
        smart_kwargs(self.on_user_joined, user=None, server=None)
        
        self.on_room_start: Callable | None = on_room_start
        smart_kwargs(self.on_room_start, room=None, server=None)

        self.on_message: Callable | None = on_message
        smart_kwargs(self.on_message, message=None, user=None, server=None)

        self.on_question: Callable | None = on_question
        smart_kwargs(self.on_question, question=None, user=None, server=None)

        self.on_room_left: Callable | None = on_room_left
        smart_kwargs(self.on_room_left, room=None, user=None, server=None)

        if print_logo:
            path = files("mpglite").joinpath("logo.txt")
            with open(path, encoding="utf-8") as logo:
                print(logo.read())

    async def _main(self):
        self.loop = asyncio.get_running_loop()
        async with websockets.serve(self._handler, self.host, self.port) as ws_server:
            self.__logger.info(f"Server started on ws://{self.host}:{self.port}")
            self.__ws_server = ws_server
            await self.__stop_event.wait()
            self.__logger.info("Server shutting down...")

    async def _broadcast(self, message: Message):
        self.__logger.debug(f"Broadcasting: {repr(message)}")

        for user in self.users.values():
            await user._send(message)

    async def _handler(self, websocket: ServerConnection):
        user = User(self.__logger, websocket)
        self.users[user.user_id] = user

        # Join lobby by default
        room = self.rooms["lobby"]
        await room._add_user(user)
        user.current_room = room
        await self._rooms_updated()
        await self._users_updated()
        
        # smart_call(self.on_user_joined, user=user, server=self)
        threading.Thread(
            target=smart_call,
            args=(self.on_user_joined,),
            kwargs={
                "user": user,
                "server": self
            },
            daemon=True
        ).start()

        try:
            async for message_json in websocket:
                # data: dict = json.loads(message_json)
                # msg_type: str = data.get("type")

                self.__logger.debug(f"Received message: {message_json}")

                message: Message = Message.parse(message_json)
                message_type = message.type

                if message_type == "question":
                    question_message = message.parsed_message

                    await self._handle_question(message, question_message, user)
                else:
                    await self._handle_message(user, message)

        except ConnectionClosed:
            await user._disconnected()
            await self._rooms_updated()
            await self._users_updated()

            if self.exception_when_user_leaves:
                raise UserLeftError(
                    f"User #{user.user_id} ({user.username}) left the game."
                )
        finally:
            if user.current_room:
                await user.current_room._remove_user(user)
            if user.user_id in self.users:
                del self.users[user.user_id]

    async def _handle_message(self, user: User, message: Message):
        match message.type:
            case "join_room":
                await self._join_room(user, message.room)

            case "create_room":
                await self._create_room(
                    user,
                    room_name=message.room,
                    max_players=message.max_players,
                    min_players=message.min_players,
                    auto_start=message.auto_start,
                )

            case "get_room_list":
                await user._send(self._get_room_list_message())

            case "client_message":
                # smart_call(
                #     self.on_message, message=message.message, user=user, server=self
                # )
                
                threading.Thread(
                    target=smart_call,
                    args=(self.on_message,),
                    kwargs={
                        "message": message.message,
                        "user": user,
                        "server": self
                    },
                    daemon=True
                ).start()

    async def _handle_question(self, question: Question, message: Message, user: User):
        self.__logger.debug(f"Handling question #{question.question_id}: {message}")

        async def answer(answer_message: Message):
            self.__logger.debug(
                f"Answering question {question.question_id} with {answer_message}"
            )

            await user._send(
                Answer(question.question_id, answer_message, process=question.process)
            )

        match message.type:
            case "init_request":
                await answer(
                    MessageBundle(
                        [
                            InitMessage(user.user_id, user.username),
                            self._get_user_list_message(),
                            self._get_room_list_message(),
                        ]
                    )
                )
            case "get_room_list":
                await answer(self._get_room_list_message())

            case "join_room":
                await answer(await self._join_room(user, message.room))

            case "leave_room":
                if user.current_room is None:
                    await answer(
                        ErrorMessage("ERR_NOT_IN_ROOM", "You are not in a room.")
                    )

                await answer(await self._leave_room(user, user.current_room.name))

                if self.exception_when_user_leaves:
                    raise UserLeftError(
                        f"User #{user.user_id} ({user.username}) left the game."
                    )

            case "start_room":
                room = self.rooms.get(message.room)
                if room is None:
                    await answer(
                        ErrorMessage(
                            "ERR_NO_SUCH_ROOM",
                            f"There's no room named {message.room}.",
                        )
                    )

                await answer(room.start())

            case "end_room":
                room = self.rooms.get(message.room)
                if room is None:
                    await answer(
                        ErrorMessage(
                            "ERR_NO_SUCH_ROOM",
                            f"There's no room named {message.room}.",
                        )
                    )

                await answer(await room._end())

            case "rematch":
                room = user.current_room
                if room is None:
                    await answer(
                        ErrorMessage(
                            "ERR_REMATCH_NO_ROOM",
                            "You are not in a room, can't rematch.",
                        )
                    )
                else:
                    await answer(room._wants_rematch(user))

            case "set_username":
                username = message.username
                if any(user.username == username for user in self.users.values()):
                    await answer(
                        ErrorMessage("ERR_USERNAME_TAKEN", "Username already taken")
                    )
                else:
                    user.username = username
                    await answer(Message("username", username=user.username))
                    await self._users_updated()

            case "create_room":
                await answer(
                    await self._create_room(
                        user,
                        room_name=message.room,
                        min_players=message.min_players,
                        max_players=message.max_players,
                        auto_start=message.auto_start,
                    )
                )

            case "client_message":
                await answer(
                    ServerMessage(
                        smart_call(
                            self.on_question,
                            question=message.message,
                            user=user,
                            server=self,
                        )
                    )
                )

            case "private_message":
                if message.to_id not in self.users:
                    await answer(
                        ErrorMessage(
                            "ERR_NO_SUCH_USER",
                            f"There's no user with id {message.to_id}.",
                        )
                    )
                else:
                    await self.users[message.to_id]._send(message)
                    await answer(OKMessage())

            case "private_question":
                if message.to_id not in self.users:
                    await answer(
                        ErrorMessage(
                            "ERR_NO_SUCH_USER",
                            f"There's no user with id {message.to_id}.",
                        )
                    )
                else:
                    await answer(await self.users[message.to_id]._ask(message))

            case "room_message":
                if message.room_name:
                    room = self.rooms[message.room_name]
                else:
                    room = user.current_room

                await room._broadcast(
                    message,
                    excluded_users=message.excluded_users,
                    included_users=message.included_users,
                )
                await answer(OKMessage())

    async def _join_room(self, user: User, room_name: str) -> Message:
        if room_name not in self.rooms or self.rooms[room_name].lobby:
            return ErrorMessage(
                "ERR_NO_SUCH_ROOM",
                f"There's no room named {room_name}.",
            )

        room = self.rooms[room_name]

        if user.current_room == room:
            return OKMessage()

        if user.current_room:
            await user.current_room._remove_user(user)

        result = await room._add_user(user)
        if result.ok:
            user.current_room = room
            result = RoomJoinedMessage(room)
            await self._rooms_updated()

        return result

    async def _leave_room(self, user: User, room_name: str) -> Message:
        if room_name not in self.rooms:
            return ErrorMessage(
                "ERR_NO_SUCH_ROOM",
                f"There's no room named {room_name}.",
            )

        if self.rooms[room_name].lobby:
            return ErrorMessage("ERR_LOBBY_CANNOT_BE_LEFT", "You can't leave lobby.")

        room = self.rooms[room_name]
        await room._remove_user(user)
        user.current_room = None

        await self._users_updated()
        await self._rooms_updated()
        return RoomLeftMessage(room.name)

    async def _create_room(
        self,
        user: User,
        room_name: str,
        max_players: int,
        min_players: int,
        auto_start: bool,
    ) -> Message:

        if room_name in self.rooms.keys():
            return ErrorMessage(
                "ERR_ROOM_EXISTS", f'Room "{room_name}" already exists.'
            )

        self.rooms[room_name] = Room(
            server=self,
            logger=self.__logger,
            name=room_name,
            max_players=max_players,
            min_players=min_players,
            auto_start=auto_start,
        )

        await self._join_room(user, room_name)
        await self._rooms_updated()
        return OKMessage()

    def _delete_room(self, room_name: str) -> Message:
        if room_name not in self.rooms:
            return ErrorMessage(
                "ERR_NO_SUCH_ROOM", f"There's no room named {room_name}."
            )

        room = self.rooms[room_name]

        if room.lobby:
            return ErrorMessage(
                "ERR_LOBBY_CANNOT_BE_DELETED", "Lobby cannot be deleted."
            )

        asyncio.create_task(room._broadcast(RoomDeletedMessage(room.name)))

        for user in room.users.values():
            user.current_room = None

        del self.rooms[room_name]
        asyncio.create_task(self._rooms_updated())

        return RoomDeletedMessage(room.name)

    def _get_room_list_message(self) -> RoomListMessage:
        return RoomListMessage([str(room) for room in self.rooms.values()])

    def _get_user_list_message(self) -> UserListMessage:
        return UserListMessage([str(user) for user in self.users.values()])

    async def _rooms_updated(self) -> None:
        self.__logger.debug("Rooms updated")

        await self._broadcast(self._get_room_list_message())

    async def _users_updated(self) -> None:
        self.__logger.debug("Users updated")

        await self._broadcast(self._get_user_list_message())

    def _room_started(self, room: Room):
        asyncio.create_task(self._rooms_updated())

        if self.on_room_start:
            game_kwargs = smart_kwargs(self.on_room_start, room=room, server=self)

            thread = threading.Thread(
                target=self.on_room_start, kwargs=game_kwargs, daemon=True
            )
            thread.start()

    def _user_or_id(self, user: User | int) -> User:
        if isinstance(user, int):
            return self.users[user]
        return user

    def ask_player(
        self, player: int | User, message: Any, timeout: int | None = None
    ) -> Any:
        """
        Asks a specific player a question and returns the answer as a string.
        If the user is not found, or if it times out, returns None.
        """
        user_to_ask = self._user_or_id(player)
        if user_to_ask is None:
            return None

        return user_to_ask.ask(message, timeout=timeout)

    def send_to_player(self, player: int | User, message: Any) -> None:
        user_to_send = self._user_or_id(player)
        if user_to_send is None:
            return None

        user_to_send.send(message)

    def start(self):
        """Starts the websocket server"""
        try:
            asyncio.get_running_loop()
            return self._main()
        except RuntimeError:
            asyncio.run(self._main())

    def stop(self):
        """Stop the server."""
        if hasattr(self, "loop"):
            self.loop.call_soon_threadsafe(self.__stop_event.set)
        else:
            # If running in the same thread (like in a test)
            self.__stop_event.set()
