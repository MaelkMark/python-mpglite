# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

MPGLite is a lightweight Python multiplayer game engine built on the websockets library. It enables Python beginners to create simple multiplayer games without deep knowledge of async/await or asyncio.

- **Python version**: >=3.10
- **Main dependency**: websockets>=13.0
- **Build system**: Hatchling

## Common Commands

### Install for Development
```bash
pip install -e .
```

### Run Tests
```bash
# Activate the Python 3.10 venv
"venv310/Scripts/activate"

# Run all tests
pytest tests/

# Run a specific test file
pytest tests/test_file_name.py
```

Note: Tests must be run at the file level, not individual test functions, as some tests depend on preceding tests in the same file.

### Troubleshooting Tests
If tests fail due to port conflicts after terminating:
```bash
python tests/free_port.py [PORT]  # Default is 8765
```

## Architecture Overview

### Module Structure

**Source code** (`src/mpglite/`):
- `server.py` - Server-side implementation with `Server`, `Room`, `User` classes
- `client.py` - Client-side implementation with `Client`, `User`, `Room` classes
- `message.py` - Message protocol with `Message` base class and specialized message types (30+ message classes)
- `utils.py` - Utility functions including `smart_call()` and `smart_kwargs()` for flexible callback handling
- `exceptions.py` - Custom exception hierarchy (`MPGLiteError` base)
- `logger.py` - Logging utilities with `Loglevel` enum and colored output

### Key Architectural Patterns

**Dual-Side Design**: Both server and client have their own `User` and `Room` classes. Server-side classes are authoritative; client-side classes are local representations that mirror server state through message updates.

**Message Protocol**: All communication uses JSON messages via the `Message` class hierarchy. Messages are parsed dynamically using `Message.parse()` which converts JSON to the appropriate message subclass based on the `type` field.

**Callback System**: Callbacks are validated at initialization using `smart_kwargs()` which inspects function signatures and raises `SignatureError` if required parameters are missing. This allows flexible callback signatures.

**Question/Answer Pattern**: The `Question` and `Answer` classes enable request-response communication over WebSockets. Questions are tracked in a pending list and answered asynchronously.

**Room Management**:
- A default "lobby" room always exists
- Rooms have states: "open", "started", "ended"
- Auto-start when reaching max_players if `auto_start=True`
- Rematch support via `wants_rematch` tracking

**Threading Model**:
- Server: Asyncio-based with `websockets` library
- Client: Synchronous API with background listener thread for WebSocket messages
- Game callbacks run in daemon threads via `threading.Thread`

### Important Implementation Details

**Room lifecycle**: When creating a room, the user automatically joins it. When all players leave a room (or `on_room_left` returns True), the room is deleted. Rooms cannot be deleted if they are the lobby.

**Callback parameters**: Server callbacks receive `(room, server)` or `(message/question, user, server)` parameters. Client callbacks receive `(room, client)` or `(message/question, sender, client)`.

**User disconnection**: On unexpected disconnect, `User._disconnected()` clears pending questions and removes the user from their room.

**Port configuration**: Tests use port 8765 by default. Server fixtures in tests are module-scoped and run in daemon threads.

## Coding style
- Use a "_" prefix for inner methods of the library that the user shouldn't call
- Use a "__" prefix for inner methods of classes that shouldn't be accessible from outside the class
- Use type annotations

## Writing tests
All of the library's methods should be tested.
Use the util functions of `testingutils.py` and the fixtures of `conftest.py`.
Test different edge cases as well.