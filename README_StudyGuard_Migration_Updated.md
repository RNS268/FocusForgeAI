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

------------------------------------------------------------------------

# 31. Laptop Migration Checklist (StudyGuard AI + ESP32-S3)

Use this section when moving the project to another Windows laptop. The
Windows laptop runs StudyGuard AI; the ESP32-S3 can optionally act as a
companion display.

## 31.1 Copy the project and data

Copy the complete project, including:

``` text
app.py
requirements.txt
README.md
studyguard\
config\
assets\
models\
tests\
build_windows.bat
```

Also copy any custom scripts and project-specific configuration files.
Do **not** copy `.venv`, `.venv312`, or another virtual-environment
folder. Create a fresh environment on the new laptop.

To preserve previous analytics, close StudyGuard and copy its local data
directory too. The typical location documented above is:

``` text
%USERPROFILE%\StudyGuardAI\
```

Keep `.env` files and API credentials private. Never commit secrets to a
public repository.

## 31.2 Install required software

  -----------------------------------------------------------------------
  Software                            Purpose
  ----------------------------------- -----------------------------------
  Python 3.12 (64-bit)                Runs the app and is the recommended
                                      version for this working MediaPipe
                                      setup

  Visual Studio Code                  Editing and debugging

  VS Code Python and Pylance          Python interpreter selection and
  extensions                          code execution

  Git for Windows                     Optional version control

  Arduino IDE 2.x                     Only needed to modify or upload
                                      ESP32 firmware

  Espressif ESP32 board package       Only needed for ESP32 development
                                      in Arduino IDE
  -----------------------------------------------------------------------

Official downloads:

-   Python: https://www.python.org/downloads/
-   VS Code: https://code.visualstudio.com/
-   Git: https://git-scm.com/downloads/win
-   Arduino IDE: https://www.arduino.cc/en/software/
-   ESP32 Arduino setup:
    https://docs.espressif.com/projects/arduino-esp32/en/latest/installing.html

Enable **Add Python to PATH** during Python installation. Python 3.11
may also work, but Python 3.12 is the recommended migration target for
the currently working setup.

## 31.3 Create a fresh Python environment

Open Command Prompt or the VS Code terminal and change to the copied
project directory. Example:

``` cmd
cd /d C:\StudyGuard\StudyGuard-AI-main
```

Create and activate the environment:

``` cmd
py -3.12 -m venv .venv312
.venv312\Scripts\activate
python --version
python -m pip install --upgrade pip
```

Confirm that the version is Python 3.12.x. Then install the project
dependencies:

``` cmd
python -m pip install -r requirements.txt
```

Verify the important packages:

``` cmd
python -m pip show mediapipe
python -m pip show opencv-python
python -m pip show numpy
python -m pip show ultralytics
python -m pip show PySide6
```

Install missing packages only inside the activated `.venv312`
environment. Avoid accidentally installing them into a different global
Python installation.

## 31.4 Configure Visual Studio Code

1.  Open the copied project folder in VS Code.
2.  Install Microsoft's **Python** and **Pylance** extensions.
3.  Press `Ctrl+Shift+P`.
4.  Select **Python: Select Interpreter**.
5.  Choose the project's interpreter:

``` text
C:\StudyGuard\StudyGuard-AI-main\.venv312\Scripts\python.exe
```

6.  Open `app.py`.
7.  Use the Python extension's **Run Python File** command.

If VS Code uses the wrong Python installation, activate `.venv312` in
its integrated terminal and check:

``` cmd
python --version
where python
```

The first path should point to the project's
`.venv312\Scripts\python.exe`.

## 31.5 Verify models, assets, and configuration

Before launching, confirm these resources are present when their
features are required:

``` text
config\default_config.json
models\yolo11n.pt
assets\sounds\
```

Phone detection requires a compatible local YOLO model. If the model is
missing, phone detection may be disabled while other features continue
working.

If needed, install Ultralytics and download the model from the project
root:

``` cmd
python -c "from ultralytics import YOLO; YOLO('yolo11n.pt')"
mkdir models
move yolo11n.pt models\yolo11n.pt
```

Do not overwrite a custom model without making a backup.

## 31.6 Windows camera and firewall setup

1.  Allow desktop applications to access the camera in Windows Privacy &
    security settings.
2.  Close other applications that may be using the webcam.
3.  Start StudyGuard and select the correct camera.
4.  Complete calibration again for the new camera position and lighting.
5.  If using the ESP32 companion connection, allow the application
    through Windows Firewall on the trusted private network.

Camera index, resolution, FPS, and detection quality may need adjustment
for the new laptop.

## 31.7 ESP32-S3 companion display (optional)

The existing ESP32-S3 N16R8 firmware can remain installed if the
hardware, wiring, and pin assignments have not changed. A laptop
migration alone does not require re-uploading the firmware.

The current companion connection uses:

  ------------------------------------------------------------------------
  Connection                                    Port Purpose
  --------------------- ---------------------------- ---------------------
  Windows laptop TCP                          `8080` JPEG video frames
  server                                             sent to the ESP32-S3

  ESP32-S3 HTTP bridge                        `8082` Study state, timer,
                                                     and event messages
  ------------------------------------------------------------------------

The video protocol is a 4-byte big-endian JPEG payload length followed
by the JPEG bytes. The ESP32 connects as a TCP client to the Windows
laptop.

On the new laptop:

1.  Connect the laptop and ESP32-S3 to the same local network.
2.  Find the laptop's current IPv4 address using:

``` cmd
ipconfig
```

3.  Update the laptop IP in the ESP32 firmware or relevant project
    configuration. Do not assume the old laptop IP is still valid.
4.  Keep TCP port `8080` and HTTP bridge port `8082`, unless both sides
    are intentionally changed.
5.  Check Windows Firewall rules for these ports on the trusted private
    network.
6.  Start StudyGuard and confirm that its TCP stream server starts.
7.  Check the ESP32 serial output for a successful TCP connection.
8.  Test the bridge using the ESP32's current IP:

``` text
http://ESP32_IP_ADDRESS:8082/health
```

A successful health check should return a JSON response indicating that
the FocusForge ESP32 service is running. If the router assigns new IP
addresses, update the relevant configuration. Do not treat old IP
addresses as permanent.

## 31.8 First launch and migration tests

With `.venv312` activated, run:

``` cmd
python app.py
```

Test in this order:

-   [ ] Application opens without Python import errors.
-   [ ] Webcam preview works.
-   [ ] MediaPipe face and eye landmarks initialize.
-   [ ] Hand and pose tracking initialize.
-   [ ] YOLO model loads and phone detection is enabled, if required.
-   [ ] Calibration completes.
-   [ ] Study timer starts, pauses, resumes, and stops.
-   [ ] Audio alerts play.
-   [ ] SQLite history and analytics are available.
-   [ ] CSV export works.
-   [ ] ESP32-S3 connects to TCP port `8080`, if companion hardware is
    used.
-   [ ] ESP32-S3 receives state and events through port `8082`, if
    companion hardware is used.
-   [ ] TFT video, status, and timer display work.
-   [ ] Touchscreen controls respond correctly.

Run the project tests too:

``` cmd
python -m unittest discover -s tests -v
```

A successful app launch does not prove every detector works. Check live
detector statuses and test each enabled feature.

## 31.9 New-laptop completion checklist

``` text
[ ] Complete project folder copied
[ ] SQLite/data directory backed up and restored if history is needed
[ ] Python 3.12 installed
[ ] VS Code and Python extension installed
[ ] Fresh .venv312 created
[ ] requirements.txt installed in .venv312
[ ] VS Code points to .venv312
[ ] YOLO model copied/downloaded if phone detection is required
[ ] Configuration and sound assets verified
[ ] Windows camera permissions enabled
[ ] StudyGuard starts with python app.py
[ ] Calibration completed on the new laptop
[ ] All required detectors tested
[ ] Audio and analytics tested
[ ] ESP32 Wi-Fi and laptop IP updated if companion hardware is used
[ ] TCP video port 8080 tested if companion hardware is used
[ ] HTTP bridge port 8082 tested if companion hardware is used
[ ] TFT and touchscreen tested if companion hardware is used
```

**Migration note:** The laptop-specific items are Python packages, the
virtual environment, camera permissions, network addresses, and firewall
rules. ESP32 firmware and physical wiring can stay unchanged if the
board, display, touch controller, and pin assignments remain the same.
