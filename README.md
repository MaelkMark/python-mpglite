<div align="center" style="text-align: center">
    <h1>MPGLite</h1>
    <p>v0.1.0 BETA</p>
</div>

MPGLite is a lightweight Python multiplayer game engine built on the [websockets](https://github.com/python-websockets/websockets) library. Its goal is to enable Python beginners and developers unfamiliar with async/await or asyncio to easily and quickly create simple multiplayer games. Have you ever created a simple game that runs in the terminal and wondered if you could make it multiplayer? Then this might be the right library for you. MPGLite is designed so you have to write as few additional code as possible, handles repetitive and complex tasks, taking the weight off your shoulders. However, it is not meant to handle robust multiplayer games or thousands of players.

## Features
- Server and client side
- Built-in "room" functionalities
- Easy communication between the server and clients
- Simple callback implementation
- Customizable for any game.

## Hello, Server!
Here's a simple example of a client greeting the server:

server.py
```py
from mpglite.server import Server

def message_received(message):
    print("Message received:", message)

server = Server(
    "localhost",
    8765,
    on_message=message_received
)
server.start()
```

client.py
```py
from mpglite.client import Client

client = Client("localhost", 8765)
client.connect()

client.send("Hello, Server!")
```

## Installation
```
pip install mpglite
```