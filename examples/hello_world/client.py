from mpglite.client import Client

client = Client("localhost", 8765)
client.connect()
client.send("Hello World!")