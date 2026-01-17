<div align="center" style="text-align: center">
    <h1>MPGLite</h1>
    <p>A simple Python multiplayer game engine</p>
    <p>v0.1.0 BETA</p>
    <a href="https://github.com/MaelkMark/python-mpglite/actions/workflows/tests.yml">
        <img src="https://github.com/MaelkMark/python-mpglite/actions/workflows/tests.yml/badge.svg" alt="Tests Status">
    </a>
</div>

MPGLite is a lightweight Python multiplayer game engine built on the [websockets](https://github.com/python-websockets/websockets) library. Its goal is to enable Python beginners and developers unfamiliar with async/await or asyncio to easily and quickly create simple multiplayer games. Have you ever created a simple game and wondered if you could make it multiplayer? Then this might be the right library for you. MPGLite is designed so you have to write as few additional code as possible, handles repetitive and complex tasks, taking the weight off your shoulders. However, it is not for handling robust multiplayer games or thousands of players.

<!-- omit from toc -->
## Table of Contents
- [Features](#features)
- [Hello, Server!](#hello-server)
- [Installation](#installation)


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
