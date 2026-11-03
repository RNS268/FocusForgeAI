"""FocusForge AI entry point.

Phase 2: laptop webcam plus local MediaPipe face landmarks.
Later phases will replace the OpenCV preview window with the PySide6 app.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import cv2

from core.camera_manager import CameraManager, CameraStatus
from core.face_detector import (
    FaceDetector,
    download_face_landmarker_model,
    draw_face_overlays,
)
from utils.logger import get_logger, setup_logging
from utils.performance import FpsTracker

ROOT = Path(__file__).resolve().parent
SETTINGS_PATH = ROOT / "config" / "settings.json"


def load_settings() -> dict:
    if not SETTINGS_PATH.exists():
        return {}
    with SETTINGS_PATH.open(encoding="utf-8") as handle:
        return json.load(handle)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="FocusForge AI — Phase 2 face landmarks")
    parser.add_argument("--camera", type=int, default=None, help="Camera device index (default from settings.json)")
    parser.add_argument("--list-cameras", action="store_true", help="Probe and print camera indexes, then exit")
    parser.add_argument("--download-models", action="store_true", help="Download the Face Landmarker model, then exit")
    parser.add_argument("--width", type=int, default=None)
    parser.add_argument("--height", type=int, default=None)
    return parser.parse_args()


def list_cameras() -> int:
    print("Probing camera indexes 0-5...")
    devices = CameraManager.list_devices()
    found = False
    for device in devices:
        state = "AVAILABLE" if device.available else "not found"
        print(f"  [{device.index}] {device.name} — {state}")
        found = found or device.available
    if not found:
        print("No cameras responded. Grant camera permission and close other apps using the webcam.")
        return 1
    return 0


def download_models(settings: dict) -> int:
    face_cfg = settings.get("face", {})
    model_path = ROOT / face_cfg.get("model_path", "models/face_landmarker.task")
    try:
        saved = download_face_landmarker_model(model_path)
    except Exception as exc:
        print(f"Model download failed: {exc}")
        return 1
    print(f"Face Landmarker model ready: {saved} ({saved.stat().st_size} bytes)")
    return 0


def overlay_status(frame, manager: CameraManager, detector: FaceDetector, process_fps: float) -> None:
    info = manager.info()
    result_note = detector.error_message if not detector.available else "Face Landmarker: READY"
    lines = [
        "FocusForge AI — Phase 2 Face Landmarks",
        f"Camera: {info.status.value.upper()} | {info.backend} | {info.width}x{info.height}",
        f"Capture FPS: {manager.measured_fps:.1f} | Process FPS: {process_fps:.1f}",
        result_note,
        "Keys: Q quit | R reconnect | L toggle landmarks",
    ]
    if info.error_message:
        lines.append(info.error_message)

    y = 24
    color = (0, 255, 0) if info.status == CameraStatus.CONNECTED else (0, 0, 255)
    for line in lines:
        cv2.putText(frame, line, (12, y), cv2.FONT_HERSHEY_SIMPLEX, 0.52, color, 1, cv2.LINE_AA)
        y += 20


def run_preview(manager: CameraManager, detector: FaceDetector, draw_landmarks: bool) -> int:
    logger = get_logger("main")
    window = "FocusForge AI — Face Landmarks"
    cv2.namedWindow(window, cv2.WINDOW_NORMAL)
    process_fps = FpsTracker()

    if not manager.start():
        logger.error(manager.error_message)
        print(manager.error_message)
        return 1

    if not detector.available:
        print(f"Face detection unavailable: {detector.error_message}")
        print("The webcam preview will still run. Use --download-models after installing MediaPipe.")

    print("Preview running. Press Q in the video window to quit.")
    try:
        while True:
            frame = manager.get_latest_frame()
            if frame is None:
                if manager.status == CameraStatus.ERROR:
                    print(manager.error_message)
                    return 1
                key = cv2.waitKey(30) & 0xFF
                if key in (ord("q"), ord("Q"), 27):
                    break
                continue

            display = frame.copy()
            face_result = detector.detect(display)
            if detector.available and draw_landmarks:
                draw_face_overlays(display, face_result, draw_all_landmarks=True)

            if detector.available:
                count = face_result.face_count
                if count == 0:
                    face_label = "Face: NOT DETECTED"
                    face_color = (0, 0, 255)
                elif count == 1:
                    face_label = f"Face: 1  landmarks={len(face_result.faces[0].landmarks_px)}  inf={face_result.inference_ms:.1f}ms"
                    face_color = (0, 255, 0)
                else:
                    face_label = f"Faces: {count} (multiple)  inf={face_result.inference_ms:.1f}ms"
                    face_color = (0, 165, 255)
                cv2.putText(
                    display,
                    face_label,
                    (12, display.shape[0] - 16),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.55,
                    face_color,
                    1,
                    cv2.LINE_AA,
                )
            elif detector.error_message:
                cv2.putText(
                    display,
                    "FACE DETECTOR UNAVAILABLE",
                    (12, display.shape[0] - 16),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.55,
                    (0, 0, 255),
                    1,
                    cv2.LINE_AA,
                )

            overlay_status(display, manager, detector, process_fps.tick())
            cv2.imshow(window, display)

            key = cv2.waitKey(1) & 0xFF
            if key in (ord("q"), ord("Q"), 27):
                break
            if key in (ord("r"), ord("R")):
                print("Reconnecting camera...")
                if not manager.reconnect():
                    print(manager.error_message)
            if key in (ord("l"), ord("L")):
                draw_landmarks = not draw_landmarks
                print(f"Landmark overlay: {'on' if draw_landmarks else 'off'}")
    finally:
        detector.close()
        manager.stop()
        cv2.destroyAllWindows()
        logger.info("Phase 2 preview stopped")
    return 0


def main() -> int:
    settings = load_settings()
    app_cfg = settings.get("app", {})
    camera_cfg = settings.get("camera", {})
    perf_cfg = settings.get("performance", {})
    log_cfg = settings.get("logging", {})
    face_cfg = settings.get("face", {})

    setup_logging(
        level=log_cfg.get("level", "INFO"),
        log_directory=ROOT / log_cfg.get("directory", "logs"),
    )
    logger = get_logger("main")
    logger.info("Starting %s %s", app_cfg.get("name", "FocusForge AI"), app_cfg.get("version", ""))

    args = parse_args()
    if args.list_cameras:
        return list_cameras()
    if args.download_models:
        return download_models(settings)

    manager = CameraManager(
        device_index=args.camera if args.camera is not None else int(camera_cfg.get("device_index", 0)),
        width=args.width if args.width is not None else int(camera_cfg.get("width", 640)),
        height=args.height if args.height is not None else int(camera_cfg.get("height", 480)),
        requested_fps=int(camera_cfg.get("requested_fps", 30)),
        buffer_size=int(camera_cfg.get("buffer_size", 1)),
        reconnect_attempts=int(camera_cfg.get("reconnect_attempts", 5)),
        reconnect_delay_seconds=float(camera_cfg.get("reconnect_delay_seconds", 1.5)),
        fps_smoothing=float(perf_cfg.get("fps_smoothing", 0.15)),
    )
    detector = FaceDetector(
        model_path=ROOT / face_cfg.get("model_path", "models/face_landmarker.task"),
        max_faces=int(face_cfg.get("max_faces", 2)),
        min_detection_confidence=float(face_cfg.get("min_detection_confidence", 0.5)),
        min_presence_confidence=float(face_cfg.get("min_presence_confidence", 0.5)),
        min_tracking_confidence=float(face_cfg.get("min_tracking_confidence", 0.5)),
    )
    return run_preview(manager, detector, draw_landmarks=bool(face_cfg.get("draw_landmarks", True)))


if __name__ == "__main__":
    sys.exit(main())
