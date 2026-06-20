"""
FolkTown Relay Server - simple threading version, no gevent needed
"""
import os
import json
import threading
from flask import Flask, request, jsonify
from simple_websocket import Server, ConnectionClosed

app = Flask(__name__)

rooms = {}
rooms_lock = threading.Lock()

@app.route("/")
def index():
    return "FolkTown Relay OK"

@app.route("/status")
def status():
    with rooms_lock:
        connected = {r: len(ws) for r, ws in rooms.items()}
    return jsonify({"ok": True, "rooms": connected})

@app.route("/command", methods=["POST"])
def command():
    data   = request.get_json(silent=True) or {}
    room   = str(data.get("room", "default"))
    action = str(data.get("action", "toggle"))
    payload = json.dumps({"action": action})
    sent = 0
    dead = []

    with rooms_lock:
        conns = list(rooms.get(room, []))

    for ws in conns:
        try:
            ws.send(payload)
            sent += 1
        except Exception:
            dead.append(ws)

    if dead:
        with rooms_lock:
            for ws in dead:
                try:
                    rooms.get(room, []).remove(ws)
                except ValueError:
                    pass

    return jsonify({"ok": True, "sent": sent, "room": room})

@app.route("/pc")
def pc_socket():
    room = request.args.get("room", "default")
    ws = Server(request.environ, ping_interval=20)

    with rooms_lock:
        if room not in rooms:
            rooms[room] = []
        rooms[room].append(ws)

    try:
        while True:
            ws.receive()  # blocks, keeps connection alive
    except ConnectionClosed:
        pass
    finally:
        with rooms_lock:
            try:
                rooms.get(room, []).remove(ws)
            except (ValueError, KeyError):
                pass
    return ""

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5001))
    app.run(host="0.0.0.0", port=port, threaded=True)
