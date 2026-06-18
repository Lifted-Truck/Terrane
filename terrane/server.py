"""Local backend server: physics loop + websocket state stream + static
frontend. Run:  python -m terrane.server  then open http://localhost:8800
"""

from __future__ import annotations

import asyncio
import functools
import http.server
import json
import os
import threading

import websockets

from .engine import Engine
from .midi_io import load_midi_events
from .params import Params

HTTP_PORT = 8800
WS_PORT = 8766  # 8765 collides with Tonality's tonality-serve.py in this dev environment
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FRONTEND = os.path.join(ROOT, "frontend")
FIXTURES = os.path.join(ROOT, "fixtures")


class Server:
    def __init__(self) -> None:
        self.engine = Engine(Params())
        self.clients: set = set()
        self.fixture_task: asyncio.Task | None = None

    async def physics_loop(self) -> None:
        loop = asyncio.get_running_loop()
        dt = 1.0 / self.engine.params.physics_hz
        next_t = loop.time()
        while True:
            self.engine.step(dt)
            next_t += dt
            now = loop.time()
            if next_t < now - 4 * dt:
                next_t = now  # drop backlog after a stall rather than sprinting through it
            await asyncio.sleep(max(0.0, next_t - now))

    async def broadcast_loop(self) -> None:
        while True:
            if self.clients:
                msg = json.dumps(
                    {
                        "type": "state",
                        "state": self.engine.snapshot(),
                        "params": self.engine.params.to_dict(),
                        "anchors": [
                            {"name": a.name, "x": a.x, "y": a.y, "depth": a.depth, "sigma": a.sigma}
                            for a in self.engine.terrain.anchors
                        ],
                        "fixtures": sorted(
                            f for f in os.listdir(FIXTURES) if f.endswith(".mid")
                        ) if os.path.isdir(FIXTURES) else [],
                    }
                )
                websockets.broadcast(self.clients, msg)
            await asyncio.sleep(1 / 30)

    async def play_fixture(self, name: str) -> None:
        path = os.path.join(FIXTURES, os.path.basename(name))
        events = load_midi_events(path)
        loop = asyncio.get_running_loop()
        start = loop.time()
        for e in events:
            await asyncio.sleep(max(0.0, start + e.t - loop.time()))
            if e.kind == "on":
                self.engine.note_on(e.midi, e.velocity)
            else:
                self.engine.note_off(e.midi)

    def _stop_playback(self) -> None:
        if self.fixture_task:
            self.fixture_task.cancel()
            self.fixture_task = None

    def dispatch(self, msg: dict) -> None:
        kind = msg.get("type")
        if kind == "note_on":
            self.engine.note_on(int(msg["midi"]), int(msg.get("velocity", 80)))
        elif kind == "note_off":
            self.engine.note_off(int(msg["midi"]))
        elif kind == "params":
            self.engine.params.update(msg.get("values", {}))
        elif kind == "anchor":
            a = self.engine.terrain.anchors[int(msg["index"])]
            for field in ("x", "y", "depth", "sigma"):
                if field in msg:
                    setattr(a, field, float(msg[field]))
        elif kind == "drop_anchor":
            self.engine.drop_anchor()
        elif kind == "reset":
            self._stop_playback()
            self.engine.reset()
        elif kind == "fixture":
            self._stop_playback()
            self.fixture_task = asyncio.get_running_loop().create_task(
                self.play_fixture(msg["name"])
            )

    async def handler(self, ws) -> None:
        self.clients.add(ws)
        try:
            async for raw in ws:
                try:
                    self.dispatch(json.loads(raw))
                except (KeyError, ValueError, IndexError):
                    pass  # malformed control message; keep streaming
        finally:
            self.clients.discard(ws)


def serve_frontend() -> None:
    handler = functools.partial(
        http.server.SimpleHTTPRequestHandler, directory=FRONTEND
    )
    httpd = http.server.ThreadingHTTPServer(("127.0.0.1", HTTP_PORT), handler)
    httpd.serve_forever()


async def main() -> None:
    server = Server()
    threading.Thread(target=serve_frontend, daemon=True).start()
    async with websockets.serve(server.handler, "127.0.0.1", WS_PORT):
        print(f"TERRANE: open http://localhost:{HTTP_PORT}  (ws on :{WS_PORT})")
        await asyncio.gather(server.physics_loop(), server.broadcast_loop())


if __name__ == "__main__":
    asyncio.run(main())
