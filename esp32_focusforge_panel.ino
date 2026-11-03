/*
  FocusForge AI - ESP32-S3 N16R8 Control Panel
  5 tabs: HOME + LIVE + LOGS + TIMER + SETUP

  Hardware:
    ESP32-S3 N16R8
    2.8" ILI9341 320x240 TFT (landscape)
    XPT2046 touch

  Purpose:
    - Connect to Wi-Fi laptop running FocusForge AI
    - Read live laptop status from /status JSON endpoint
    - Show live camera feed from the laptop JPEG stream
    - Display focus score, distraction count, timer, logs, and setup

  Wiring is preserved from your firmware:
    TFT: SCK=12, MOSI=11, MISO=13, CS=10, DC=9, RST=14
    TOUCH: CS=15, IRQ=16

  Laptop server expected:
    http://192.168.29.129:8081/status
    JSON example:
      {
        "status":"ok",
        "focus_score":88,
        "distraction_count":4,
        "session_active":true,
        "camera_status":"connected",
        "face_status":"ready",
        "phone_status":"none",
        "timestamp":1762160000.0
      }

  Video stream expected from laptop:
    TCP protocol: 4-byte big-endian JPEG length followed by JPEG bytes
  on port 8080.
*/

#include <WiFi.h>
#include <WiFiClient.h>
#include <SPI.h>
#include <Adafruit_GFX.h>
#include <Adafruit_ILI9341.h>
#include <XPT2046_Touchscreen.h>
#include <TJpg_Decoder.h>
#include <esp_heap_caps.h>

// ===== USER CONFIG =====
static const char* WIFI_SSID = "Shashank";
static const char* WIFI_PASSWORD = "qwerty6967";
static const IPAddress SERVER_IP(192, 168, 29, 129);
static const uint16_t SERVER_PORT = 8080;
static const uint16_t STATUS_PORT = 8081;

// Preserve existing wiring
#define PIN_TFT_SCK 12
#define PIN_TFT_MOSI 11
#define PIN_TFT_MISO 13
#define PIN_TFT_CS 10
#define PIN_TFT_DC 9
#define PIN_TFT_RST 14
#define PIN_TOUCH_CS 15
#define PIN_TOUCH_IRQ 16

// Touch calibration
#define TOUCH_RAW_X_MIN 200
#define TOUCH_RAW_X_MAX 3700
#define TOUCH_RAW_Y_MIN 240
#define TOUCH_RAW_Y_MAX 3800
#define TOUCH_SWAP_XY false
#define TOUCH_INVERT_X false
#define TOUCH_INVERT_Y false

static const int16_t SW = 320;
static const int16_t SH = 240;
static const int16_t HEADER_H = 24;
static const int16_t NAV_Y = 204;
static const int16_t NAV_H = 36;
static const int16_t CONTENT_Y = 24;

static const uint16_t BG = 0xEF5D;
static const uint16_t WHITE = 0xFFFF;
static const uint16_t TEXT = 0x18E3;
static const uint16_t MUTED = 0x7BEF;
static const uint16_t BLUE = 0x239F;
static const uint16_t GREEN = 0x25E8;
static const uint16_t RED = 0xE986;
static const uint16_t AMBER = 0xFD20;
static const uint16_t BORDER = 0xCE79;
static const uint16_t NAV_IDLE = 0xDEDB;
static const uint16_t DARK = 0x2108;

enum Screen : uint8_t { HOME, LIVE, LOGS, TIMER, SETUP, SCREEN_COUNT };
const char* TAB_NAMES[SCREEN_COUNT] = {"HOME", "LIVE", "LOGS", "TIMER", "SETUP"};

Adafruit_ILI9341 tft(PIN_TFT_CS, PIN_TFT_DC, PIN_TFT_RST);
XPT2046_Touchscreen ts(PIN_TOUCH_CS);
WiFiClient cam;
Screen currentScreen = HOME;

// ---- Home / Session state ----
bool sessionActive = false;
uint32_t sessionStartMs = 0, studyAccumulatedMs = 0;
uint16_t focusSessions = 0, distractions = 0;
uint32_t lastHomePaint = 0;

// ---- Laptop status values ----
int laptopFocusScore = 0;
uint16_t laptopDistractionCount = 0;
bool laptopSessionActive = false;
bool laptopCameraConnected = false;
String laptopCameraStatus = "offline";
String laptopPhoneStatus = "unavailable";
String laptopFaceStatus = "not_ready";
bool hasLaptopStatus = false;
uint32_t lastStatusPollMs = 0;

// ---- Logs ----
static const uint8_t LOG_CAPACITY = 12;
struct LogEntry {
  uint32_t atMs;
  char message[30];
};
LogEntry logEntries[LOG_CAPACITY];
uint8_t logCount = 0, logScroll = 0;

// ---- Timer state ----
enum TimerMode : uint8_t { POMO_TIMER, CUSTOM_TIMER, STOPWATCH_TIMER };
enum PomoPhase : uint8_t { PHASE_FOCUS, PHASE_SHORT_BREAK, PHASE_LONG_BREAK };
TimerMode timerMode = POMO_TIMER;
PomoPhase pomoPhase = PHASE_FOCUS;
bool timerRunning = false;
uint32_t timerEndMs = 0;
uint32_t timerRemainingMs = 25UL * 60UL * 1000UL;
uint16_t customMinutes = 25;
uint8_t focusInCycle = 0;
bool stopwatchRunning = false;
uint32_t stopwatchStartedMs = 0, stopwatchAccumulatedMs = 0;
uint32_t lastTimerPaint = 0;

// ---- Camera receive state ----
uint8_t* jpegBuf = nullptr;
const size_t JPEG_CAP = 192 * 1024;
uint8_t hdr[4];
uint8_t hdrPos = 0; uint32_t frameLen = 0, framePos = 0;
uint32_t lastConnectAttempt = 0, lastByteMs = 0, lastFrameMs = 0;
bool frameReady = false;
uint32_t framesReceived = 0;

// ===== Utilities =====
uint32_t studySeconds() {
  uint32_t ms = studyAccumulatedMs;
  if (sessionActive) ms += millis() - sessionStartMs;
  return ms / 1000;
}

void fmtTime(uint32_t sec, char* out, size_t n) {
  snprintf(out, n, "%02lu:%02lu:%02lu", (unsigned long)(sec / 3600), (unsigned long)((sec / 60) % 60), (unsigned long)(sec % 60));
}

void addLog(const char* message) {
  if (logCount < LOG_CAPACITY) logCount++;
  for (int i = LOG_CAPACITY - 1; i > 0; i--) {
    logEntries[i] = logEntries[i - 1];
  }
  logEntries[0].atMs = millis();
  snprintf(logEntries[0].message, sizeof(logEntries[0].message), "%s", message);
  logScroll = 0;
  Serial.printf("[LOG] %s\n", message);
}

void fmtElapsed(uint32_t ms, char* out, size_t n) {
  uint32_t sec = ms / 1000;
  snprintf(out, n, "+%02lu:%02lu", (unsigned long)(sec / 3600), (unsigned long)((sec / 60) % 60));
}

void textAt(int x, int y, uint8_t size, uint16_t color, const char* s) {
  tft.setTextSize(size);
  tft.setTextColor(color);
  tft.setCursor(x, y);
  tft.print(s);
}

void centered(int cx, int y, uint8_t size, uint16_t color, const char* s) {
  int16_t x1, y1; uint16_t w, h;
  tft.setTextSize(size);
  tft.getTextBounds(s, 0, y, &x1, &y1, &w, &h);
  textAt(cx - (int)w / 2, y, size, color, s);
}

void card(int x, int y, int w, int h, const char* label, const char* value, uint16_t valueColor = TEXT) {
  tft.fillRoundRect(x, y, w, h, 7, WHITE);
  tft.drawRoundRect(x, y, w, h, 7, BORDER);
  textAt(x + 8, y + 7, 1, MUTED, label);
  textAt(x + 8, y + 25, 2, valueColor, value);
}

void button(int x, int y, int w, int h, const char* label, uint16_t fill, uint16_t fg = WHITE) {
  tft.fillRoundRect(x, y, w, h, 7, fill);
  tft.drawRoundRect(x, y, w, h, 7, fill);
  centered(x + w / 2, y + (h - 8) / 2, 1, fg, label);
}

void drawHeader(const char* title) {
  tft.fillRect(0, 0, SW, HEADER_H, DARK);
  textAt(7, 7, 1, WHITE, "FOCUSFORGE AI");
  int16_t x1, y1; uint16_t w, h;
  tft.setTextSize(1);
  tft.getTextBounds(title, 0, 0, &x1, &y1, &w, &h);
  textAt(SW - w - 7, 7, 1, 0xBDF7, title);
}

void drawNav() {
  tft.fillRect(0, NAV_Y, SW, NAV_H, NAV_IDLE);
  for (int i = 0; i < SCREEN_COUNT; i++) {
    int x = i * 64;
    uint16_t c = (i == (int)currentScreen) ? BLUE : NAV_IDLE;
    tft.fillRect(x, NAV_Y, 64, NAV_H, c);
    if (i == (int)currentScreen) {
      tft.fillRect(x + 5, NAV_Y + 3, 54, 2, WHITE);
    }
    centered(x + 32, NAV_Y + 15, 1, (i == (int)currentScreen) ? WHITE : TEXT, TAB_NAMES[i]);
  }
}

void drawPlaceholder(const char* title, const char* subtitle) {
  tft.fillRect(0, CONTENT_Y, SW, NAV_Y - CONTENT_Y, BG);
  tft.fillRoundRect(18, 65, 284, 92, 10, WHITE);
  tft.drawRoundRect(18, 65, 284, 92, 10, BORDER);
  centered(160, 91, 2, BLUE, title);
  centered(160, 120, 1, MUTED, subtitle);
  centered(160, 139, 1, MUTED, "This section will be enabled in a later build.");
}

bool cameraConnected() {
  return WiFi.status() == WL_CONNECTED && cam.connected();
}

// ===== Status parsing from laptop =====
String extractJsonString(const String& json, const char* key) {
  String needle = String("\"") + key + String("\":\"");
  int start = json.indexOf(needle);
  if (start < 0) return "";
  start += needle.length();
  int end = json.indexOf('"', start);
  if (end < 0) return "";
  return json.substring(start, end);
}

int extractJsonInt(const String& json, const char* key) {
  String needle = String("\"") + key + String("\":");
  int start = json.indexOf(needle);
  if (start < 0) return 0;
  start += needle.length();
  int end = json.indexOf(',', start);
  if (end < 0) end = json.indexOf('}', start);
  if (end < 0) return 0;
  String value = json.substring(start, end);
  value.trim();
  return value.toInt();
}

bool extractJsonBool(const String& json, const char* key) {
  String needle = String("\"") + key + String("\":");
  int start = json.indexOf(needle);
  if (start < 0) return false;
  start += needle.length();
  int end = json.indexOf(',', start);
  if (end < 0) end = json.indexOf('}', start);
  if (end < 0) return false;
  String value = json.substring(start, end);
  value.trim();
  return value.equalsIgnoreCase("true");
}

bool fetchLaptopStatus() {
  WiFiClient client;
  const uint32_t timeoutMs = 2000;

  if (!client.connect(SERVER_IP, STATUS_PORT)) {
    return false;
  }

  client.setTimeout(timeoutMs);
  client.println(F("GET /status HTTP/1.1"));
  client.print(F("Host: "));
  client.println(SERVER_IP);
  client.println(F("Connection: close"));
  client.println();

  String response = "";
  uint32_t start = millis();
  while (client.connected() || client.available()) {
    while (client.available()) {
      char c = client.read();
      response += c;
    }
    if (millis() - start > timeoutMs) break;
    delay(10);
  }

  client.stop();

  int jsonStart = response.indexOf('{');
  int jsonEnd = response.lastIndexOf('}');
  if (jsonStart < 0 || jsonEnd < 0 || jsonEnd <= jsonStart) {
    return false;
  }

  String json = response.substring(jsonStart, jsonEnd + 1);
  if (json.length() < 10) {
    return false;
  }

  laptopFocusScore = extractJsonInt(json, "focus_score");
  laptopDistractionCount = (uint16_t)extractJsonInt(json, "distraction_count");
  laptopSessionActive = extractJsonBool(json, "session_active");
  laptopCameraStatus = extractJsonString(json, "camera_status");
  if (laptopCameraStatus.length() == 0) laptopCameraStatus = "offline";
  laptopFaceStatus = extractJsonString(json, "face_status");
  if (laptopFaceStatus.length() == 0) laptopFaceStatus = "not_ready";
  laptopPhoneStatus = extractJsonString(json, "phone_status");
  if (laptopPhoneStatus.length() == 0) laptopPhoneStatus = "unavailable";
  laptopCameraConnected = (laptopCameraStatus.indexOf("connected") >= 0 || laptopCameraStatus.indexOf("online") >= 0);

  hasLaptopStatus = true;
  if (currentScreen == HOME) drawHome(false);
  if (currentScreen == SETUP) drawSetup();
  return true;
}

// ===== UI screens =====
void drawLogs() {
  tft.fillRect(0, CONTENT_Y, SW, NAV_Y - CONTENT_Y, BG);
  textAt(9, 29, 1, MUTED, "RECENT ACTIVITY (RAM ONLY)");
  button(250, 26, 62, 22, "CLEAR", RED, WHITE);

  if (logCount == 0) {
    tft.fillRoundRect(15, 75, 290, 75, 8, WHITE);
    tft.drawRoundRect(15, 75, 290, 75, 8, BORDER);
    centered(160, 98, 2, BLUE, "NO ACTIVITY YET");
    centered(160, 124, 1, MUTED, "Start a study session to create logs.");
    return;
  }

  const uint8_t visible = 6;
  for (uint8_t row = 0; row < visible; row++) {
    uint8_t idx = logScroll + row;
    if (idx >= logCount) break;
    int y = 51 + row * 23;
    tft.fillRoundRect(7, y, 306, 21, 4, WHITE);
    char elapsed[12];
    fmtElapsed(logEntries[idx].atMs, elapsed, sizeof(elapsed));
    textAt(13, y + 7, 1, BLUE, elapsed);
    textAt(76, y + 7, 1, TEXT, logEntries[idx].message);
  }

  if (logCount > visible) {
    button(8, 190, 48, 13, "OLDER", BLUE);
    button(264, 190, 48, 13, "NEWER", BLUE);
    char page[20];
    snprintf(page, sizeof(page), "%u-%u OF %u", logScroll + 1, min((int)logScroll + visible, (int)logCount), logCount);
    centered(160, 192, 1, MUTED, page);
  }
}

void drawSetup() {
  tft.fillRect(0, CONTENT_Y, SW, NAV_Y - CONTENT_Y, BG);

  const bool wifi = WiFi.status() == WL_CONNECTED;
  const bool camera = cameraConnected();

  card(7, 30, 150, 48, "WI-FI", wifi ? "CONNECTED" : "OFFLINE", wifi ? GREEN : RED);
  card(163, 30, 150, 48, "CAMERA SERVER", camera ? "CONNECTED" : "OFFLINE", camera ? GREEN : RED);

  tft.fillRoundRect(7, 84, 306, 70, 7, WHITE);
  tft.drawRoundRect(7, 84, 306, 70, 7, BORDER);
  textAt(15, 92, 1, MUTED, "DEVICE IP");
  String ip = wifi ? WiFi.localIP().toString() : String("Not assigned");
  textAt(105, 92, 1, TEXT, ip.c_str());

  textAt(15, 110, 1, MUTED, "MAC SERVER");
  char server[24];
  snprintf(server, sizeof(server), "%u.%u.%u.%u:%u", SERVER_IP[0], SERVER_IP[1], SERVER_IP[2], SERVER_IP[3], SERVER_PORT);
  textAt(105, 110, 1, TEXT, server);

  textAt(15, 128, 1, MUTED, "LAPTOP FOCUS");
  char focus[12];
  snprintf(focus, sizeof(focus), "%d%%", laptopFocusScore);
  textAt(105, 128, 1, TEXT, focus);

  button(7, 164, 306, 31, "RECONNECT WI-FI + CAMERA", BLUE, WHITE);
}

void drawHome(bool full) {
  if (full) {
    tft.fillRect(0, CONTENT_Y, SW, NAV_Y - CONTENT_Y, BG);
  }

  char study[16];
  fmtTime(studySeconds(), study, sizeof(study));
  card(6, 30, 198, 56, "TOTAL STUDY TIME", study, BLUE);

  char foc[12];
  snprintf(foc, sizeof(foc), "%d%%", laptopFocusScore > 0 ? laptopFocusScore : 0);
  card(210, 30, 104, 56, "FOCUS SCORE", foc, GREEN);

  char dis[12];
  snprintf(dis, sizeof(dis), "%u", laptopDistractionCount > 0 ? laptopDistractionCount : distractions);
  card(6, 92, 100, 48, "DISTRACTIONS", dis, RED);

  card(110, 92, 100, 48, "CAMERA", laptopCameraConnected ? "ONLINE" : "OFFLINE", laptopCameraConnected ? GREEN : RED);
  card(214, 92, 100, 48, "WI-FI", WiFi.status() == WL_CONNECTED ? "ONLINE" : "OFFLINE", WiFi.status() == WL_CONNECTED ? GREEN : RED);

  button(6, 148, 198, 48, sessionActive ? "STOP STUDY SESSION" : "START STUDY SESSION", sessionActive ? RED : GREEN);
  button(210, 148, 104, 48, "+ DISTRACTION", AMBER, DARK);

  tft.drawRoundRect(6, 148, 198, 48, 7, BORDER);
  tft.drawRoundRect(210, 148, 104, 48, 7, BORDER);
}

void drawLive() {
  tft.fillRect(0, CONTENT_Y, SW, NAV_Y - CONTENT_Y, DARK);

  if (!cameraConnected()) {
    centered(160, 82, 2, WHITE, "CAMERA OFFLINE");
    centered(160, 111, 1, 0xBDF7, WiFi.status() == WL_CONNECTED ? "Waiting for MacBook stream" : "Connecting to Wi-Fi...");
    centered(160, 132, 1, 0xBDF7, "Start the Python webcam server on your Mac");
  } else if (millis() - lastFrameMs > 2500) {
    centered(160, 82, 2, WHITE, "CONNECTED");
    centered(160, 111, 1, 0xBDF7, "Waiting for first video frame...");
  }
}

uint32_t activeTimerRemaining(uint32_t now) {
  if (!timerRunning) return timerRemainingMs;
  return (int32_t)(timerEndMs - now) > 0 ? timerEndMs - now : 0;
}

uint32_t stopwatchElapsed(uint32_t now) {
  return stopwatchAccumulatedMs + (stopwatchRunning ? now - stopwatchStartedMs : 0);
}

void drawTimerClock() {
  char tm[16];
  if (timerMode == POMO_TIMER) {
    tft.fillRect(65, 101, 190, 34, BG);
    uint32_t rem = activeTimerRemaining(millis());
    fmtTime((rem + 999) / 1000, tm, sizeof(tm));
    centered(160, 108, 3, BLUE, tm);
  } else if (timerMode == CUSTOM_TIMER) {
    tft.fillRect(65, 84, 190, 43, BG);
    uint32_t rem = activeTimerRemaining(millis());
    fmtTime((rem + 999) / 1000, tm, sizeof(tm));
    centered(160, 91, 3, BLUE, tm);
  } else {
    tft.fillRect(65, 98, 190, 43, BG);
    fmtTime(stopwatchElapsed(millis()) / 1000, tm, sizeof(tm));
    centered(160, 105, 3, BLUE, tm);
  }
}

void drawTimer() {
  tft.fillRect(0, CONTENT_Y, SW, NAV_Y - CONTENT_Y, BG);

  button(6, 29, 99, 23, timerMode == POMO_TIMER ? "POMODORO" : "POMODORO", timerMode == POMO_TIMER ? BLUE : WHITE, timerMode == POMO_TIMER ? WHITE : TEXT);
  button(110, 29, 99, 23, "CUSTOM", timerMode == CUSTOM_TIMER ? BLUE : WHITE, timerMode == CUSTOM_TIMER ? WHITE : TEXT);
  button(214, 29, 100, 23, "STOPWATCH", timerMode == STOPWATCH_TIMER ? BLUE : WHITE, timerMode == STOPWATCH_TIMER ? WHITE : TEXT);
  tft.drawRoundRect(6, 29, 99, 23, 6, BORDER);
  tft.drawRoundRect(110, 29, 99, 23, 6, BORDER);
  tft.drawRoundRect(214, 29, 100, 23, 6, BORDER);

  if (timerMode == POMO_TIMER) {
    const char* phaseName = pomoPhase == PHASE_FOCUS ? "FOCUS SESSION" : (pomoPhase == PHASE_SHORT_BREAK ? "SHORT BREAK" : "LONG BREAK");
    centered(160, 59, 1, MUTED, phaseName);
    button(12, 76, 94, 22, "FOCUS 25", pomoPhase == PHASE_FOCUS ? BLUE : WHITE, pomoPhase == PHASE_FOCUS ? WHITE : TEXT);
    button(113, 76, 94, 22, "SHORT 5", pomoPhase == PHASE_SHORT_BREAK ? BLUE : WHITE, pomoPhase == PHASE_SHORT_BREAK ? WHITE : TEXT);
    button(214, 76, 94, 22, "LONG 15", pomoPhase == PHASE_LONG_BREAK ? BLUE : WHITE, pomoPhase == PHASE_LONG_BREAK ? WHITE : TEXT);
    drawTimerClock();
    char cycle[30];
    snprintf(cycle, sizeof(cycle), "FOCUS SESSIONS IN CYCLE: %u/4", focusInCycle);
    centered(160, 137, 1, MUTED, cycle);
  } else if (timerMode == CUSTOM_TIMER) {
    centered(160, 61, 1, MUTED, "CUSTOM COUNTDOWN");
    drawTimerClock();
    button(42, 132, 48, 27, "- 5", AMBER, DARK);
    char mins[20];
    snprintf(mins, sizeof(mins), "%u MIN", customMinutes);
    centered(160, 141, 1, TEXT, mins);
    button(230, 132, 48, 27, "+ 5", AMBER, DARK);
    centered(160, 169, 1, MUTED, "Adjust in 5-minute steps");
  } else {
    centered(160, 66, 1, MUTED, "STOPWATCH");
    drawTimerClock();
    centered(160, 145, 1, MUTED, stopwatchRunning ? "STOPWATCH RUNNING" : "STOPWATCH PAUSED");
  }

  button(8, 174, 148, 25, (timerMode == STOPWATCH_TIMER ? stopwatchRunning : timerRunning) ? "PAUSE" : "START", GREEN, WHITE);
  button(164, 174, 148, 25, "RESET", RED, WHITE);
}

void drawCurrentScreen() {
  drawHeader(TAB_NAMES[currentScreen]);
  switch (currentScreen) {
    case HOME: drawHome(true); break;
    case LIVE: drawLive(); break;
    case LOGS: drawLogs(); break;
    case TIMER: drawTimer(); break;
    case SETUP: drawSetup(); break;
  }
  drawNav();
}

// ===== JPEG callback / live camera drawing =====
bool jpegOutput(int16_t x, int16_t y, uint16_t w, uint16_t h, uint16_t* bitmap) {
  int16_t ax = x, ay = y + CONTENT_Y;
  if (ay >= NAV_Y || ax >= SW || ax + (int)w <= 0 || ay + (int)h <= CONTENT_Y) return true;

  int16_t sx = max((int16_t)0, ax), sy = max((int16_t)CONTENT_Y, ay);
  int16_t ex = min((int16_t)SW, (int16_t)(ax + w)), ey = min((int16_t)NAV_Y, (int16_t)(ay + h));
  if (ex <= sx || ey <= sy) return true;

  uint16_t* src = bitmap + (sy - ay) * w + (sx - ax);
  tft.startWrite();
  for (int16_t row = sy; row < ey; row++) {
    tft.setAddrWindow(sx, row, ex - sx, 1);
    tft.writePixels(src, (uint32_t)(ex - sx), true);
    src += w;
  }
  tft.endWrite();
  return true;
}

void resetFrameParser() {
  hdrPos = 0;
  frameLen = 0;
  framePos = 0;
  frameReady = false;
}

// ===== Wi-Fi and camera connection =====
void wifiTick() {
  static uint32_t lastAttempt = 0;
  if (WiFi.status() == WL_CONNECTED) return;
  if (millis() - lastAttempt < 12000) return;
  lastAttempt = millis();
  Serial.println("[WIFI] Starting/retrying Wi-Fi");
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
}

void cameraConnectTick(uint32_t now) {
  if (WiFi.status() != WL_CONNECTED) {
    if (cam.connected()) cam.stop();
    return;
  }
  if (cam.connected()) return;
  if (now - lastConnectAttempt < 3000) return;

  lastConnectAttempt = now;
  cam.stop();
  Serial.printf("[CAM] Connecting to %s:%u\n", SERVER_IP.toString().c_str(), SERVER_PORT);
  if (cam.connect(SERVER_IP, SERVER_PORT, 1200)) {
    Serial.println("[CAM] TCP connected");
    lastByteMs = now;
  } else {
    Serial.println("[CAM] TCP connection failed; retrying");
  }
  resetFrameParser();
}

void cameraReceiveTick(uint32_t now) {
  if (!cam.connected()) return;

  size_t budget = 8192;
  while (budget && cam.available()) {
    if (hdrPos < 4) {
      int v = cam.read();
      if (v < 0) break;
      hdr[hdrPos++] = (uint8_t)v;
      budget--;
      lastByteMs = now;
      if (hdrPos == 4) {
        frameLen = ((uint32_t)hdr[0] << 24) | ((uint32_t)hdr[1] << 16) | ((uint32_t)hdr[2] << 8) | hdr[3];
        if (frameLen < 64 || frameLen > JPEG_CAP) {
          Serial.printf("[CAM] Invalid JPEG length: %lu\n", (unsigned long)frameLen);
          cam.stop();
          resetFrameParser();
          return;
        }
        framePos = 0;
      }
    } else {
      size_t want = min((size_t)(frameLen - framePos), min(budget, (size_t)cam.available()));
      int got = cam.read(jpegBuf + framePos, want);
      if (got <= 0) break;
      framePos += (uint32_t)got;
      budget -= (size_t)got;
      lastByteMs = now;
      if (framePos == frameLen) {
        frameReady = true;
        framesReceived++;
        lastFrameMs = now;
        if (currentScreen == LIVE) {
          TJpgDec.drawJpg(0, 0, jpegBuf, frameLen);
        }
        frameReady = false;
        hdrPos = 0;
        frameLen = 0;
        framePos = 0;
      }
    }
  }

  if (now - lastByteMs > 10000) {
    Serial.println("[CAM] Stream timeout; reconnecting");
    cam.stop();
    resetFrameParser();
  }
}

// ===== Timer logic =====
void selectPomoPhase(PomoPhase phase) {
  timerRunning = false;
  pomoPhase = phase;
  timerRemainingMs = (phase == PHASE_FOCUS ? 25UL : (phase == PHASE_SHORT_BREAK ? 5UL : 15UL)) * 60UL * 1000UL;
  drawTimer();
}

void timerFinish() {
  timerRunning = false;
  timerRemainingMs = 0;

  if (timerMode == CUSTOM_TIMER) {
    addLog("Custom timer completed");
    if (currentScreen == TIMER) drawTimer();
    return;
  }

  if (pomoPhase == PHASE_FOCUS) {
    focusSessions++; focusInCycle++;
    addLog("Pomodoro focus completed");
    if (focusInCycle >= 4) {
      selectPomoPhase(PHASE_LONG_BREAK);
      addLog("Long break ready");
    } else {
      selectPomoPhase(PHASE_SHORT_BREAK);
      addLog("Short break ready");
    }
  } else {
    addLog(pomoPhase == PHASE_LONG_BREAK ? "Long break completed" : "Short break completed");
    if (pomoPhase == PHASE_LONG_BREAK) focusInCycle = 0;
    selectPomoPhase(PHASE_FOCUS);
  }

  if (currentScreen == TIMER) drawTimer();
  if (currentScreen == HOME) drawHome(false);
}

void timerTick(uint32_t now) {
  if (timerRunning && (int32_t)(timerEndMs - now) <= 0) timerFinish();
  if (currentScreen == TIMER && now - lastTimerPaint >= 1000) {
    lastTimerPaint = now;
    drawTimerClock();
  }
}

void handleTimerTouch(int x, int y) {
  if (y >= 29 && y <= 54) {
    if (timerRunning) {
      timerRemainingMs = activeTimerRemaining(millis());
      timerRunning = false;
    }
    if (x < 107) timerMode = POMO_TIMER;
    else if (x < 211) timerMode = CUSTOM_TIMER;
    else timerMode = STOPWATCH_TIMER;
    drawTimer();
    return;
  }

  if (timerMode == POMO_TIMER && y >= 73 && y <= 101) {
    if (x < 109) selectPomoPhase(PHASE_FOCUS);
    else if (x < 211) selectPomoPhase(PHASE_SHORT_BREAK);
    else selectPomoPhase(PHASE_LONG_BREAK);
    return;
  }

  if (timerMode == CUSTOM_TIMER && y >= 128 && y <= 163) {
    if (timerRunning) return;
    if (x < 105) customMinutes = (customMinutes > 5) ? customMinutes - 5 : 5;
    else if (x > 215) customMinutes = (customMinutes < 180) ? customMinutes + 5 : 180;
    timerRemainingMs = (uint32_t)customMinutes * 60UL * 1000UL;
    drawTimer();
    return;
  }

  if (y >= 171 && y <= 202) {
    if (x < 160) {
      if (timerMode == STOPWATCH_TIMER) {
        if (stopwatchRunning) {
          stopwatchAccumulatedMs += millis() - stopwatchStartedMs;
          stopwatchRunning = false;
        } else {
          stopwatchStartedMs = millis();
          stopwatchRunning = true;
        }
      } else {
        if (timerRunning) {
          timerRemainingMs = activeTimerRemaining(millis());
          timerRunning = false;
        } else {
          if (timerRemainingMs == 0) {
            timerRemainingMs = (timerMode == POMO_TIMER ?
                               (pomoPhase == PHASE_FOCUS ? 25UL : (pomoPhase == PHASE_SHORT_BREAK ? 5UL : 15UL)) * 60UL * 1000UL :
                               (uint32_t)customMinutes * 60UL * 1000UL);
          }
          timerEndMs = millis() + timerRemainingMs;
          timerRunning = true;
          if (timerMode == POMO_TIMER && pomoPhase == PHASE_FOCUS) addLog("Pomodoro focus started");
          else if (timerMode == POMO_TIMER) addLog("Pomodoro break started");
          else addLog("Custom timer started");
        }
      }
    } else {
      if (timerMode == STOPWATCH_TIMER) {
        stopwatchRunning = false;
        stopwatchAccumulatedMs = 0;
        stopwatchStartedMs = 0;
      } else {
        timerRunning = false;
        timerRemainingMs = (timerMode == POMO_TIMER ?
                           (pomoPhase == PHASE_FOCUS ? 25UL : (pomoPhase == PHASE_SHORT_BREAK ? 5UL : 15UL)) * 60UL * 1000UL :
                           (uint32_t)customMinutes * 60UL * 1000UL);
      }
      addLog("Timer reset");
    }
    drawTimer();
  }
}

// ===== Touch handling =====
void touchTick() {
  static bool wasDown = false;
  static uint32_t lastTap = 0;

  if (!ts.touched()) {
    wasDown = false;
    return;
  }
  if (wasDown || millis() - lastTap < 180) return;

  TS_Point p = ts.getPoint();
  wasDown = true;
  lastTap = millis();

  int32_t rx = p.x, ry = p.y;
  if (TOUCH_SWAP_XY) {
    int32_t t = rx; rx = ry; ry = t;
  }
  int32_t x = map(rx, TOUCH_RAW_X_MIN, TOUCH_RAW_X_MAX, 0, SW - 1);
  int32_t y = map(ry, TOUCH_RAW_Y_MIN, TOUCH_RAW_Y_MAX, 0, SH - 1);
  x = constrain(x, 0, SW - 1);
  y = constrain(y, 0, SH - 1);
  if (TOUCH_INVERT_X) x = SW - 1 - x;
  if (TOUCH_INVERT_Y) y = SH - 1 - y;

  Serial.printf("[TOUCH] x=%ld y=%ld\n", (long)x, (long)y);

  if (y >= NAV_Y) {
    Screen next = (Screen)constrain((int)x / 64, 0, 4);
    if (next != currentScreen) {
      currentScreen = next;
      logScroll = 0;
      drawCurrentScreen();
    }
  } else if (currentScreen == HOME && y >= 148 && y < 200) {
    if (x < 205) {
      if (!sessionActive) {
        sessionActive = true;
        sessionStartMs = millis();
        addLog("Study session started");
      } else {
        studyAccumulatedMs += millis() - sessionStartMs;
        sessionActive = false;
        focusSessions++;
        addLog("Study session completed");
      }
      drawHome(false);
    } else {
      distractions++;
      addLog("Distraction recorded");
      drawHome(false);
    }
  } else if (currentScreen == LOGS) {
    if (y >= 24 && y < 50 && x >= 245) {
      logCount = 0;
      logScroll = 0;
      drawLogs();
    } else if (y >= 185 && logCount > 6) {
      if (x < 80 && logScroll + 6 < logCount) logScroll++;
      else if (x > 240 && logScroll > 0) logScroll--;
      drawLogs();
    }
  } else if (currentScreen == TIMER) {
    handleTimerTouch(x, y);
  } else if (currentScreen == SETUP && y >= 160 && y < 200) {
    cam.stop();
    resetFrameParser();
    WiFi.disconnect();
    WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
    addLog("Manual reconnect requested");
    drawSetup();
  }
}

// ===== Setup / loop =====
void setup() {
  Serial.begin(921600);
  delay(250);
  Serial.println("\n[BOOT] FocusForge AI Stage 3");

  pinMode(PIN_TFT_CS, OUTPUT);
  digitalWrite(PIN_TFT_CS, HIGH);
  pinMode(PIN_TOUCH_CS, OUTPUT);
  digitalWrite(PIN_TOUCH_CS, HIGH);
  pinMode(PIN_TOUCH_IRQ, INPUT_PULLUP);

  SPI.begin(PIN_TFT_SCK, PIN_TFT_MISO, PIN_TFT_MOSI, -1);
  tft.begin(40000000);
  tft.setRotation(3);
  tft.setTextWrap(false);
  tft.fillScreen(BG);

  ts.begin();
  ts.setRotation(1);

  TJpgDec.setJpgScale(1);
  TJpgDec.setSwapBytes(false);
  TJpgDec.setCallback(jpegOutput);

  jpegBuf = (uint8_t*)heap_caps_malloc(JPEG_CAP, MALLOC_CAP_SPIRAM | MALLOC_CAP_8BIT);
  if (!jpegBuf) jpegBuf = (uint8_t*)malloc(JPEG_CAP);
  Serial.printf("[MEM] JPEG buffer: %s\n", jpegBuf ? "allocated" : "FAILED");

  WiFi.mode(WIFI_STA);
  WiFi.persistent(false);
  WiFi.setSleep(false);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);

  drawCurrentScreen();
  addLog("Device started");

  Serial.println("[BOOT] Ready. Tabs: HOME LIVE LOGS TIMER SETUP");
}

void loop() {
  uint32_t now = millis();

  if (now - lastStatusPollMs > 1500) {
    lastStatusPollMs = now;
    fetchLaptopStatus();
  }

  wifiTick();
  cameraConnectTick(now);
  cameraReceiveTick(now);
  touchTick();
  timerTick(now);

  if (currentScreen == HOME && now - lastHomePaint >= 1000) {
    lastHomePaint = now;
    drawHome(false);
  }

  delay(1);
}
