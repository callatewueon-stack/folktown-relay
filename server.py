import os, json, threading
from flask import Flask, request, jsonify, Response

app = Flask(__name__)
rooms = {}
rooms_lock = threading.Lock()

class Client:
    def __init__(self):
        self.queue = []
        self.cond  = threading.Condition()
    def push(self, msg):
        with self.cond:
            self.queue.append(msg)
            self.cond.notify_all()
    def wait(self, timeout=25):
        with self.cond:
            if self.queue:
                return self.queue.pop(0)
            self.cond.wait(timeout)
            if self.queue:
                return self.queue.pop(0)
            return None

@app.route("/")
def index():
    return "FolkTown OK"

@app.route("/status")
def status():
    with rooms_lock:
        connected = {r: len(cs) for r, cs in rooms.items() if cs}
    return jsonify({"ok": True, "rooms": connected})

@app.route("/command", methods=["POST"])
def command():
    data   = request.get_json(silent=True) or {}
    room   = str(data.get("room", "default"))
    action = str(data.get("action", "toggle"))
    with rooms_lock:
        clients = list(rooms.get(room, []))
    sent = 0
    for c in clients:
        try:
            c.push(json.dumps({"action": action}))
            sent += 1
        except Exception:
            pass
    return jsonify({"ok": True, "sent": sent, "room": room})

@app.route("/poll")
def poll():
    room   = request.args.get("room", "default")
    client = Client()
    with rooms_lock:
        rooms.setdefault(room, []).append(client)
    try:
        msg = client.wait(25)
        return Response(msg or '{"action":"ping"}', mimetype="application/json")
    finally:
        with rooms_lock:
            try:
                rooms.get(room, []).remove(client)
            except Exception:
                pass

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5001))
    app.run(host="0.0.0.0", port=port, threaded=True)
