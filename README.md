# FocusForge AI

Laptop-only study monitoring application. Core attention detection runs locally on the built-in webcam. No microcontrollers, external cameras, or required internet connection.

Current milestone: **Phase 2 — face detection and facial landmarks.**

## 1. Final architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     PySide6 Desktop UI                       │
│  Dashboard | Live Monitor | Analytics | Timer | History | Settings │
└───────────────────────────┬─────────────────────────────────┘
                            │ signals / queued frames
┌───────────────────────────▼─────────────────────────────────┐
│                    Session / Focus layer                     │
│  SessionManager  FocusScorer  DistractionEngine  StudyTimer  │
└───────┬───────────────────────────┬─────────────────────────┘
        │                           │
┌───────▼────────┐         ┌────────▼────────┐
│ SQLite local DB │         │ Optional Supabase│
│ sessions/events │         │ aggregate sync   │
└────────────────┘         └─────────────────┘
                            ▲
┌───────────────────────────┴─────────────────────────────────┐
│                     Detection pipeline                       │
│  CameraManager → Face → Head pose / gaze → Eyes → Phone      │
│  (thread)        MediaPipe     landmarks        EAR   YOLO?  │
└─────────────────────────────────────────────────────────────┘
```

Design rules:

- Webcam frames stay in memory. Video is not recorded unless a future setting explicitly enables it (default off).
- Inference and camera capture run off the UI thread.
- Cloud is an adapter. Missing credentials or network never blocks local use.
- Phone detection is unavailable until a local model is present. The app will not invent detections.
- Gaze from MediaPipe landmarks is **calibrated head-pose / approximate gaze**, not clinical eye tracking.

## 2. Technology choices

| Choice | Why |
| --- | --- |
| Python 3.11 / 3.12 | Supported by OpenCV, MediaPipe, and PySide6. Do not use 3.13+ until MediaPipe wheels exist. |
| OpenCV | Webcam I/O, drawing, resize. AVFoundation on macOS, DirectShow on Windows. |
| MediaPipe Face Landmarker (Phase 2) | Local face mesh / blendshapes without a GPU server. |
| NumPy | EAR, pose math, smoothing buffers. |
| PySide6 (Phase 9) | Native desktop UI on macOS and Windows. |
| SQLite (Phase 8) | Local sessions with no server. |
| Matplotlib (Phase 10) | Analytics charts inside the desktop app. |
| Optional YOLO | Phone class only if a local model file is installed. |
| Optional Supabase | Env-based aggregate sync. Core app works offline. |

## 3. Project folder structure

Created now (Phases 1–2):

```
FocusForge_AI/
    main.py
    requirements.txt
    README.md
    .env.example
    .gitignore
    pytest.ini
    config/settings.json
    models/face_landmarker.task   # downloaded locally; required for landmarks
    core/__init__.py
    core/camera_manager.py
    core/face_detector.py
    utils/__init__.py
    utils/logger.py
    utils/performance.py
    tests/test_camera_manager.py
    tests/test_performance.py
    tests/test_face_detector.py
```

Planned (not created yet — later phases, no empty stubs):

```
    core/attention_detector.py
    core/head_pose.py
    core/eye_detector.py
    core/phone_detector.py
    core/distraction_engine.py
    core/focus_scorer.py
    core/session_manager.py
    database/database.py
    database/models.py
    ui/main_window.py
    ui/dashboard.py
    ui/live_monitor.py
    ui/analytics.py
    ui/study_timer.py
    ui/session_history.py
    ui/settings.py
    cloud/supabase_client.py
    utils/calibration.py
    tests/test_attention.py
    tests/test_focus_scorer.py
    tests/test_database.py
```

## 4. Development roadmap

| Phase | Scope | Status |
| --- | --- | --- |
| 1 | Venv, OpenCV webcam, FPS, camera errors, reconnect | Done |
| 2 | MediaPipe face + landmarks | **This milestone** |
| 3 | Head pose and approximate gaze | Waiting |
| 4 | EAR, blink vs prolonged closure, drowsiness | Waiting |
| 5 | Optional local phone detector | Waiting |
| 6 | Distraction matrix + temporal smoothing | Waiting |
| 7 | Focus scoring + session manager | Waiting |
| 8 | SQLite schema | Waiting |
| 9 | PySide6 application shell and pages | Waiting |
| 10 | Analytics + CSV export | Waiting |
| 11 | Optional Supabase adapter | Waiting |
| 12 | Performance pass and end-to-end tests | Waiting |

Each phase ships complete, runnable code. Later phases start only after you confirm the previous one.

## 5. Dependencies and installation

Use **Python 3.11 or 3.12**. This machine has `python3.12`. The default `python3` may be 3.14 and is not supported.

### macOS

```bash
cd /Users/Shashank/Desktop/Distraction/FocusForge_AI
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
python main.py --download-models
```

Grant camera access: **System Settings → Privacy & Security → Camera** → allow Terminal, iTerm, Python, or your IDE.

If macOS blocks the first camera open, run the preview once, then approve the prompt and run it again.

### Windows

```bat
cd FocusForge_AI
py -3.12 -m venv .venv
.venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt
python main.py --download-models
```

Allow camera access in **Settings → Privacy → Camera**. Close Skype, Teams, Zoom, or the Windows Camera app if the device is busy.

## 6. Phase 2 commands

From `FocusForge_AI` with the venv active:

```bash
# Unit tests (no webcam required)
python -m pytest -q

# List cameras
python main.py --list-cameras

# Download the local Face Landmarker model (once; needs internet this step only)
python main.py --download-models

# Live preview with landmarks
python main.py

# Other camera index or resolution
python main.py --camera 1 --width 640 --height 480
```

Keys in the preview window: `Q` quit, `R` reconnect, `L` toggle landmark overlay.

## 7. Expected Phase 2 output

- `--download-models` writes `models/face_landmarker.task` (a few MB).
- `python main.py` opens `FocusForge AI — Face Landmarks`.
- Overlay: camera CONNECTED, **capture FPS** and **process FPS** (measured, not a constant).
- One face: yellow mesh, orange box, `Face: 1 landmarks=478`.
- Leave the frame: `Face: NOT DETECTED`.
- A second person: `Faces: 2 (multiple)`.
- Missing model or MediaPipe: webcam still runs, overlay says `FACE DETECTOR UNAVAILABLE`.
- No video files are written.

## 8. Expected Phase 1 output (still valid)

- `--list-cameras` prints at least `Camera 0` as AVAILABLE on a laptop with a working webcam.
- Camera backend is `AVFOUNDATION` on Mac or `DSHOW` on Windows.
- Quit with Q releases the camera.

## 8. Troubleshooting

| Symptom | What to do |
| --- | --- |
| `Unable to open camera index 0` | Grant OS camera permission; quit other apps using the webcam; try `--camera 1`. |
| Black frame / no frames | Unplug virtual cameras if any; reboot if the driver is stuck; confirm built-in camera in Photo Booth / Windows Camera. |
| `ModuleNotFoundError: cv2` | Activate `.venv` and `pip install -r requirements.txt`. |
| Wrong Python | `python --version` must be 3.11.x or 3.12.x. Recreate the venv with `python3.12` or `py -3.12`. |
| Preview window does not appear | You need a desktop session. SSH/headless machines cannot show `cv2.imshow`. |
| Low FPS | Capture stays at 640×480. Landmark overlay can be toggled with `L`. |
| `FACE DETECTOR UNAVAILABLE` | `pip install -r requirements.txt` then `python main.py --download-models`. |
| `ModuleNotFoundError: mediapipe` | Activate `.venv` and reinstall requirements. MediaPipe needs Python 3.11 or 3.12. |
| Model download SSL/network error | Retry when online. Core webcam still works offline after the model is saved. |

## Privacy

Phases 1–2 process frames in RAM only. No video file is written. Logging does not include images. The Face Landmarker model runs locally after download.
