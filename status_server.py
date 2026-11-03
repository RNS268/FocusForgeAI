"""FocusForge AI status server for the ESP32 remote control panel.

This tiny HTTP bridge exposes the current laptop-side AI metrics to the ESP32-S3
panel over Wi-Fi. The ESP32 fetches a lightweight JSON payload from the laptop,
without needing to run the camera/AI pipeline itself.

Example:
    python status_server.py --host 0.0.0.0 --port 8081

Then the ESP32 can call:
    GET http://192.168.29.129:8081/status

Response:
    {
      "status": "ok",
      "focus_score": 88,
      "distraction_count": 4,
      "session_active": true,
      "camera_status": "connected",
      "face_status": "ready",
      "phone_status": "none",
      "timestamp": 1762160000.0
    }
"""

from __future__ import annotations

import argparse
import json
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any


class FocusForgeStatusStore:
    """Thread-safe in-memory state for the AI dashboard metrics."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._data: dict[str, Any] = {
            "status": "ok",
            "focus_score": 0,
            "distraction_count": 0,
            "session_active": False,
            "camera_status": "offline",
            "face_status": "not_ready",
            "phone_status": "unavailable",
            "timestamp": 0.0,
        }

    def update(self, payload: dict[str, Any]) -> None:
        if not isinstance(payload, dict):
            raise ValueError("Status payload must be a JSON object")
        with self._lock:
            self._data.update(payload)
            self._data["timestamp"] = time.time()

    def get_snapshot(self) -> dict[str, Any]:
        with self._lock:
            response = dict(self._data)
        response["timestamp"] = float(response.get("timestamp", time.time()))
        return response

    def reset(self) -> None:
        with self._lock:
            self._data = {
                "status": "ok",
                "focus_score": 0,
                "distraction_count": 0,
                "session_active": False,
                "camera_status": "offline",
                "face_status": "not_ready",
                "phone_status": "unavailable",
                "timestamp": time.time(),
            }


class FocusForgeStatusHandler(BaseHTTPRequestHandler):
    """Simple JSON service for the ESP32 dashboard."""

    server_version = "FocusForgeStatus/1.0"

    @property
    def store(self) -> FocusForgeStatusStore:
        return self.server.store  # type: ignore[attr-defined]

    def _send_json(self, payload: dict[str, Any], status_code: int = 200) -> None:
        body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        if self.path == "/" or self.path == "/health":
            self._send_json({"status": "ok", "service": "FocusForge AI"})
            return

        if self.path == "/status":
            self._send_json(self.store.get_snapshot())
            return

        self._send_json({"status": "not_found", "message": f"Unknown route: {self.path}"}, 404)

    def do_POST(self) -> None:
        if self.path not in {"/status", "/update"}:
            self._send_json({"status": "not_found", "message": f"Unknown route: {self.path}"}, 404)
            return

        try:
            content_length = int(self.headers.get("Content-Length", "0"))
            raw = self.rfile.read(content_length) if content_length > 0 else b"{}"
            payload = json.loads(raw.decode("utf-8"))
            if not isinstance(payload, dict):
                raise ValueError("JSON body must be an object")
            self.store.update(payload)
            self._send_json({"status": "ok", "updated": True, "data": self.store.get_snapshot()})
        except Exception as exc:  # broad catch to keep the server resilient
            self._send_json({"status": "error", "message": f"Invalid JSON payload: {exc}"}, 400)

    def do_OPTIONS(self) -> None:
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def log_message(self, format: str, *args: Any) -> None:  # noqa: A003
        # Keep the logs quiet while the server is running.
        return


class FocusForgeStatusServer(ThreadingHTTPServer):
    def __init__(self, server_address: tuple[str, int], store: FocusForgeStatusStore) -> None:
        self.store = store
        super().__init__(server_address, FocusForgeStatusHandler)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="FocusForge AI status bridge for ESP32 panel")
    parser.add_argument("--host", default="0.0.0.0", help="Bind host (default: 0.0.0.0)")
    parser.add_argument("--port", type=int, default=8081, help="HTTP port (default: 8081)")
    parser.add_argument("--focus-score", type=int, default=0, help="Initial focus score")
    parser.add_argument("--distraction-count", type=int, default=0, help="Initial distraction count")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    store = FocusForgeStatusStore()
    store.update(
        {
            "focus_score": args.focus_score,
            "distraction_count": args.distraction_count,
            "session_active": False,
            "camera_status": "offline",
            "face_status": "not_ready",
            "phone_status": "unavailable",
        }
    )

    server = FocusForgeStatusServer((args.host, args.port), store)
    print(f"FocusForge AI status server listening on http://{args.host}:{args.port}")
    print("ESP32 endpoints: GET /status   POST /status JSON")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping FocusForge AI status server...")
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
