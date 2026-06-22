"""Lightweight Raspberry Pi MJPEG camera server for Smart Classroom AI V2.

The module is safe to import on development machines. Camera-specific imports
and hardware initialization happen only when ``main()`` starts the server.
"""

from __future__ import annotations

import json
import os
import threading
import time
import uuid
from datetime import datetime, timezone
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib import error as urllib_error
from urllib import request as urllib_request


def env_int(name: str, default: int, minimum: int, maximum: int) -> int:
    raw_value = os.getenv(name, str(default)).strip()
    try:
        value = int(raw_value)
    except ValueError:
        print(f"Invalid {name}={raw_value!r}; using {default}.")
        return default
    return max(minimum, min(maximum, value))


def env_bool(name: str, default: bool = False) -> bool:
    default_label = "1" if default else "0"
    return os.getenv(name, default_label).strip().lower() in {"1", "true", "yes", "on"}


HOST = os.getenv("SMART_CLASSROOM_LIVE_STREAM_HOST", "0.0.0.0").strip() or "0.0.0.0"
PORT = env_int("SMART_CLASSROOM_LIVE_STREAM_PORT", 8081, 1, 65535)
WIDTH = env_int("SMART_CLASSROOM_LIVE_STREAM_WIDTH", 640, 160, 3840)
HEIGHT = env_int("SMART_CLASSROOM_LIVE_STREAM_HEIGHT", 480, 120, 2160)
FPS = env_int("SMART_CLASSROOM_LIVE_STREAM_FPS", 10, 1, 30)
JPEG_QUALITY = env_int("SMART_CLASSROOM_LIVE_STREAM_JPEG_QUALITY", 70, 30, 95)
BACKEND_URL = os.getenv(
    "SMART_CLASSROOM_BACKEND_URL",
    "http://10.86.94.199:8000",
).strip().rstrip("/") or "http://10.86.94.199:8000"
SNAPSHOT_UPLOAD_ENABLED = env_bool("SMART_CLASSROOM_LIVE_SNAPSHOT_UPLOAD_ENABLED")
SNAPSHOT_UPLOAD_INTERVAL = env_int(
    "SMART_CLASSROOM_LIVE_SNAPSHOT_UPLOAD_INTERVAL",
    10,
    1,
    3600,
)
SNAPSHOT_DEVICE_NAME = os.getenv(
    "SMART_CLASSROOM_LIVE_SNAPSHOT_DEVICE_NAME",
    "Raspberry Pi 5 Live Stream",
).strip() or "Raspberry Pi 5 Live Stream"
SNAPSHOT_AUTO_ANALYZE = env_bool("SMART_CLASSROOM_LIVE_SNAPSHOT_AUTO_ANALYZE")
SNAPSHOT_SESSION_ID = os.getenv("SMART_CLASSROOM_LIVE_SNAPSHOT_SESSION_ID", "").strip()
SNAPSHOT_TIMEOUT = env_int("SMART_CLASSROOM_LIVE_SNAPSHOT_TIMEOUT", 10, 1, 120)


class CameraStream:
    """Capture and JPEG-encode frames once for all connected HTTP clients."""

    def __init__(self, width: int, height: int, fps: int, jpeg_quality: int):
        self.width = width
        self.height = height
        self.fps = fps
        self.jpeg_quality = jpeg_quality
        self.backend_name = "Not started"
        self.last_error: str | None = None
        self._camera: Any = None
        self._cv2: Any = None
        self._picamera_rgb = False
        self._frame: bytes | None = None
        self._frame_number = 0
        self._condition = threading.Condition()
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        self._open_camera()
        self._thread = threading.Thread(
            target=self._capture_loop,
            name="smart-classroom-camera",
            daemon=True,
        )
        self._thread.start()

    def _open_camera(self) -> None:
        picamera_error: Exception | None = None
        picamera = None

        try:
            import cv2  # Imported lazily so this module compiles without camera packages.
            from picamera2 import Picamera2

            picamera = Picamera2()
            configuration = picamera.create_video_configuration(
                main={"size": (self.width, self.height), "format": "RGB888"},
                controls={"FrameRate": self.fps},
                buffer_count=4,
            )
            picamera.configure(configuration)
            picamera.start()
            time.sleep(1.0)
            self._camera = picamera
            self._cv2 = cv2
            self._picamera_rgb = True
            self.backend_name = "Picamera2"
            print("Camera backend: Picamera2")
            return
        except Exception as error:  # Hardware/driver errors should also use the fallback.
            picamera_error = error
            if picamera is not None:
                try:
                    picamera.stop()
                except Exception:
                    pass
                try:
                    picamera.close()
                except Exception:
                    pass
            print(f"Picamera2 unavailable or could not start: {error}")
            print("Trying OpenCV VideoCapture(0) fallback...")

        try:
            import cv2

            camera = cv2.VideoCapture(0)
            camera.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
            camera.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
            camera.set(cv2.CAP_PROP_FPS, self.fps)
            if not camera.isOpened():
                camera.release()
                raise RuntimeError("OpenCV could not open camera device 0")

            self._camera = camera
            self._cv2 = cv2
            self._picamera_rgb = False
            self.backend_name = "OpenCV VideoCapture(0)"
            print("Camera backend: OpenCV VideoCapture(0)")
        except Exception as opencv_error:
            raise RuntimeError(
                "No camera backend could start. Install python3-picamera2 and "
                "python3-opencv on Raspberry Pi, then check that the camera is enabled. "
                f"Picamera2 error: {picamera_error}; OpenCV error: {opencv_error}"
            ) from opencv_error

    def _capture_frame(self) -> Any:
        if self._picamera_rgb:
            rgb_frame = self._camera.capture_array()
            return self._cv2.cvtColor(rgb_frame, self._cv2.COLOR_RGB2BGR)

        success, frame = self._camera.read()
        if not success or frame is None:
            raise RuntimeError("Camera returned an empty frame")
        return frame

    def _capture_loop(self) -> None:
        frame_interval = 1.0 / self.fps
        next_frame_at = time.monotonic()
        last_error_log_at = 0.0

        while not self._stop_event.is_set():
            try:
                frame = self._capture_frame()
                encoded, buffer = self._cv2.imencode(
                    ".jpg",
                    frame,
                    [self._cv2.IMWRITE_JPEG_QUALITY, self.jpeg_quality],
                )
                if not encoded:
                    raise RuntimeError("JPEG encoding failed")

                with self._condition:
                    self._frame = buffer.tobytes()
                    self._frame_number += 1
                    self.last_error = None
                    self._condition.notify_all()
            except Exception as error:
                self.last_error = str(error)
                now = time.monotonic()
                if now - last_error_log_at >= 5:
                    print(f"Camera frame error: {error}")
                    last_error_log_at = now

            next_frame_at += frame_interval
            delay = next_frame_at - time.monotonic()
            if delay > 0:
                self._stop_event.wait(delay)
            else:
                next_frame_at = time.monotonic()

    def wait_for_frame(self, previous_number: int, timeout: float = 5.0) -> tuple[bytes | None, int]:
        with self._condition:
            self._condition.wait_for(
                lambda: self._frame_number != previous_number or self._stop_event.is_set(),
                timeout=timeout,
            )
            return self._frame, self._frame_number

    def latest_jpeg(self) -> bytes | None:
        """Return the immutable latest JPEG without opening or reading the camera again."""
        with self._condition:
            return memoryview(self._frame).tobytes() if self._frame is not None else None

    def status(self) -> dict[str, Any]:
        with self._condition:
            return {
                "ok": self._thread is not None and self._thread.is_alive(),
                "service": "smart-classroom-pi-live-stream",
                "camera_backend": self.backend_name,
                "frame_available": self._frame is not None,
                "frame_number": self._frame_number,
                "width": self.width,
                "height": self.height,
                "fps": self.fps,
                "jpeg_quality": self.jpeg_quality,
                "last_error": self.last_error,
            }

    @property
    def stopped(self) -> bool:
        return self._stop_event.is_set()

    def stop(self) -> None:
        self._stop_event.set()
        with self._condition:
            self._condition.notify_all()
        if self._thread is not None:
            self._thread.join(timeout=3)

        if self._camera is None:
            return
        try:
            if self._picamera_rgb:
                self._camera.stop()
                self._camera.close()
            else:
                self._camera.release()
        except Exception as error:
            print(f"Camera shutdown warning: {error}")


class SnapshotUploader:
    """Periodically upload the camera stream's latest in-memory JPEG frame."""

    def __init__(
        self,
        camera_stream: CameraStream,
        backend_url: str,
        enabled: bool,
        interval: int,
        device_name: str,
        auto_analyze: bool,
        session_id: str,
        timeout: int,
    ):
        self.camera_stream = camera_stream
        self.backend_url = backend_url
        self.enabled = enabled
        self.interval = interval
        self.device_name = device_name
        self.auto_analyze = auto_analyze
        self.session_id = session_id
        self.timeout = timeout
        self._last_ok: bool | None = None
        self._last_at: str | None = None
        self._last_error: str | None = None
        self._status_lock = threading.Lock()
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        if not self.enabled:
            print("Snapshot upload: Disabled")
            return

        print(
            "Snapshot upload: Enabled | "
            f"Backend: {self.backend_url} | Interval: {self.interval} seconds | "
            f"Auto analyze: {'true' if self.auto_analyze else 'false'} | "
            f"Session ID: {self.session_id or 'Not set'}"
        )
        self._thread = threading.Thread(
            target=self._upload_loop,
            name="smart-classroom-snapshot-uploader",
            daemon=True,
        )
        self._thread.start()

    def _upload_loop(self) -> None:
        while not self._stop_event.wait(self.interval):
            self.upload_latest_snapshot()

    @staticmethod
    def _multipart_body(fields: dict[str, str], image_bytes: bytes) -> tuple[bytes, str]:
        boundary = f"smart-classroom-{uuid.uuid4().hex}"
        chunks: list[bytes] = []

        for name, value in fields.items():
            chunks.extend(
                [
                    f"--{boundary}\r\n".encode("ascii"),
                    f'Content-Disposition: form-data; name="{name}"\r\n\r\n'.encode("utf-8"),
                    value.encode("utf-8"),
                    b"\r\n",
                ]
            )

        chunks.extend(
            [
                f"--{boundary}\r\n".encode("ascii"),
                b'Content-Disposition: form-data; name="snapshot"; filename="live_stream_snapshot.jpg"\r\n',
                b"Content-Type: image/jpeg\r\n\r\n",
                image_bytes,
                b"\r\n",
                f"--{boundary}--\r\n".encode("ascii"),
            ]
        )
        return b"".join(chunks), boundary

    def upload_latest_snapshot(self) -> bool:
        image_bytes = self.camera_stream.latest_jpeg()
        if image_bytes is None:
            message = "No camera frame is available for snapshot upload."
            self._record_result(False, message)
            print(f"Snapshot upload failed: {message}")
            return False

        fields = {
            "device_name": self.device_name,
            "auto_analyze": "true" if self.auto_analyze else "false",
        }
        if self.session_id:
            fields["session_id"] = self.session_id

        body, boundary = self._multipart_body(fields, image_bytes)
        upload_url = f"{self.backend_url}/iot/camera/snapshot"
        request = urllib_request.Request(
            upload_url,
            data=body,
            headers={
                "Content-Type": f"multipart/form-data; boundary={boundary}",
                "Content-Length": str(len(body)),
                "User-Agent": "Smart-Classroom-Pi-Live-Stream/1.0",
            },
            method="POST",
        )

        try:
            with urllib_request.urlopen(request, timeout=self.timeout) as response:
                status_code = response.status
                response.read()
            self._record_result(True, None)
            print(f"Snapshot upload success | Backend response status: {status_code}")
            return True
        except urllib_error.HTTPError as error:
            message = f"Backend returned HTTP {error.code}: {error.reason}"
        except (urllib_error.URLError, TimeoutError, OSError) as error:
            message = str(error)
        except Exception as error:  # Keep video alive for any unexpected upload failure.
            message = f"Unexpected upload error: {error}"

        self._record_result(False, message)
        print(f"Snapshot upload failed: {message}. Live video continues.")
        return False

    def _record_result(self, ok: bool, error: str | None) -> None:
        with self._status_lock:
            self._last_ok = ok
            self._last_at = datetime.now(timezone.utc).isoformat()
            self._last_error = error

    def status(self) -> dict[str, Any]:
        with self._status_lock:
            return {
                "snapshot_upload_enabled": self.enabled,
                "snapshot_upload_interval": self.interval,
                "snapshot_upload_last_ok": self._last_ok,
                "snapshot_upload_last_at": self._last_at,
                "snapshot_upload_last_error": self._last_error,
                "backend_url": self.backend_url,
            }

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=self.timeout + 2)


class LiveStreamServer(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True

    def __init__(
        self,
        server_address: tuple[str, int],
        camera_stream: CameraStream,
        snapshot_uploader: SnapshotUploader,
    ):
        super().__init__(server_address, LiveStreamHandler)
        self.camera_stream = camera_stream
        self.snapshot_uploader = snapshot_uploader


class LiveStreamHandler(BaseHTTPRequestHandler):
    server: LiveStreamServer

    def do_GET(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler API name.
        path = self.path.split("?", 1)[0]
        if path == "/health":
            self._send_health()
            return
        if path == "/stream.mjpg":
            self._send_stream()
            return

        body = b"Smart Classroom Pi live stream. Use /health or /stream.mjpg\n"
        self.send_response(HTTPStatus.NOT_FOUND)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_health(self) -> None:
        status = self.server.camera_stream.status()
        status.update(self.server.snapshot_uploader.status())
        body = json.dumps(status).encode("utf-8")
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _send_stream(self) -> None:
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "multipart/x-mixed-replace; boundary=frame")
        self.send_header("Cache-Control", "no-store, no-cache, must-revalidate, max-age=0")
        self.send_header("Pragma", "no-cache")
        self.send_header("Connection", "close")
        self.end_headers()

        frame_number = -1
        try:
            while True:
                frame, frame_number = self.server.camera_stream.wait_for_frame(frame_number)
                if self.server.camera_stream.stopped:
                    break
                if frame is None:
                    continue
                self.wfile.write(b"--frame\r\n")
                self.wfile.write(b"Content-Type: image/jpeg\r\n")
                self.wfile.write(f"Content-Length: {len(frame)}\r\n\r\n".encode("ascii"))
                self.wfile.write(frame)
                self.wfile.write(b"\r\n")
        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
            pass

    def log_message(self, message_format: str, *args: Any) -> None:
        print(f"HTTP {self.client_address[0]} - {message_format % args}")


def main() -> int:
    camera_stream = CameraStream(WIDTH, HEIGHT, FPS, JPEG_QUALITY)
    snapshot_uploader = SnapshotUploader(
        camera_stream=camera_stream,
        backend_url=BACKEND_URL,
        enabled=SNAPSHOT_UPLOAD_ENABLED,
        interval=SNAPSHOT_UPLOAD_INTERVAL,
        device_name=SNAPSHOT_DEVICE_NAME,
        auto_analyze=SNAPSHOT_AUTO_ANALYZE,
        session_id=SNAPSHOT_SESSION_ID,
        timeout=SNAPSHOT_TIMEOUT,
    )
    try:
        camera_stream.start()
    except RuntimeError as error:
        print(f"Live stream startup failed: {error}")
        return 1

    server: LiveStreamServer | None = None
    try:
        snapshot_uploader.start()
        server = LiveStreamServer((HOST, PORT), camera_stream, snapshot_uploader)
        display_host = "<raspberry-pi-ip>" if HOST in {"0.0.0.0", "::"} else HOST
        print("Smart Classroom Raspberry Pi Live Video")
        print(f"Listening on: {HOST}:{PORT}")
        print(f"Resolution: {WIDTH}x{HEIGHT} at {FPS} FPS, JPEG quality {JPEG_QUALITY}")
        print(f"Health: http://{display_host}:{PORT}/health")
        print(f"Stream: http://{display_host}:{PORT}/stream.mjpg")
        print("Frames are kept in memory and are not saved to disk.")
        print("Press Ctrl + C to stop.\n")
        server.serve_forever(poll_interval=0.5)
    except KeyboardInterrupt:
        print("\nStopping Raspberry Pi live stream...")
    except OSError as error:
        print(f"HTTP server startup failed on {HOST}:{PORT}: {error}")
        return 1
    finally:
        if server is not None:
            server.server_close()
        snapshot_uploader.stop()
        camera_stream.stop()

    print("Raspberry Pi live stream stopped safely.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
