"""
FolkTown Relay Server
=====================
Deploy this on Render.com (free tier) once.
Both the watch (via HTTP) and the PC .exe (via WebSocket) connect to this.

Endpoints:
  GET  /status          - health check
  POST /command         - watch sends {"action": "toggle"|"pause"|"resume", "room": "ROOM_ID"}
  WS   /pc?room=ROOM_ID - PC connects here and waits for commands
"""

import os
import asyncio
import json
from flask import Flask, request, jsonify
from flask_sock import Sock

app = Flask(__name__)
sock = Sock(app)

# room_id -> list of websocket connections
rooms = {}
rooms_lock = asyncio.Lock()

@app.route("/status")
def status():
    connected = {r: len(ws) for r, ws in rooms.items() if ws}
    return jsonify({"ok": True, "rooms": connected})

@app.route("/command", methods=["POST"])
def command():
    """Watch calls this to send a command to all PCs in the room."""
    data   = request.get_json(silent=True) or {}
    room   = str(data.get("room", "default"))
    action = data.get("action", "toggle")  # toggle / pause / resume

    conns  = rooms.get(room, [])
    dead   = []
    sent   = 0
    for ws in conns:
        try:
            ws.send(json.dumps({"action": action}))
            sent += 1
        except Exception:
            dead.append(ws)
    for d in dead:
        conns.remove(d)

    return jsonify({"ok": True, "sent": sent, "room": room})

@sock.route("/pc")
def pc_socket(ws):
    """PC .exe connects here and waits for commands."""
    room = request.args.get("room", "default")
    if room not in rooms:
        rooms[room] = []
    rooms[room].append(ws)
    print(f"PC connected to room '{room}' ({len(rooms[room])} total)")
    try:
        while True:
            # Keep connection alive - just wait for data (we send TO the PC, not receive)
            msg = ws.receive(timeout=30)
            if msg is None:
                break  # connection closed
    except Exception:
        pass
    finally:
        if ws in rooms.get(room, []):
            rooms[room].remove(ws)
        print(f"PC disconnected from room '{room}'")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5001))
    app.run(host="0.0.0.0", port=port)
