"""
FolkTown Relay Server - Fixed version
"""
import os
import json
import threading
from flask import Flask, request, jsonify
from flask_sock import Sock

app = Flask(__name__)
sock = Sock(app)

# room -> list of active websocket connections
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
                    rooms[room].remove(ws)
                except ValueError:
                    pass

    return jsonify({"ok": True, "sent": sent, "room": room})

@sock.route("/pc")
def pc_socket(ws):
    room = request.args.get("room", "default")

    with rooms_lock:
        if room not in rooms:
            rooms[room] = []
        rooms[room].append(ws)

    print(f"[+] PC joined room '{room}' — total: {len(rooms[room])}")

    try:
        while True:
            # Receive keeps connection alive; we send TO the PC
            msg = ws.receive(timeout=25)
            if msg is None:
                break
            # PC sent a ping — just ignore it
    except Exception as e:
        print(f"[-] PC disconnected from '{room}': {e}")
    finally:
        with rooms_lock:
            try:
                rooms[room].remove(ws)
            except (ValueError, KeyError):
                pass
        print(f"[-] PC removed from room '{room}'")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5001))
    app.run(host="0.0.0.0", port=port)
