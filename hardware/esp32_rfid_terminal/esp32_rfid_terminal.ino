/*
 * DPDP Healthcare — ESP32 RFID Physical Verification Terminal
 * Phase 2: WiFi + Backend integration + Status LEDs
 *
 * Reads an RFID card via RC522, sends the UID to the Flask backend,
 * prints the access decision to the Serial Monitor, and shows the result
 * on the GREEN (granted) / RED (denied or error) status LEDs.
 *
 * Hardware:
 *   ESP32 Dev Board + RC522 RFID reader + 1 green LED + 1 red LED
 *
 * Wiring (RC522 -> ESP32):
 *   SDA  -> GPIO 5
 *   SCK  -> GPIO 18
 *   MOSI -> GPIO 23
 *   MISO -> GPIO 19
 *   RST  -> GPIO 22
 *   GND  -> GND
 *   3.3V -> 3.3V   (NEVER 5V!)
 *   IRQ  -> (not connected)
 *
 * Wiring (Status LEDs -> ESP32). For EACH LED:
 *     ESP32 GPIO -> [220-330 ohm resistor] -> LED long leg (anode +)
 *     LED short leg (cathode -) -> GND
 *   GREEN LED -> GPIO 25   (lights on ACCESS GRANTED)
 *   RED   LED -> GPIO 26   (lights on ACCESS DENIED / errors)
 *   IMPORTANT: always use a current-limiting resistor (220-330 ohm) per LED,
 *   otherwise you can damage the LED and/or the ESP32 GPIO pin.
 *
 * Libraries required (Arduino IDE -> Manage Libraries):
 *   - MFRC522 by GithubCommunity
 *   (WiFi.h and HTTPClient.h are built into the ESP32 core)
 */

#include <SPI.h>
#include <MFRC522.h>
#include <WiFi.h>
#include <HTTPClient.h>
#include <ESPmDNS.h>

#define SS_PIN     5
#define RST_PIN    22

// Status LED pins (safe GPIOs that don't clash with the RC522 SPI pins).
#define GREEN_LED  25
#define RED_LED    26

MFRC522 rfid(SS_PIN, RST_PIN);

// ================= SETUP =================
// WIFI_SSID, WIFI_PASSWORD and BACKEND_HOST live in secrets.h (gitignored).
// First time: copy secrets.example.h to secrets.h and fill in your values.
//
// We resolve the PC by its hostname (mDNS) instead of a hard-coded IP, so the
// ESP32 keeps working even when the laptop's IP changes — flash ONCE, never
// edit again. BACKEND_HOST is your PC name WITHOUT the ".local" suffix.
#include "secrets.h"
const int   BACKEND_PORT  = 5000;
const char* BACKEND_PATH  = "/api/v1/auth/rfid-verify";
// =================================================

// Resolved at runtime from the hostname (falls back to re-resolving if it fails).
IPAddress backendIP;
bool backendResolved = false;

// Resolve BACKEND_HOST.local -> IP via mDNS. Returns true on success.
bool resolveBackend() {
  IPAddress ip = MDNS.queryHost(BACKEND_HOST);   // looks up "<host>.local"
  if (ip != IPAddress(0, 0, 0, 0)) {
    backendIP = ip;
    backendResolved = true;
    Serial.print("Backend resolved: ");
    Serial.print(BACKEND_HOST);
    Serial.print(".local -> ");
    Serial.println(backendIP);
    return true;
  }
  Serial.println("Could not resolve backend hostname (is the PC on the same WiFi?).");
  return false;
}

// ── LED helpers ──────────────────────────────────────────────────────

void bothLedsOff() {
  digitalWrite(GREEN_LED, LOW);
  digitalWrite(RED_LED, LOW);
}

/** Solid GREEN for `ms` milliseconds, then off (ACCESS GRANTED). */
void showGranted(unsigned long ms = 2000) {
  bothLedsOff();
  digitalWrite(GREEN_LED, HIGH);
  delay(ms);
  digitalWrite(GREEN_LED, LOW);
}

/** Solid RED for `ms` milliseconds, then off (ACCESS DENIED). */
void showDenied(unsigned long ms = 2000) {
  bothLedsOff();
  digitalWrite(RED_LED, HIGH);
  delay(ms);
  digitalWrite(RED_LED, LOW);
}

/** Fast RED blink to signal a connection/HTTP error (distinct from a clean deny). */
void showError(int blinks = 4) {
  bothLedsOff();
  for (int i = 0; i < blinks; i++) {
    digitalWrite(RED_LED, HIGH);
    delay(120);
    digitalWrite(RED_LED, LOW);
    delay(120);
  }
}

/** Boot self-test: blink both LEDs so you can confirm the wiring works. */
void ledSelfTest() {
  digitalWrite(GREEN_LED, HIGH);
  digitalWrite(RED_LED, HIGH);
  delay(400);
  bothLedsOff();
}

void setup() {
  Serial.begin(9600);
  delay(500);

  // Init status LEDs first so the boot self-test is visible.
  pinMode(GREEN_LED, OUTPUT);
  pinMode(RED_LED, OUTPUT);
  bothLedsOff();
  ledSelfTest();

  SPI.begin(18, 19, 23, 5);   // SCK, MISO, MOSI, SS
  rfid.PCD_Init();

  Serial.print("Connecting to WiFi");
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  int attempts = 0;
  while (WiFi.status() != WL_CONNECTED && attempts < 40) {
    delay(500);
    Serial.print(".");
    attempts++;
  }

  Serial.println("");
  if (WiFi.status() == WL_CONNECTED) {
    Serial.print("WiFi connected. ESP32 IP: ");
    Serial.println(WiFi.localIP());
    // Start mDNS and resolve the backend PC by hostname (no hard-coded IP).
    if (!MDNS.begin("esp32-rfid")) {
      Serial.println("mDNS start failed.");
    }
    resolveBackend();   // best-effort; loop() re-resolves if this misses
    // Quick green flash = ready and online.
    showGranted(300);
  } else {
    Serial.println("WiFi FAILED — check SSID/password.");
    // Red error blink = not online.
    showError(6);
  }

  Serial.println("=========================================");
  Serial.println("  RFID Terminal Ready. Tap a card...");
  Serial.println("=========================================");
}

void loop() {
  if (!rfid.PICC_IsNewCardPresent()) return;
  if (!rfid.PICC_ReadCardSerial()) return;

  // Build the UID string (hex, uppercase, no spaces)
  String cardId = "";
  for (byte i = 0; i < rfid.uid.size; i++) {
    if (rfid.uid.uidByte[i] < 0x10) cardId += "0";
    cardId += String(rfid.uid.uidByte[i], HEX);
  }
  cardId.toUpperCase();

  Serial.print("Card tapped: ");
  Serial.println(cardId);

  if (WiFi.status() == WL_CONNECTED) {
    // Make sure we have the backend IP (re-resolve if the first attempt missed
    // or the PC's IP changed since boot).
    if (!backendResolved) resolveBackend();
    if (!backendResolved) {
      Serial.println("Backend not resolved — cannot send. Is the PC on this WiFi?");
      showError();
      rfid.PICC_HaltA();
      delay(500);
      return;
    }

    // Build the URL from the resolved IP: http://<ip>:<port><path>
    String url = "http://" + backendIP.toString() + ":" + String(BACKEND_PORT) + BACKEND_PATH;

    HTTPClient http;
    http.begin(url);
    http.addHeader("Content-Type", "application/json");

    String payload = "{\"card_id\":\"" + cardId + "\"}";
    int code = http.POST(payload);
    // If the POST failed at the connection level, the PC's IP may have changed —
    // drop the cached resolution so the next tap re-resolves.
    if (code <= 0) backendResolved = false;

    if (code > 0) {
      String response = http.getString();
      Serial.print("Backend says: ");
      Serial.println(response);

      // Normalize: remove spaces so "granted": true and "granted":true both match
      String compact = response;
      compact.replace(" ", "");
      compact.replace("\n", "");
      compact.replace("\r", "");

      if (compact.indexOf("\"granted\":true") >= 0) {
        Serial.println(">>> ACCESS GRANTED <<<");
        showGranted();   // GREEN LED
      } else {
        Serial.println(">>> ACCESS DENIED <<<");
        showDenied();    // RED LED
      }
    } else {
      Serial.print("HTTP error code: ");
      Serial.println(code);
      Serial.println("(Check backend is running + firewall allows port 5000)");
      showError();       // RED blink = connection/HTTP error
    }
    http.end();
  } else {
    Serial.println("WiFi not connected!");
    showError();         // RED blink = offline
  }

  rfid.PICC_HaltA();
  delay(500);   // short debounce (LED helpers already hold the result on-screen)
}
