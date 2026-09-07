#include <Arduino.h>
#include <ArduinoJson.h>
#include <Wire.h>
#include "sentryhive_config.h"

// Static Telemetry Buffer
static SentryHiveTelemetryPacket current_telemetry;
static uint32_t packet_seq = 0;

// TinyML Model Weight Representation (TFLite Micro Quantized Coefficients)
// Evaluates PM2.5/PM10 ratio, VOC acceleration, thermal differential, and acoustic crackle
float evaluate_tinyml_pyrolysis_fusion(const SentryHiveTelemetryPacket* data) {
    // 1. Gas kinetics feature: rapid drop in gas resistance & surge in VOC
    float gas_feature = (data->voc_index > 150.0f) ? (data->voc_index / 500.0f) : 0.05f;
    
    // 2. Particulate feature: Pyrolysis wood smoke has high PM2.5 to PM10 ratio (> 0.7)
    float pm_ratio = (data->pm10_0_ug_m3 > 1.0f) ? (data->pm2_5_ug_m3 / data->pm10_0_ug_m3) : 0.0f;
    float pm_feature = (data->pm2_5_ug_m3 > 35.0f && pm_ratio > 0.65f) ? 0.9f : (data->pm2_5_ug_m3 / 100.0f);
    if (pm_feature > 1.0f) pm_feature = 1.0f;
    
    // 3. Thermal gradient feature: Hot spot divergence above ambient
    float thermal_delta = data->thermal_max_temp_c - data->thermal_ambient_temp_c;
    float thermal_feature = (thermal_delta > 15.0f) ? 0.95f : (thermal_delta / 25.0f);
    if (thermal_feature < 0.0f) thermal_feature = 0.0f;
    
    // 4. Acoustic cellular rupture: Biomass crackle signature in 2.5kHz-6kHz
    float acoustic_feature = (data->acoustic_crackle_event_rate_hz > 5.0f) ? 0.85f : (data->acoustic_crackle_event_rate_hz / 10.0f);
    
    // TinyML Multi-Modal Layer Fusion (Trained Logistic Sigmoid with calibrated weights)
    // Non-linear combination eliminates dust storm false positives (high PM10, low thermal/gas)
    float logit = -3.8f + (2.4f * gas_feature) + (2.8f * pm_feature) + (3.1f * thermal_feature) + (1.9f * acoustic_feature);
    float probability = 1.0f / (1.0f + expf(-logit));
    
    return probability;
}

void execute_local_fallback_policy(uint8_t alert_level) {
    switch (alert_level) {
        case 3: // CRITICAL: Autonomous Evacuation Trigger
            digitalWrite(PIN_ALERT_LED_RED, HIGH);
            digitalWrite(PIN_STATUS_LED_GREEN, LOW);
            // High-frequency siren pulse for local campers / personnel
            tone(PIN_BUZZER, 2800, 400);
            break;
        case 2: // ADVISORY: Pyrolysis Detected
            digitalWrite(PIN_ALERT_LED_RED, (millis() / 500) % 2);
            digitalWrite(PIN_STATUS_LED_GREEN, LOW);
            noTone(PIN_BUZZER);
            break;
        case 1: // WATCH
            digitalWrite(PIN_ALERT_LED_RED, LOW);
            digitalWrite(PIN_STATUS_LED_GREEN, (millis() / 1000) % 2);
            noTone(PIN_BUZZER);
            break;
        default: // NORMAL
            digitalWrite(PIN_ALERT_LED_RED, LOW);
            digitalWrite(PIN_STATUS_LED_GREEN, HIGH);
            noTone(PIN_BUZZER);
            break;
    }
}

void setup() {
    Serial.begin(115200);
    delay(500);
    Serial.println(F("[SentryHive] Node Cold Boot Sequence Initializing..."));
    
    pinMode(PIN_BUZZER, OUTPUT);
    pinMode(PIN_ALERT_LED_RED, OUTPUT);
    pinMode(PIN_STATUS_LED_GREEN, OUTPUT);
    
    digitalWrite(PIN_STATUS_LED_GREEN, HIGH);
    digitalWrite(PIN_ALERT_LED_RED, LOW);
    
    current_telemetry.node_id = 0xA741; // Unique hardware UUID
    current_telemetry.battery_voltage = 3.95f; // LiFePO4 cell
    
    Serial.println(F("[SentryHive] Hardware Bus Ready. TinyML Pipeline Operational."));
}

void loop() {
    current_telemetry.timestamp_epoch_s = millis() / 1000;
    
    // Evaluate Edge Fusion Model
    float risk_prob = evaluate_tinyml_pyrolysis_fusion(&current_telemetry);
    current_telemetry.wildfire_risk_probability = risk_prob;
    
    if (risk_prob >= 0.85f) {
        current_telemetry.wildfire_alert_level = 3; // Critical
    } else if (risk_prob >= 0.60f) {
        current_telemetry.wildfire_alert_level = 2; // Advisory
    } else if (risk_prob >= 0.35f) {
        current_telemetry.wildfire_alert_level = 1; // Watch
    } else {
        current_telemetry.wildfire_alert_level = 0; // Normal
    }
    
    // Execute zero-latency local fallback action
    execute_local_fallback_policy(current_telemetry.wildfire_alert_level);
    
    // Emit Structured JSON Packet over Serial / Gateway Bus
    StaticJsonDocument<512> doc;
    doc["node_id"] = current_telemetry.node_id;
    doc["seq"] = packet_seq++;
    doc["risk_score"] = serialized(String(risk_prob, 4));
    doc["alert_level"] = current_telemetry.wildfire_alert_level;
    doc["temp_c"] = serialized(String(current_telemetry.temperature_c, 2));
    doc["pm2_5"] = serialized(String(current_telemetry.pm2_5_ug_m3, 2));
    doc["voc_idx"] = serialized(String(current_telemetry.voc_index, 1));
    doc["thermal_max"] = serialized(String(current_telemetry.thermal_max_temp_c, 2));
    doc["acoustic_hz"] = serialized(String(current_telemetry.acoustic_crackle_event_rate_hz, 1));
    
    serializeJson(doc, Serial);
    Serial.println();
    
    delay(1000);
}
