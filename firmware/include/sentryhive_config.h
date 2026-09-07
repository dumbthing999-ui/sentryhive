#pragma once

#include <stdint.h>
#include <stdbool.h>

// Hardware Pin Configuration for SentryHive v1.0
// ESP32-S3-WROOM-1 DevKit Pin Mapping

// I2C Bus (BME688, Sensirion SPS30, MLX90640)
#define PIN_I2C_SDA             8
#define PIN_I2C_SCL             9
#define I2C_FREQUENCY_HZ        400000

// I2S MEMS Microphone (Acoustic Pyrolysis Detection)
#define PIN_I2S_BCLK            4
#define PIN_I2S_LRC             5
#define PIN_I2S_DIN             6
#define I2S_SAMPLE_RATE_HZ      16000
#define I2S_BUFFER_SAMPLES      512

// SX1262 LoRa SPI Bus
#define PIN_LORA_SCK            12
#define PIN_LORA_MISO           13
#define PIN_LORA_MOSI           11
#define PIN_LORA_CS             10
#define PIN_LORA_RST            14
#define PIN_LORA_BUSY           21
#define PIN_LORA_DIO1           47

// Alert Actuators (Local Autonomous Fallback)
#define PIN_BUZZER              1
#define PIN_ALERT_LED_RED       2
#define PIN_STATUS_LED_GREEN    48

// Multi-Modal Telemetry Data Structure
typedef struct __attribute__((packed)) {
    uint32_t node_id;
    uint32_t timestamp_epoch_s;
    float battery_voltage;
    
    // Gas & Microclimate (Bosch BME688)
    float temperature_c;
    float relative_humidity_pct;
    float barometric_pressure_hpa;
    float gas_resistance_ohms;
    float voc_index;
    
    // Particulate Matter (Sensirion SPS30)
    float pm1_0_ug_m3;
    float pm2_5_ug_m3;
    float pm4_0_ug_m3;
    float pm10_0_ug_m3;
    float typical_particle_size_um;
    
    // Thermal Far-IR Focal Array (Melexis MLX90640 32x24)
    float thermal_max_temp_c;
    float thermal_ambient_temp_c;
    float thermal_gradient_c_per_sec;
    
    // Acoustic Pyrolysis Classifier
    float acoustic_crackle_event_rate_hz;
    float acoustic_spectral_energy_ratio;
    
    // TinyML Edge Classifier Verdict
    uint8_t wildfire_alert_level; // 0=Normal, 1=Watch, 2=Advisory, 3=Critical
    float wildfire_risk_probability; // 0.0 - 1.0
} SentryHiveTelemetryPacket;
