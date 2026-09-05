/*
 * DPDP Healthcare — ESP32 RFID Physical Verification Terminal
 * Phase 2: WiFi + Backend integration
 *
 * Reads an RFID card via RC522, sends the UID to the Flask backend,
 * and prints the access decision to the Serial Monitor.
 *
 * Hardware:
 *   ESP32 Dev Board + RC522 RFID reader
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
 * Libraries required (Arduino IDE -> Manage Libraries):
 *   - MFRC522 by GithubCommunity
 *   (WiFi.h and HTTPClient.h are built into the ESP32 core)
 */

#include <SPI.h>
#include <MFRC522.h>
#include <WiFi.h>
#include <HTTPClient.h>

#define SS_PIN   5
#define RST_PIN  22

MFRC522 rfid(SS_PIN, RST_PIN);

// ================= FILL THESE IN =================
const char* WIFI_SSID     = "Redmi Note 14 Pro+ 5G";
const char* WIFI_PASSWORD = "benny2005";
const char* BACKEND_URL   = "http://10.40.139.138:5000/api/v1/auth/rfid-verify";
// =================================================

void setup() {
  Serial.begin(9600);
  delay(500);

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
  } else {
    Serial.println("WiFi FAILED — check SSID/password.");
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
    HTTPClient http;
    http.begin(BACKEND_URL);
    http.addHeader("Content-Type", "application/json");

    String payload = "{\"card_id\":\"" + cardId + "\"}";
    int code = http.POST(payload);

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
        // TODO: digitalWrite(GREEN_LED, HIGH); when resistors arrive
      } else {
        Serial.println(">>> ACCESS DENIED <<<");
        // TODO: digitalWrite(RED_LED, HIGH); when resistors arrive
      }
    } else {
      Serial.print("HTTP error code: ");
      Serial.println(code);
      Serial.println("(Check backend is running + firewall allows port 5000)");
    }
    http.end();
  } else {
    Serial.println("WiFi not connected!");
  }

  rfid.PICC_HaltA();
  delay(2000);   // debounce
}
