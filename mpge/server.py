from .utils import *
from .message import *

import threading
import websockets
from websockets.exceptions import ConnectionClosed
import asyncio
import json
import math

from typing import Any
from collections.abc import Callable
from websockets.asyncio.server import ServerConnection


class User:
    id_counter = 0

    def __init__(self, socket: ServerConnection, username: str | None = None):
        self.socket = socket

        User.id_counter += 1
        self.user_id = User.id_counter

        self.username = username if username else f"Player {self.user_id}"
        self.current_room: Room | None = None

    def __str__(self):
        return json.dumps({"user_id": self.user_id, "username": self.username})

    async def _send(self, message: Message) -> bool:
        """Helper to send JSON data to this specific user."""
        try:
            # print(f"Sending {str(message)} to user {self.user_id}")
            await self.socket.send(str(message))
            return True
        except websockets.ConnectionClosed:
            return False

    def send(self, message: Any) -> None:
        """Sends data to this specific user."""
        loop = self.socket.loop
        asyncio.run_coroutine_threadsafe(self._send(ServerMessage(message)), loop)

    async def _ask(self, message: Message, process: bool = False) -> Message:
        """Sends a Question and waits for an Answer. Returns the answer Message object."""
        loop = asyncio.get_running_loop()
        future = loop.create_future()

        def callback(response):
            if not future.done():
                loop.call_soon_threadsafe(future.set_result, response)

        await self._send(Question(message, callback, process=process))
        return await future

    def ask(self, message: Any, timeout: int | None = None) -> Any:
        loop = self.socket.loop

        message_object: ServerMessage = ServerMessage(message)

        future = asyncio.run_coroutine_threadsafe(self._ask(message_object), loop)

        try:
            return future.result(timeout=timeout).message
        except TimeoutError:
            return None

    def _disconnected(self, server):
        print(f"User {self.user_id} disconnected unexpectedly.")
        room = self.current_room
        if room is not None:
            room._remove_user(self)

            if len(room.users) == 0:
                server._delete_room(room.name)


class Room:
    def __init__(
        self,
        server,
        name,
        max_players=math.inf,
        min_players=2,
        auto_start=True,
        lobby=False,
    ):
        self.server = server
        self.name = name
        self.users: dict[int, User] = {}
        self.max_players = max_players
        self.min_players = min_players
        self.auto_start = auto_start
        self.status = "open"
        self.lobby = lobby

    @property
    def players(self):
        return list(self.users.values())

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

    async def _broadcast(self, data: dict, excluded_users: list[int] = None):
        """
        Send a message to everyone in this room.

        Args:
            data (dict): data to send, it will be converted into a JSON string.
            excluded_users (list[int]): list of user IDs to whom you don't want to send the message.
        """
        if excluded_users is None:
            excluded_users = []

        message = json.dumps(data)
        for user_id, user in self.users.items():
            if user_id not in excluded_users:
                await user._send(message)

    def broadcast(self, data: dict, excluded_users: list[int] = None):
        """
        Synchronous version of _broadcast.
        """
        if not self.users:
            return

        loop = next(iter(self.users.values())).socket.loop
        asyncio.run_coroutine_threadsafe(self._broadcast(data, excluded_users), loop)

    def _add_user(self, user: User) -> Message:
        if len(self.users) >= self.max_players:
            return ErrorMessage(
                "ERR_ROOM_FULL",
                f'Room "{self.name}" is full. Cannot add user #{user.user_id}.',
            )

        self.users[user.user_id] = user

        print("sending RoomJoinedMessage")
        asyncio.create_task(
            self.server.users[user.user_id]._send(RoomJoinedMessage(self.name))
        )

        print(
            f"Auto start: {self.auto_start}, users: {len(self.users)}, max_players: {self.max_players}"
        )
        if self.auto_start and len(self.users) == self.max_players:
            print(f'Starting room "{self.name}" automatically...')
            self.start()

        return OKMessage()

    def _remove_user(self, user: User):
        user_id = user.user_id
        if user_id in self.users:
            user.current_room = None
            del self.users[user_id]

    async def _ask_everybody_async(
        self, message: Message, process: bool = False
    ) -> dict[int, Any]:
        """Internal async handler to ask everyone at the same time."""
        tasks = {
            user.user_id: user._ask(message, process=process)
            for user in self.users.values()
        }

        results = await asyncio.gather(*tasks.values())
        results = [message.message for message in results]

        return dict(zip(tasks.keys(), results))

    def ask_everybody(self, message: Any, timeout: int | None = None) -> dict[int, Any]:
        """
        Asks every player a question and returns a dict of {user_id: Message}.
        """
        if not self.users:
            return {}

        loop = next(iter(self.users.values())).socket.loop

        message_object: ServerMessage = ServerMessage(message)

        future = asyncio.run_coroutine_threadsafe(
            self._ask_everybody_async(message_object), loop
        )

        try:
            return future.result(timeout=timeout)
        except TimeoutError:
            print(f'Room "{self.name}": ask_everybody timed out!')
            return {}

    def ask_player(
        self, player: int | User, message: Any, timeout: int | None = None
    ) -> Any:
        """
        Asks a specific player a question and returns the answer as a string.
        If the player is not in the room, or if it times out, returns None.
        """
        return self.server.ask_player(player, message, timeout=timeout)

    def start(self) -> Message:
        if self.lobby:
            return ErrorMessage(
                "ERR_LOBBY_CANNOT_BE_STARTED", "Lobby cannot be started."
            )
        if len(self.users) < self.min_players:
            return ErrorMessage("ERR_NOT_ENOUGH_PLAYERS", "Not enough players.")

        self.status = "started"
        asyncio.create_task(self.server._rooms_updated())
        self.server._room_started(self)
        message = RoomStartedMessage(self)
        self.broadcast(message)
        return message


class Lobby(Room):
    def __init__(
        self, name="lobby", max_players=math.inf, min_players=0, auto_start=True
    ):
        super().__init__(name, max_players, min_players, auto_start, lobby=True)


class Server:
    def __init__(
        self,
        host: str,
        port: int,
        logging: bool = False,
        on_room_start: Callable = None,
        on_message: Callable = None,
        on_question: Callable = None,
    ):
        self.host: str = host
        self.port: int = port
        self.logging: bool = logging
        self.rooms: dict[str, Room] = {"lobby": Lobby()}
        self.users: dict[int, User] = {}

        # smart_kwargs tests if the user passed proper properties to the callback functions.
        self.on_room_start: Callable | None = on_room_start
        smart_kwargs(self.on_room_start, room=None, server=None)

        self.on_message: Callable | None = on_message
        smart_kwargs(self.on_message, message=None, user=None, server=None)

        self.on_question: Callable | None = on_question
        smart_kwargs(self.on_question, question=None, user=None, server=None)

    async def _main(self):
        async with websockets.serve(self._handler, self.host, self.port):
            if self.logging:
                print(f"Server is running on {self.host}:{self.port}")

            await asyncio.Future()

    async def _broadcast(self, message: Message):
        if self.logging:
            print(f"Broadcasting: {repr(message)}")

        for user in self.users.values():
            await user._send(message)

    async def _handler(self, websocket: ServerConnection):
        user = User(websocket)
        self.users[user.user_id] = user

        # Join lobby by default
        room = self.rooms["lobby"]
        room._add_user(user)
        user.current_room = room
        await self._rooms_updated()
        await self._users_updated()

        try:
            async for message_json in websocket:
                # data: dict = json.loads(message_json)
                # msg_type: str = data.get("type")

                if self.logging:
                    print(f"Received message: {message_json}")

                message: Message = Message.parse(message_json)
                message_type = message.type

                if message_type == "question":
                    question_message = message.parsed_message
                    question_id = message.question_id

                    await self._handle_question(message, question_message, user)
                else:
                    await self._handle_message(user, message)

        except ConnectionClosed:
            user._disconnected(self)
            await self._rooms_updated()
            await self._users_updated()
        finally:
            if user.current_room:
                user.current_room._remove_user(user)
            if user.user_id in self.users:
                del self.users[user.user_id]

    async def _handle_message(self, user: User, message: Message):
        match message.type:
            case "join_room":
                user._send(await self._join_room(user, message.room))

            case "create_room":
                await self._create_room(
                    user,
                    room_name=message.room,
                    min_players=message.min_players,
                    max_players=message.max_players,
                    auto_start=message.auto_start,
                )

            case "room_message":
                content = message.message
                if self.logging:
                    print(f'User {user.user_id} sent: "{content}"')

                if message.room_name:
                    room = self.rooms[message.room_name]
                else:
                    room = user.current_room

                await room._broadcast(
                    content,
                    [user.user_id, *message.excluded_users],
                )

            case "get_room_list":
                await user._send(self._get_room_list_message())

            case "client_message":
                smart_call(
                    self.on_message, message=message.message, user=user, server=self
                )

    async def _handle_question(
        self, question: Question, question_message: Message, user: User
    ):
        answer_message = None
        match question_message.type:
            case "init_request":
                answer_message = MessageBundle(
                    [
                        InitMessage(user.user_id, len(self.users)),
                        self._get_user_list_message(),
                        self._get_room_list_message(),
                    ]
                )
            case "get_room_list":
                answer_message = self._get_room_list_message()

            case "join_room":
                answer_message = await self._join_room(user, question_message.room)

            case "set_username":
                username = question_message.username
                if any(user.username == username for user in self.users.values()):
                    answer_message = ErrorMessage(
                        "ERR_USERNAME_TAKEN", "Username already taken"
                    )
                else:
                    user.username = username
                    answer_message = Message("username", username=user.username)
                    await self._users_updated()

            case "create_room":
                answer_message = await self._create_room(
                    user,
                    room_name=question_message.room,
                    min_players=question_message.min_players,
                    max_players=question_message.max_players,
                    auto_start=question_message.auto_start,
                )

            case "client_message":
                answer_message = ServerMessage(
                    smart_call(
                        self.on_question,
                        question=question_message.message,
                        user=user,
                        server=self,
                    )
                )

        if answer_message is not None:
            await user._send(
                Answer(question.question_id, answer_message, process=question.process)
            )

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
            user.current_room._remove_user(user)

        room._add_user(user)
        user.current_room = room

        await self._rooms_updated()
        return OKMessage()

    async def _create_room(
        self, user: User, room_name: str, max_players: int, **kwargs
    ) -> Message:

        if room_name in self.rooms.keys():
            return ErrorMessage(
                "ERR_ROOM_EXISTS", f'Room "{room_name}" already exists.'
            )

        self.rooms[room_name] = Room(self, room_name, max_players, **kwargs)

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

        for user in room.users.values():
            user.current_room = None

        del self.rooms[room_name]
        asyncio.create_task(self._rooms_updated())

        return OKMessage()

    def _get_room_list_message(self) -> RoomListMessage:
        return RoomListMessage([str(room) for room in self.rooms.values()])

    def _get_user_list_message(self) -> UserListMessage:
        return UserListMessage([str(user) for user in self.users.values()])

    async def _rooms_updated(self) -> None:
        if self.logging:
            print("Rooms updated")

        await self._broadcast(self._get_room_list_message())

    async def _users_updated(self) -> None:
        if self.logging:
            print("Users updated")

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
        asyncio.run(self._main())


print(
    rf"""
<<>><<>><<>><<>><<>><<>><<>><<>><<>><<>><<>><<>><<>><<>>
    
    /\\       /\\  /\\\\\\\       /\\\\     /\\\\\\\\
    /\ /\\   /\\\  /\\    /\\   /\    /\\   /\\      
    /\\ /\\ / /\\  /\\    /\\  /\\          /\\      
    /\\  /\\  /\\  /\\\\\\\    /\\          /\\\\\\  
    /\\   /\  /\\  /\\         /\\   /\\\\  /\\      
    /\\       /\\  /\\          /\\    /\   /\\      
    /\\       /\\  /\\           /\\\\\     /\\\\\\\\
    
    {"Python Multiplayer Game Engine":^49}
    {"Made with ❤  by Márk":^49}
    
<<>><<>><<>><<>><<>><<>><<>><<>><<>><<>><<>><<>><<>><<>>
    
"""
)
