#include "esp_camera.h"
#include <WiFi.h>

// — Wi-Fi credentials —
const char* ssid       = "Sujan1234";
const char* password   = "Sujan12345#";

// — Flask server info —
const char* serverIP   = "192.168.0.106";
const uint16_t serverPort = 5000;

// — LDR digital input pin ——
const int LDR_PIN      = 13;  // D0 = intact (LOW), D1 = broken (HIGH)

// — HTTP multipart boundary —
const String boundary  = "----ESP32CAMBoundary";
const String CRLF      = "\r\n";

// — AI-Thinker camera pins —
#define PWDN_GPIO_NUM     32
#define RESET_GPIO_NUM    -1
#define XCLK_GPIO_NUM      0
#define SIOD_GPIO_NUM     26
#define SIOC_GPIO_NUM     27
#define Y9_GPIO_NUM       35
#define Y8_GPIO_NUM       34
#define Y7_GPIO_NUM       39
#define Y6_GPIO_NUM       36
#define Y5_GPIO_NUM       21
#define Y4_GPIO_NUM       19
#define Y3_GPIO_NUM       18
#define Y2_GPIO_NUM        5
#define VSYNC_GPIO_NUM    25
#define HREF_GPIO_NUM     23
#define PCLK_GPIO_NUM     22

void setup() {
  Serial.begin(115200);
  delay(1000);

  pinMode(LDR_PIN, INPUT);

  // Camera config
  camera_config_t config;
  config.ledc_channel    = LEDC_CHANNEL_0;
  config.ledc_timer      = LEDC_TIMER_0;
  config.pin_d0          = Y2_GPIO_NUM;
  config.pin_d1          = Y3_GPIO_NUM;
  config.pin_d2          = Y4_GPIO_NUM;
  config.pin_d3          = Y5_GPIO_NUM;
  config.pin_d4          = Y6_GPIO_NUM;
  config.pin_d5          = Y7_GPIO_NUM;
  config.pin_d6          = Y8_GPIO_NUM;
  config.pin_d7          = Y9_GPIO_NUM;
  config.pin_xclk        = XCLK_GPIO_NUM;
  config.pin_pclk        = PCLK_GPIO_NUM;
  config.pin_vsync       = VSYNC_GPIO_NUM;
  config.pin_href        = HREF_GPIO_NUM;
  config.pin_sccb_sda    = SIOD_GPIO_NUM;
  config.pin_sccb_scl    = SIOC_GPIO_NUM;
  config.pin_pwdn        = PWDN_GPIO_NUM;
  config.pin_reset       = RESET_GPIO_NUM;
  config.xclk_freq_hz    = 20000000;
  config.pixel_format    = PIXFORMAT_JPEG;
  config.frame_size      = FRAMESIZE_VGA;
  config.jpeg_quality    = 12;
  config.fb_count        = 1;
  if (esp_camera_init(&config) != ESP_OK) {
    Serial.println("Camera init failed!");
    while (true) { delay(1000); }
  }

  // Connect Wi-Fi
  WiFi.begin(ssid, password);
  Serial.print("Connecting to Wi-Fi");
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("\nWi-Fi connected, IP: " + WiFi.localIP().toString());
}

void loop() {
  // Check for beam break (non-blocking edge detection)
  static bool prevState = LOW;
  bool currentState = digitalRead(LDR_PIN);
  
  if (prevState == LOW && currentState == HIGH) { // Rising edge detection
    Serial.println(">> Beam broken! Capturing & uploading…");
    captureAndUpload();
  }
  prevState = currentState;
  delay(10);
}

void captureAndUpload() {
  camera_fb_t *fb = esp_camera_fb_get();
  if (!fb) {
    Serial.println("Camera capture failed");
    return;
  }

  WiFiClient client;
  if (!client.connect(serverIP, serverPort)) {
    Serial.println("Connection failed");
    esp_camera_fb_return(fb);
    return;
  }

  // Build multipart request
  String header = 
    "--" + boundary + "\r\n" +
    "Content-Disposition: form-data; name=\"image\"; filename=\"capture.jpg\"\r\n" +
    "Content-Type: image/jpeg\r\n\r\n";
  
  String footer = "\r\n--" + boundary + "--\r\n";

  // Send request
  client.print("POST /upload HTTP/1.1\r\n");
  client.print("Host: " + String(serverIP) + "\r\n");
  client.print("Content-Length: " + String(header.length() + fb->len + footer.length()) + "\r\n");
  client.print("Content-Type: multipart/form-data; boundary=" + boundary + "\r\n");
  client.print("Connection: close\r\n\r\n"); // Force connection closure
  client.print(header);
  client.write(fb->buf, fb->len);
  client.print(footer);

  // Handle response with FIXED timeout (10 seconds total)
  unsigned long start = millis();
  while (client.connected() && millis() - start < 10000) {
    while (client.available()) {
      Serial.write(client.read());
    }
    delay(10);
  }

  // Cleanup
  client.stop();
  esp_camera_fb_return(fb);
  Serial.println(">> Upload done\n");
}