# FocusForge AI

FocusForge AI is a laptop-based distraction monitoring system that uses the built-in webcam and local computer vision to detect attention quality, drowsiness, gaze drift, and phone use. The laptop remains the AI engine, while an ESP32-S3 panel acts as a remote display/control dashboard.

Current state: working local AI pipeline + live ESP32 status bridge + live panel integration.

## 1. System architecture

```text
┌───────────────────────────────┐
│ Laptop / MacBook / Windows    │
│                               │
│  Webcam + OpenCV              │
│  Face detection               │
│  Gaze / attention logic        │
│  Eye closure / drowsiness      │
│  Focus scoring                │
│  Status server (JSON)         │
│  Live video stream (JPEG TCP) │
└───────────────┬───────────────┘
                │ Wi-Fi
                │
┌───────────────▼───────────────┐
│ ESP32-S3 N16R8                 │
│  ILI9341 320x240 TFT           │
│  5 tabs: HOME LIVE LOGS TIMER SETUP │
│  Reads focus + distraction JSON │
│  Shows live video feed         │
└───────────────────────────────┘
```

This architecture keeps the laptop as the inference engine and the ESP32 as the display/control panel.

## 2. What is working now

- OpenCV webcam capture
- MediaPipe face landmark detection
- eye-state estimation
- attention / gaze classification
- distraction engine
- focus scoring
- desktop UI for laptop monitoring
- local status server for ESP32
- ESP32 TFT firmware for the remote panel
- live JSON status publishing from the laptop to the panel

## 3. Main project files

```text
FocusForge_AI/
├── main.py
├── main_ui.py
├── status_server.py
├── esp32_focusforge_panel.ino
├── requirements.txt
├── README.md
├── config/
│   └── settings.json
├── core/
│   ├── __init__.py
│   ├── attention_detector.py
│   ├── camera_manager.py
│   ├── distraction_engine.py
│   ├── eye_detector.py
│   ├── face_detector.py
│   ├── focus_scorer.py
│   ├── head_pose.py
│   ├── phone_detector.py
│   ├── status_reporter.py
│   └── __pycache__/
├── ui/
│   ├── analytics.py
│   ├── dashboard.py
│   ├── live_monitor.py
│   ├── main_window.py
│   ├── session_history.py
│   ├── settings.py
│   └── study_timer.py
├── utils/
│   ├── __init__.py
│   ├── calibration.py
│   ├── logger.py
│   ├── performance.py
│   └── __pycache__/
├── tests/
│   ├── test_camera_manager.py
│   ├── test_distraction_focus.py
│   ├── test_eye_detector.py
│   ├── test_face_detector.py
│   ├── test_phase2_attention.py
│   ├── test_phone_detector.py
│   └── test_performance.py
├── models/
│   └── face_landmarker.task
└── logs/
```

## 4. How the system works

### 4.1 Laptop side

The laptop runs the actual AI pipeline:

1. Camera captures frames
2. Face detector identifies the user
3. Attention detector evaluates gaze direction
4. Eye detector checks blink / closure / fatigue
5. Optional phone detector runs if a model exists
6. Distraction engine merges everything into one final state
7. Focus scorer calculates the current focus percentage
8. `status_server.py` exposes the results as JSON

### 4.2 ESP32 side

The ESP32 receives the JSON from the laptop and shows it on the TFT panel:

- focus score
- distractions count
- study/session state
- Wi‑Fi / camera status
- timer
- logs
- setup data

The live video feed is also received on the ESP32 through the JPEG stream from the laptop.

## 5. Required runtime flow

### Start the laptop AI + status server

From the project folder:

```bash
cd /Users/Shashank/Desktop/Distraction/FocusForge_AI
source .venv/bin/activate
python status_server.py --host 0.0.0.0 --port 8081
```

Then run the desktop app:

```bash
python main_ui.py
```

### ESP32 upload steps

1. Open `esp32_focusforge_panel.ino` in Arduino IDE
2. Set the correct Wi‑Fi SSID/password
3. Set the laptop IP to the host MacBook/Windows IP
4. Upload to the ESP32-S3 board
5. Open the serial monitor to check connection state

## 6. Required config changes when moving between machines

If you switch from Mac to Windows or another laptop, update only these values:

- ESP32 Wi‑Fi SSID/password
- laptop IP address in the ESP32 sketch
- camera index if the webcam number differs
- any absolute model file path if it was saved locally on the previous machine

The Python package list stays almost the same across macOS and Windows.

## 7. Dependencies

Install the project dependencies with Python 3.11 or 3.12:

```bash
pip install -r requirements.txt
```

The core requirements are:

```txt
numpy==1.26.4
opencv-contrib-python==4.11.0.86
pytest>=8.0.0,<9
mediapipe==0.10.21
PySide6>=6.7.0
```

Optional packages:

```txt
matplotlib>=3.8.0
ultralytics>=8.0.0
supabase>=2.0.0
python-dotenv>=1.0.0
```

## 8. Project status

### Completed

- webcam baseline
- face detection and landmarks
- eye closure analysis
- distraction state logic
- focus scoring
- desktop UI shell
- laptop-to-ESP32 status publishing
- ESP32 panel firmware draft

### Still optional / future work

- full SQLite session persistence
- advanced analytics dashboard
- export tools
- cloud sync
- calibration workflow
- production testing on final ESP32 hardware

## 9. Notes

- The laptop remains the AI brain.
- The ESP32 is a display/control panel.
- The system is designed to work locally without cloud dependence.
- If optional model packages are missing, the code should fail gracefully instead of crashing.

## 10. Privacy and local-first design

- All inference runs locally
- frames stay in memory
- no raw video is required to be uploaded to external services
- cloud sync is optional and never required for the main workflow

## 11. Quick start summary

```bash
cd FocusForge_AI
source .venv/bin/activate
python status_server.py --host 0.0.0.0 --port 8081
python main_ui.py
```

Then upload `esp32_focusforge_panel.ino` to the ESP32-S3 and connect it to the same Wi‑Fi.
