from mpglite.server import Server

def message_received(message):
    print("Message received:", message)

server = Server(
    "localhost",
    8765,
    on_message=message_received
)

server.start()