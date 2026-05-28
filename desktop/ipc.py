"""
IPC Bridge — Lightweight UDP socket protocol for communicating between
the headless voice engine process and the Desktop UI process.

Protocol: JSON messages over localhost UDP.
Voice Engine → UI:  port 5010
UI → Voice Engine:  port 5011
"""

import json
import socket
import threading
from typing import Callable, Optional


UI_PORT = 5010       # Voice Engine sends TO this port (UI listens)
ENGINE_PORT = 5011   # UI sends TO this port (Voice Engine listens)
HOST = "127.0.0.1"
MAX_SIZE = 8192


class JsonUDPSender:
    """Fire-and-forget JSON sender over UDP."""

    def __init__(self, target_port: int):
        self._port = target_port
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    def send(self, msg_type: str, **data):
        payload = {"type": msg_type, **data}
        try:
            self._sock.sendto(
                json.dumps(payload).encode("utf-8"),
                (HOST, self._port),
            )
        except Exception:
            pass  # Non-critical — UI might not be running


class JsonUDPListener:
    """Background thread that listens for JSON messages on a UDP port."""

    def __init__(self, listen_port: int, handler: Callable[[dict], None]):
        self._port = listen_port
        self._handler = handler
        self._running = False

    def start(self):
        self._running = True
        t = threading.Thread(target=self._loop, daemon=True, name="ipc-listener")
        t.start()

    def _loop(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            sock.bind((HOST, self._port))
        except OSError:
            return  # Port already in use (another instance)
        sock.settimeout(0.5)

        while self._running:
            try:
                data, _ = sock.recvfrom(MAX_SIZE)
                msg = json.loads(data.decode("utf-8"))
                self._handler(msg)
            except socket.timeout:
                continue
            except Exception:
                continue

    def stop(self):
        self._running = False


# ── Convenience singletons for the voice engine side ──

_engine_sender: Optional[JsonUDPSender] = None


def get_engine_sender() -> JsonUDPSender:
    """Get (or create) the sender that the voice engine uses to push updates to the UI."""
    global _engine_sender
    if _engine_sender is None:
        _engine_sender = JsonUDPSender(UI_PORT)
    return _engine_sender
