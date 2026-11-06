# StudyGuard AI

StudyGuard AI is a local-first Windows desktop study companion that uses
the laptop webcam to estimate focus-related behavior in real time. It
combines a PySide6 dashboard, local computer-vision detectors, session
tracking, audio alerts, analytics, calibration, settings, and SQLite
storage.

## Features

-   Live webcam preview with futuristic HUD
-   Minimal, Standard, and Developer HUD modes
-   Focus score, study timer, focused time, current/best streak
-   Phone detection with local YOLO
-   Eye/EAR drowsiness detection
-   Excessive blinking detection
-   Head-pose looking-away detection
-   Yawn/MAR detection
-   MediaPipe posture and hand tracking
-   User-presence detection with optional auto-pause/resume
-   Animated event overlays and event timeline
-   Per-event audio alerts and custom sounds
-   Pomodoro study/break mode
-   Analytics, history, and CSV export
-   First-run calibration
-   Camera Retry / Select Camera / Timer-only fallback
-   Settings for Camera, Detection, Audio, Study, and Privacy
-   HOME navigation from secondary screens
-   Local SQLite database
-   Windows packaging support

------------------------------------------------------------------------

## 1. Requirements

### Recommended environment

-   Windows 10/11
-   Python 3.11 or 3.12
-   Working laptop/USB webcam
-   8 GB RAM recommended

Python 3.11 or 3.12 is recommended for reliable MediaPipe support on
Windows. Python 3.13 may run parts of the UI/tests, but MediaPipe wheels
may not be available for every environment.

### Main Python dependencies

The project uses these major packages:

-   `PySide6` --- desktop UI
-   `opencv-python` --- webcam/image processing
-   `numpy` --- numerical operations
-   `mediapipe` --- face, eye, hand, and pose landmarks
-   `ultralytics` --- YOLO phone detection
-   `torch` --- YOLO runtime dependency

SQLite is provided by Python and does not require a separate database
server.

Use the project's `requirements.txt` as the authoritative dependency
list:

``` powershell
pip install -r requirements.txt
```

If `requirements.txt` is missing/incomplete, the core packages can be
installed with:

``` powershell
pip install PySide6 opencv-python numpy mediapipe ultralytics
```

------------------------------------------------------------------------

## 2. Project Layout

``` text
StudyGuardAI/
│
├── app.py
├── requirements.txt
├── README.md
├── build_windows.bat
│
├── config/
│   └── default_config.json
│
├── models/
│   └── yolo11n.pt
│
├── assets/
│   ├── models/
│   │   └── yolo11n.pt
│   └── sounds/
│       ├── Drowsinedd - drowsiness.mp3
│       ├── phone.mp3
│       ├── away.mp3
│       ├── bad_posture.mp3
│       ├── yawn.mp3
│       └── complete.mp3
│
├── studyguard/
│   ├── app.py
│   ├── core/
│   ├── vision/
│   ├── audio/
│   ├── analytics/
│   ├── database/
│   └── ui/
│
└── tests/
```

Important source areas:

``` text
studyguard/core/       camera, config, events, event engine, session, state
studyguard/vision/     face, eyes, phone, hands, presence, pose, yawn, posture
studyguard/audio/      audio manager
studyguard/database/   SQLite/database repository
studyguard/ui/         dashboard, camera, overlay, settings, analytics, calibration
```

------------------------------------------------------------------------

## 3. Fresh Installation on Windows

### Step 1 --- Install Python

Install Python 3.11 or 3.12 and enable **Add Python to PATH** during
installation.

Verify:

``` powershell
python --version
```

### Step 2 --- Open the project

``` powershell
cd C:\Path\To\StudyGuardAI
```

### Step 3 --- Create a virtual environment

``` powershell
python -m venv .venv
```

### Step 4 --- Activate it

``` powershell
.\.venv\Scripts\activate
```

### Step 5 --- Upgrade pip

``` powershell
python -m pip install --upgrade pip
```

### Step 6 --- Install dependencies

``` powershell
pip install -r requirements.txt
```

### Step 7 --- Install/verify MediaPipe

``` powershell
pip show mediapipe
```

If missing:

``` powershell
pip install mediapipe
```

### Step 8 --- Verify Ultralytics

``` powershell
pip show ultralytics
```

### Step 9 --- Start StudyGuard

``` powershell
python app.py
```

If your project uses the package entry point:

``` powershell
python -m studyguard.app
```

------------------------------------------------------------------------

# 4. YOLO Phone-Detection Model

Phone detection requires a local YOLO weight file. The application does
**not** automatically download YOLO weights at startup.

The preferred model is:

``` text
yolo11n.pt
```

YOLO11 official documentation:

https://docs.ultralytics.com/models/yolo11/

Official YOLO11 repository:

https://github.com/ultralytics/yolo11

Ultralytics documents `yolo11n.pt` as a pretrained YOLO11 detection
model and supports loading it through the `YOLO()` Python API.

## Supported locations in the current phone detector

``` text
models/yolo11n.pt
models/yolov8n.pt
assets/models/yolo11n.pt
```

Recommended layout:

``` text
StudyGuardAI/
└── models/
    └── yolo11n.pt
```

## Download using Ultralytics

After installing `ultralytics`, from the project root run:

``` powershell
python -c "from ultralytics import YOLO; YOLO('yolo11n.pt')"
```

Ultralytics will download the official pretrained weight if it is not
already available.

If it downloads `yolo11n.pt` into the project root, move it into the
model directory:

``` powershell
mkdir models -ErrorAction SilentlyContinue
Move-Item .\yolo11n.pt .\models\yolo11n.pt
```

Then verify:

``` text
StudyGuardAI\models\yolo11n.pt
```

### Important behavior

The phone detector checks for a compatible local model. If no model is
found:

``` text
Phone detection: disabled
Other StudyGuard features: continue working
```

The detector also uses temporal persistence so that a single-frame YOLO
false positive does not immediately become a `PHONE_DETECTED` event.

The current detector recognizes phone-related classes such as:

``` text
cell phone
mobile phone
phone
smartphone
```

------------------------------------------------------------------------

# 5. MediaPipe Models

Face/eye/hand/posture processing uses MediaPipe landmark APIs. There is
normally no separate `.pt` model that needs to be downloaded manually
for these detectors.

Install with:

``` powershell
pip install mediapipe
```

Verify:

``` powershell
pip show mediapipe
```

If MediaPipe cannot be installed/initialized, use Python 3.11 or 3.12.

------------------------------------------------------------------------

# 6. Audio Setup

Audio files are kept in:

``` text
assets\sounds\
```

Current project sounds:

``` text
Drowsiness - drowsiness.mp3
phone.mp3
away.mp3
bad_posture.mp3
yawn.mp3
complete.mp3
```

Current intended mappings:

  Event / Action     Sound
  ------------------ -------------------------------
  Drowsiness         `Drowsiness - drowsiness.mp3`
  Phone detected     `phone.mp3`
  Looking away       `away.mp3`
  Bad posture        `bad_posture.mp3`
  Yawn               `yawn.mp3`
  Session complete   `complete.mp3`

Open:

``` text
Settings > Audio
```

Audio settings include enabled/disabled state, mute, per-event sound
selection, and custom sound mappings. Event cooldowns prevent an alert
from playing repeatedly on every camera frame.

Additional supported events can be mapped from the Audio settings page,
including events such as:

``` text
DROWSINESS
PHONE_DETECTED
LOOKING_AWAY
BAD_POSTURE
YAWN
EXCESSIVE_BLINKING
USER_AWAY
USER_RETURNED
BREAK_START
BREAK_END
SESSION_START
SESSION_END
```

If a custom sound cannot be played, the audio manager can fall back to a
Windows/platform beep where supported.

For maximum multimedia compatibility, WAV is generally recommended for
newly added sounds.

------------------------------------------------------------------------

# 7. First Launch and Calibration

Run:

``` powershell
python app.py
```

On first launch, complete calibration:

1.  Select/confirm the camera.
2.  Look straight at the camera.
3.  Blink normally.
4.  Look left and right.
5.  Sit comfortably in the normal study position.
6.  Complete calibration.

If the webcam is unavailable, StudyGuard can continue in timer-only
mode.

------------------------------------------------------------------------

# 8. Camera Setup

Open:

``` text
Settings > Camera
```

Available camera controls can include:

-   Camera index
-   Resolution
-   FPS
-   Mirror camera
-   Detection quality

If the camera fails, the application provides:

``` text
Retry
Select Camera
Continue Timer-Only
```

Timer-only mode keeps the application usable but does not provide real
webcam behavioral detection.

------------------------------------------------------------------------

# 9. Detection System

## Eyes / Drowsiness

Eye Aspect Ratio (EAR) is calculated from face landmarks.

It supports:

-   Open eyes
-   Closing eyes
-   Closed eyes
-   Drowsiness
-   Excessive blinking

Drowsiness uses a sustained eye-closed condition rather than a single
frame.

## Phone

YOLO identifies phones in the camera frame. Inference is throttled
internally for performance and temporal persistence reduces false
positives.

## Looking Away

Head pose estimates:

``` text
CENTER
LEFT
RIGHT
UP
DOWN
```

A sufficiently large deviation sustained for the configured duration can
create `LOOKING_AWAY`.

## Yawn

Mouth Aspect Ratio (MAR) is used to estimate prolonged mouth opening. A
sustained threshold crossing can create `YAWN`.

## Posture

MediaPipe Pose landmarks are used to estimate shoulder alignment, head
position, lean, and a practical posture classification.

Posture classification is a heuristic and is not a medical assessment.

## Presence

Face presence determines whether the user is visible. When auto-pause is
enabled, absence can pause the study session; returning can resume it.

## Hands

MediaPipe Hands detects visible hands and exposes their landmarks to the
camera HUD. It does not determine a specific activity.

------------------------------------------------------------------------

# 10. Dashboard / HUD

The main dashboard contains:

-   Live camera preview
-   Focus score
-   Study session timer
-   Current streak
-   Today statistics
-   Live status
-   Event timeline
-   Start/Pause/Resume/Stop controls
-   Analytics
-   Settings
-   Recalibrate

The camera HUD can display:

-   Presence
-   Eyes
-   Phone state
-   Hand state
-   Head pose
-   Posture
-   Yawn/fatigue state
-   Focus
-   Session timer
-   FPS
-   Confidence
-   Camera status
-   Landmark overlays
-   Phone bounding boxes
-   Event indicators
-   Developer diagnostics

HUD modes:

``` text
MINIMAL
STANDARD
DEVELOPER
```

------------------------------------------------------------------------

# 11. Focus Score

The focus score starts from a baseline of 100 and is adjusted using
detected events and their duration.

Current event penalties:

  Event                  Penalty
  -------------------- ---------
  Phone detected             8.0
  Looking away               4.5
  Drowsiness                10.0
  Yawn                       3.0
  Bad posture                2.5
  User away                  5.0
  Excessive blinking         3.0

The score is clamped to:

``` text
0 - 100
```

------------------------------------------------------------------------

# 12. Study Sessions

A study session tracks:

-   Start time
-   End time
-   Elapsed time
-   Paused time
-   Focused time
-   Distraction events
-   Current focus streak
-   Best streak
-   Focus score

Controls:

``` text
START STUDY SESSION
PAUSE
RESUME
STOP
```

------------------------------------------------------------------------

# 13. Pomodoro Mode

Pomodoro mode is available in Study settings.

Default configuration:

``` text
Study: 25 minutes
Break: 5 minutes
```

When enabled, StudyGuard can transition between study and break states
and generate `BREAK_START` / `BREAK_END` events.

------------------------------------------------------------------------

# 14. Analytics and CSV Export

StudyGuard stores session information locally in SQLite.

Analytics can include:

-   Session duration
-   Focused duration
-   Focus score
-   Distraction count
-   Distraction categories
-   Focus streak
-   Best streak
-   Historical sessions
-   Daily statistics

CSV export is available from the analytics/history interface.

No cloud database is required.

------------------------------------------------------------------------

# 15. Local Database

The application uses SQLite under the local StudyGuard data directory.

A typical location is:

``` text
%USERPROFILE%\StudyGuardAI\
```

Local data can include:

-   Sessions
-   Events
-   Daily statistics
-   Settings
-   Calibration information

No separate database server is required.

If you want to preserve historical analytics when moving to another
computer, preserve the application's SQLite/data directory as well as
the project files.

------------------------------------------------------------------------

# 16. Configuration

Default configuration:

``` text
config/default_config.json
```

Important detection parameters currently include:

``` json
{
    "eye_ear_threshold": 0.21,
    "drowsy_seconds": 1.5,
    "blink_window_seconds": 0.5,
    "excessive_blinks_per_minute": 28,
    "yawn_mar_threshold": 0.62,
    "yawn_seconds": 1.0,
    "looking_away_seconds": 2.0,
    "head_yaw_threshold": 22.0,
    "head_pitch_threshold": 18.0,
    "phone_confidence": 0.45,
    "phone_persistence_frames": 4,
    "posture_warning_seconds": 6.0,
    "absence_seconds": 3.0
}
```

Audio, study, UI, camera, detection, and calibration settings are
handled by the configuration system. Prefer changing settings through
the application UI rather than manually editing JSON unless you know the
configuration schema.

------------------------------------------------------------------------

# 17. Keyboard Shortcuts

  Key       Action
  --------- ------------------------
  `Space`   Start / Pause / Resume
  `Esc`     Stop session
  `R`       Recalibrate
  `M`       Toggle mute
  `H`       Toggle HUD mode
  `D`       Toggle developer mode

------------------------------------------------------------------------

# 18. Navigation

The dashboard is the home screen.

Secondary pages include:

-   Analytics
-   Settings
-   Calibration
-   Session Summary

A `HOME` button is available on secondary pages so the user can return
to the dashboard without closing the application.

------------------------------------------------------------------------

# 19. Privacy

StudyGuard is designed around local processing.

By default:

-   Webcam frames are processed locally/in memory.
-   No video recording is implemented.
-   No screenshots are saved by default.
-   No microphone is required.
-   Webcam frames are not uploaded.
-   No cloud vision API is required.
-   Study data is stored locally.
-   SQLite is local.
-   CSV export is explicitly user initiated.

------------------------------------------------------------------------

# 20. Testing

Run:

``` powershell
python -m unittest discover -s tests -v
```

The tests are designed to avoid requiring a physical webcam, YOLO
weights, or live camera inference for most unit-test scenarios.

------------------------------------------------------------------------

# 21. Windows Packaging

The project includes:

``` text
build_windows.bat
```

Run from the project root:

``` powershell
.\build_windows.bat
```

Expected output is similar to:

``` text
dist/
└── StudyGuardAI/
```

When packaging, make sure these runtime resources are included:

``` text
config\
models\yolo11n.pt
assets\sounds\
```

If phone detection is required, the YOLO model must be shipped alongside
the packaged application at a path recognized by the phone detector.

------------------------------------------------------------------------

# 22. Moving StudyGuard to Another Computer

Copy the complete project, including:

``` text
studyguard\
config\
assets\
models\
requirements.txt
app.py
```

Then on the new computer:

``` powershell
cd C:\Path\To\StudyGuardAI
python -m venv .venv
.\.venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt
python app.py
```

Verify these resources were copied:

``` text
models\yolo11n.pt
assets\sounds\
```

If historical analytics are required, preserve the local SQLite/data
directory too.

------------------------------------------------------------------------

# 23. Troubleshooting

## Camera unavailable

1.  Close other applications using the webcam.
2.  Check Windows camera permissions.
3.  Open `Settings > Camera`.
4.  Try another camera index.
5.  Press `Retry`.
6.  Select another camera.
7.  Use timer-only mode if necessary.

## MediaPipe unavailable

Check:

``` powershell
python --version
pip show mediapipe
```

Use Python 3.11 or 3.12 if the current environment cannot provide
MediaPipe wheels.

## Phone detection unavailable

Check:

``` powershell
pip show ultralytics
```

and:

``` text
models\yolo11n.pt
```

No YOLO model means phone detection is disabled while the rest of the
application remains usable.

## Audio does not play

Check:

-   Windows output device
-   Windows master volume
-   StudyGuard audio enabled state
-   Mute state
-   `Settings > Audio`
-   Selected sound file exists
-   Supported audio format
-   `assets\sounds\` exists

## Slow inference

Possible causes include CPU-only YOLO inference, high camera
resolution/FPS, low lighting, or the combined vision workload.

Try reducing camera resolution/FPS or detection quality in
`Settings > Camera`.

------------------------------------------------------------------------

# 24. Clean Reinstallation

If the virtual environment becomes corrupted:

``` powershell
deactivate
```

Delete:

``` text
.venv\
```

Create it again:

``` powershell
python -m venv .venv
.\.venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Verify:

``` powershell
python --version
pip show PySide6
pip show opencv-python
pip show numpy
pip show mediapipe
pip show ultralytics
```

Then:

``` powershell
python app.py
```

------------------------------------------------------------------------

# 25. Architecture

``` text
CameraWorker
    |
    v
FramePacket
    |
    v
VisionPipeline
    |
    +-- Face / Presence
    +-- Eyes / EAR
    +-- Head Pose
    +-- Phone / YOLO
    +-- Hands / MediaPipe
    +-- Posture / MediaPipe
    +-- Yawn / MAR
    |
    v
DetectionResult
    |
    v
EventEngine
    |
    v
EventBus
    +----------+-----------+-----------+
    |          |           |           |
    v          v           v           v
Dashboard  AudioManager  SQLite     StudySession
    |                       |           |
    v                       v           v
Camera HUD              Analytics   FocusEngine
    |
    v
Event Overlay
```

------------------------------------------------------------------------

# 26. Design Notes

### Local-first processing

The vision pipeline is intended to process camera frames locally.

### Event debouncing

Detection thresholds, persistence, and cooldowns prevent noisy
frame-by-frame alerts.

### Phone persistence

YOLO phone detection uses temporal persistence to reduce single-frame
false positives.

### Camera fallback

If the webcam is unavailable, the UI can continue in timer-only mode.

### Audio fallback

If a custom audio file cannot be played, the audio manager can use a
platform beep fallback where supported.

------------------------------------------------------------------------

# 27. Known Limitations

-   MediaPipe availability depends on Python version/platform wheels.
-   Python 3.11/3.12 is recommended for full MediaPipe functionality on
    Windows.
-   Phone detection requires a compatible local YOLO model.
-   Camera placement and lighting affect detection accuracy.
-   Phone detection can produce false positives or false negatives.
-   Posture classification is a practical heuristic, not a medical
    assessment.
-   Hand detection only indicates visible hands and does not determine a
    specific activity.
-   Timer-only mode does not provide webcam behavioral detection.
-   Windows notification behavior depends on Windows tray/notification
    availability.
-   Detection thresholds may require adjustment for different cameras,
    users, and lighting.

------------------------------------------------------------------------

# 28. Quick Start

For an existing project copy:

``` powershell
cd C:\Path\To\StudyGuardAI
python -m venv .venv
.\.venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

If `models\yolo11n.pt` is not already present:

``` powershell
python -c "from ultralytics import YOLO; YOLO('yolo11n.pt')"
mkdir models -ErrorAction SilentlyContinue
Move-Item .\yolo11n.pt .\models\yolo11n.pt -ErrorAction SilentlyContinue
```

Then:

``` powershell
python app.py
```

First-run checklist:

``` text
1. Complete calibration
2. Check Settings > Camera
3. Check Settings > Audio
4. Confirm webcam preview
5. Confirm YOLO phone model if phone detection is required
6. Start a Study Session
```

------------------------------------------------------------------------

# 29. Maintainer Checklist for a New Computer

``` text
[ ] Python 3.11 or 3.12 installed
[ ] Virtual environment created
[ ] requirements.txt installed
[ ] PySide6 installed
[ ] OpenCV installed
[ ] NumPy installed
[ ] MediaPipe installed
[ ] Ultralytics installed
[ ] YOLO model copied/downloaded
[ ] assets\sounds\ copied
[ ] config\ copied
[ ] Windows webcam permissions enabled
[ ] python app.py starts successfully
[ ] calibration completed
[ ] camera detection tested
[ ] phone detection tested
[ ] audio alerts tested
[ ] Settings > Audio tested
[ ] Analytics tested
[ ] HOME navigation tested
```

------------------------------------------------------------------------

# 30. Third-Party Components

StudyGuard AI uses third-party components including PySide6/Qt, OpenCV,
NumPy, MediaPipe, Ultralytics YOLO, PyTorch, and Python's SQLite
support.

When redistributing the project or a packaged build, review and comply
with the licenses and redistribution terms of all third-party
dependencies and the YOLO model.

Ultralytics YOLO11 documentation:

https://docs.ultralytics.com/models/yolo11/

------------------------------------------------------------------------

## StudyGuard AI

``` text
LOCAL PROCESSING
FOCUS INTELLIGENCE
REAL-TIME STUDY MONITORING
```
