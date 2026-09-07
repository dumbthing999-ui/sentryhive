"""
SentryHive: Edge Wildfire & Microclimate Multi-Modal Early Warning Network
Virtual Node Emulator & Multi-Modal Telemetry Generator
"""

import time
import math
import random
import numpy as np
from typing import Dict, Any, List
from simulation.physics_engine import PhysicsEngine


class VirtualNodeEmulator:
    def __init__(self):
        self.physics = PhysicsEngine()
        self.active_scenario = "normal"
        self.ab_mode = "ai"  # "ai" (SentryHive TinyML) or "naive" (Standard Threshold)
        self.start_time = time.time()
        self.packet_seq = 1000

        # Define 4 deployed sensor nodes across the forest terrain
        self.nodes = {
            "0xA741": {
                "id": "0xA741",
                "name": "Node Alpha — North Ridge",
                "lat": 39.0968,
                "lon": -120.0324,
                "elevation_m": 2150,
                "role": "Canopy Microclimate Node",
                "is_gateway": False,
                "battery_voltage": 3.96,
                "rssi_dbm": -82,
                "snr_db": 9.4,
                "hotspot_xy": (16, 12),
                "flash_logs_count": 1420
            },
            "0xB812": {
                "id": "0xB812",
                "name": "Node Bravo — Canyon Floor",
                "lat": 39.0912,
                "lon": -120.0280,
                "elevation_m": 1890,
                "role": "Canopy Microclimate Node",
                "is_gateway": False,
                "battery_voltage": 3.92,
                "rssi_dbm": -89,
                "snr_db": 7.8,
                "hotspot_xy": (10, 15),
                "flash_logs_count": 1388
            },
            "0xC309": {
                "id": "0xC309",
                "name": "Node Charlie — East Bluff",
                "lat": 39.0945,
                "lon": -120.0210,
                "elevation_m": 2040,
                "role": "Canopy Microclimate Node",
                "is_gateway": False,
                "battery_voltage": 3.94,
                "rssi_dbm": -86,
                "snr_db": 8.5,
                "hotspot_xy": (22, 9),
                "flash_logs_count": 1405
            },
            "0xD450": {
                "id": "0xD450",
                "name": "Node Delta — South Pass Gateway",
                "lat": 39.0880,
                "lon": -120.0350,
                "elevation_m": 1980,
                "role": "Base Gateway & LTE-M Core",
                "is_gateway": True,
                "battery_voltage": 4.02,
                "rssi_dbm": -74,
                "snr_db": 11.2,
                "hotspot_xy": (8, 18),
                "flash_logs_count": 2150
            }
        }

    def set_scenario(self, scenario_name: str) -> str:
        valid = ["normal", "campfire", "dust_storm", "wildfire"]
        if scenario_name in valid:
            self.active_scenario = scenario_name
            return self.active_scenario
        raise ValueError(f"Invalid scenario: {scenario_name}. Choose from {valid}")

    def set_ab_mode(self, mode: str) -> str:
        if mode in ["ai", "naive"]:
            self.ab_mode = mode
            return self.ab_mode
        raise ValueError(f"Invalid A/B mode: {mode}. Choose 'ai' or 'naive'")

    def evaluate_tinyml(
        self,
        voc_index: float,
        pm2_5: float,
        pm10_0: float,
        ir_max: float,
        ir_ambient: float,
        acoustic_hz: float
    ) -> Dict[str, Any]:
        """
        Exact on-device TinyML Multi-Modal Logistic Sigmoid Fusion matching firmware/src/main.cpp
        """
        # 1. Gas kinetics feature: VOC acceleration
        gas_feature = (voc_index / 500.0) if voc_index > 150.0 else (voc_index / 1500.0)
        gas_feature = max(0.02, min(gas_feature, 1.0))

        # 2. Particulate feature: Sub-micron pyrolysis ratio vs coarse dust
        pm_ratio = (pm2_5 / pm10_0) if pm10_0 > 1.0 else 0.5
        if pm2_5 > 35.0 and pm_ratio > 0.65:
            pm_feature = min(1.0, 0.5 + (pm2_5 / 200.0))
        else:
            # Low ratio (dust storm) severely suppresses PM weight
            pm_feature = (pm2_5 / 150.0) * (pm_ratio ** 1.8)
        pm_feature = max(0.01, min(pm_feature, 1.0))

        # 3. Thermal gradient feature: Hot spot divergence above ambient
        thermal_delta = ir_max - ir_ambient
        if thermal_delta > 15.0:
            thermal_feature = min(1.0, 0.6 + (thermal_delta / 80.0))
        else:
            thermal_feature = max(0.0, thermal_delta / 30.0)

        # 4. Acoustic cavitation: Wood tracheid cell rupture in 2.5kHz-6kHz
        if acoustic_hz > 5.0:
            acoustic_feature = min(1.0, 0.4 + (acoustic_hz / 15.0))
        else:
            acoustic_feature = max(0.0, acoustic_hz / 12.0)

        # Multi-Modal Sigmoid Fusion
        # logit = -3.8 + 2.4*gas + 2.8*pm + 3.1*thermal + 1.9*acoustic
        logit = -3.8 + (2.4 * gas_feature) + (2.8 * pm_feature) + (3.1 * thermal_feature) + (1.9 * acoustic_feature)
        fti = 1.0 / (1.0 + math.exp(-logit))
        fti = max(0.01, min(fti, 0.99))

        # Alert level: 0=NOMINAL, 1=WATCH, 2=WARNING, 3=CRITICAL
        if fti >= 0.85:
            alert_level = 3
            level_name = "CRITICAL"
        elif fti >= 0.60:
            alert_level = 2
            level_name = "WARNING"
        elif fti >= 0.30:
            alert_level = 1
            level_name = "WATCH"
        else:
            alert_level = 0
            level_name = "NOMINAL"

        return {
            "fti": round(fti, 4),
            "alert_level": alert_level,
            "level_name": level_name,
            "gas_contribution_pct": round(gas_feature * 35.0, 1),
            "thermal_contribution_pct": round(thermal_feature * 25.0, 1),
            "acoustic_contribution_pct": round(acoustic_feature * 25.0, 1),
            "pm_ratio_contribution_pct": round(pm_feature * 15.0, 1)
        }

    def evaluate_naive_threshold(
        self,
        pm2_5: float,
        pm10_0: float,
        ir_max: float
    ) -> Dict[str, Any]:
        """
        Conventional single-variable threshold detector.
        Fails on dust storms (PM spike) and delays early smoldering pyrolysis.
        """
        tripped = False
        reasons = []

        if pm2_5 > 35.0 or pm10_0 > 50.0:
            tripped = True
            reasons.append(f"PM Threshold Exceeded ({max(pm2_5, pm10_0):.1f} ug/m3)")

        if ir_max > 45.0:
            tripped = True
            reasons.append(f"Thermal Threshold Exceeded ({ir_max:.1f}°C)")

        if tripped:
            alert_level = 3
            level_name = "CRITICAL"
            fti_proxy = 0.92
        else:
            alert_level = 0
            level_name = "NOMINAL"
            fti_proxy = 0.05

        return {
            "fti_proxy": fti_proxy,
            "alert_level": alert_level,
            "level_name": level_name,
            "reasons": reasons,
            "is_false_alarm": (self.active_scenario in ["dust_storm", "campfire"]) and tripped
        }

    def sample_telemetry(self, node_id: str) -> Dict[str, Any]:
        """
        Generates a complete telemetry packet for a specific node under the active scenario.
        """
        node = self.nodes.get(node_id, self.nodes["0xA741"])
        t = time.time() - self.start_time
        jitter = math.sin(t * 0.8 + hash(node_id) % 10) * 0.4
        self.packet_seq += 1

        scenario = self.active_scenario
        is_affected_node = (node_id == "0xA741") or (scenario == "dust_storm") or (scenario == "campfire" and node_id == "0xB812")

        # Baseline defaults
        temp_c = 21.4 + jitter * 0.5
        humidity = 42.0 + math.cos(t * 0.5) * 1.5
        pressure = 1013.2 + jitter * 0.2
        gas_res_kohm = 185.0 + jitter * 5.0
        voc_index = max(5.0, 14.0 + jitter * 3.0)
        pm1_0 = max(0.5, 2.2 + jitter * 0.4)
        pm2_5 = max(1.0, 5.4 + jitter * 0.8)
        pm4_0 = max(1.5, 6.8 + jitter * 0.9)
        pm10_0 = max(2.0, 8.5 + jitter * 1.2)
        ir_ambient = temp_c
        ir_max = ir_ambient + 1.2 + abs(jitter) * 0.3
        thermal_gradient = 0.15 + abs(jitter) * 0.05
        acoustic_hz = max(0.0, 0.1 + abs(jitter) * 0.1)
        acoustic_spectral_ratio = 0.04
        hotspot_xy = node["hotspot_xy"]
        hotspot_rad = 1.0
        wind_speed = 3.5 + jitter * 0.5
        wind_dir = 35.0

        if scenario == "normal":
            pass
        elif scenario == "campfire":
            if node_id == "0xB812":  # Campfire located at Canyon Floor
                temp_c = 24.5 + jitter * 0.8
                humidity = 38.0 + jitter
                pressure = 1012.8
                gas_res_kohm = 95.0 + jitter * 6.0
                voc_index = 85.0 + jitter * 8.0
                pm1_0 = 12.0 + jitter * 1.5
                pm2_5 = 38.5 + jitter * 3.0
                pm4_0 = 46.0 + jitter * 4.0
                pm10_0 = 54.0 + jitter * 5.0
                ir_ambient = 22.0
                ir_max = 68.4 + jitter * 2.5
                thermal_gradient = 3.8 + abs(jitter) * 0.5
                acoustic_hz = 1.2 + abs(jitter) * 0.3  # Light wood crackle
                acoustic_spectral_ratio = 0.25
                hotspot_xy = (10, 15)
                hotspot_rad = 2.4
                wind_speed = 2.2 + jitter * 0.3
                wind_dir = 40.0
            else:
                # Distant node
                temp_c = 21.8 + jitter * 0.3
                humidity = 41.5
                pressure = 1013.0
                gas_res_kohm = 160.0 + jitter * 4.0
                voc_index = 22.0 + jitter * 2.0
                pm1_0 = 3.1
                pm2_5 = 8.4
                pm4_0 = 10.2
                pm10_0 = 12.5
                ir_ambient = 21.5
                ir_max = 23.2
                thermal_gradient = 0.3
                acoustic_hz = 0.1
                acoustic_spectral_ratio = 0.05
                hotspot_xy = node["hotspot_xy"]
                hotspot_rad = 1.0
                wind_speed = 3.0
                wind_dir = 35.0

        elif scenario == "dust_storm":
            # High coarse particulates, but cold thermal, clean gas, no wood acoustic crackle
            temp_c = 23.8 + jitter * 0.4
            humidity = 24.0 + jitter * 1.0
            pressure = 1010.5 + jitter * 0.5
            gas_res_kohm = 168.0 + jitter * 3.0  # Normal gas
            voc_index = 21.0 + jitter * 2.0     # Clean air volatiles
            pm1_0 = 8.5 + jitter * 1.0
            pm2_5 = 42.0 + jitter * 3.5         # Moderate PM2.5
            pm4_0 = 125.0 + jitter * 10.0
            pm10_0 = 285.0 + jitter * 18.0      # Massive coarse dust! Ratio = 42/285 = 0.14
            ir_ambient = temp_c
            ir_max = ir_ambient + 1.1 + abs(jitter) * 0.2  # No thermal hotspot
            thermal_gradient = 0.2
            acoustic_hz = 0.0                   # Zero wood cavitation
            acoustic_spectral_ratio = 0.02
            hotspot_xy = node["hotspot_xy"]
            hotspot_rad = 1.0
            wind_speed = 12.8 + jitter * 1.5   # Strong gale
            wind_dir = 55.0

        elif scenario == "wildfire":
            # Phase 0 Smoldering Pine Duff Combustion at Node Alpha (North Ridge)
            if node_id == "0xA741":
                temp_c = 34.2 + jitter * 1.2
                humidity = 18.5 - jitter * 0.8
                pressure = 1011.0
                gas_res_kohm = 12.4 + jitter * 1.5   # Hemicellulose/cellulose decomposition
                voc_index = 465.0 + jitter * 20.0    # Massive furfural / levoglucosan
                pm1_0 = 92.0 + jitter * 8.0
                pm2_5 = 188.5 + jitter * 12.0        # Sub-micron pyrolytic smoke
                pm4_0 = 196.0 + jitter * 14.0
                pm10_0 = 208.0 + jitter * 15.0       # PM ratio = 188.5/208 = 0.91!
                ir_ambient = 22.5
                ir_max = 194.2 + jitter * 8.0        # Deep smoldering hotspot
                thermal_gradient = 18.4 + abs(jitter) * 2.0
                acoustic_hz = 17.6 + abs(jitter) * 2.5 # Violent wood tracheid micro-cavitation
                acoustic_spectral_ratio = 0.88
                hotspot_xy = (16, 12)
                hotspot_rad = 4.8
                wind_speed = 5.6 + jitter * 0.8
                wind_dir = 35.0
            else:
                # Downwind propagation to neighboring nodes
                temp_c = 26.5 + jitter * 0.6
                humidity = 29.0
                pressure = 1012.0
                gas_res_kohm = 54.0 + jitter * 4.0
                voc_index = 185.0 + jitter * 12.0
                pm1_0 = 24.0 + jitter * 3.0
                pm2_5 = 64.0 + jitter * 6.0
                pm4_0 = 70.0 + jitter * 7.0
                pm10_0 = 76.0 + jitter * 8.0
                ir_ambient = 22.0
                ir_max = 42.0 + jitter * 2.0
                thermal_gradient = 4.2
                acoustic_hz = 3.5 + abs(jitter) * 0.8
                acoustic_spectral_ratio = 0.42
                hotspot_xy = node["hotspot_xy"]
                hotspot_rad = 2.2
                wind_speed = 5.2
                wind_dir = 35.0

        # Generate 32x24 Far-IR Thermal Array
        drift_x = math.sin(math.radians(wind_dir)) * 1.5
        drift_y = -math.cos(math.radians(wind_dir)) * 1.5
        thermal_matrix = self.physics.generate_thermal_matrix(
            hotspot_center=hotspot_xy,
            max_temp=ir_max,
            ambient_temp=ir_ambient,
            radius=hotspot_rad,
            plume_drift=(drift_x, drift_y),
            noise_std=0.2
        )
        sobel_mag, sobel_vec = self.physics.compute_spatial_gradient(thermal_matrix)

        # Run AI vs Naive evaluation
        ai_verdict = self.evaluate_tinyml(
            voc_index=voc_index,
            pm2_5=pm2_5,
            pm10_0=pm10_0,
            ir_max=ir_max,
            ir_ambient=ir_ambient,
            acoustic_hz=acoustic_hz
        )

        naive_verdict = self.evaluate_naive_threshold(
            pm2_5=pm2_5,
            pm10_0=pm10_0,
            ir_max=ir_max
        )

        # Rothermel fire spread & evacuation route
        effective_fti = ai_verdict["fti"] if self.ab_mode == "ai" else naive_verdict["fti_proxy"]
        spread_info = self.physics.calculate_rothermel_spread(
            fti_score=effective_fti,
            wind_speed_ms=wind_speed,
            wind_dir_deg=wind_dir,
            slope_deg=14.0
        )

        # Hardware fallback status
        gpio_siren_active = (effective_fti >= 0.85)
        lora_p2p_active = (effective_fti >= 0.85)
        spiffs_blackbox_active = True

        return {
            "seq": self.packet_seq,
            "timestamp": int(time.time()),
            "node_id": node["id"],
            "node_name": node["name"],
            "role": node["role"],
            "is_gateway": node["is_gateway"],
            "elevation_m": node["elevation_m"],
            "coordinates": {"lat": node["lat"], "lon": node["lon"]},
            "active_scenario": scenario,
            "ab_mode": self.ab_mode,

            # Microclimate & Gas
            "temperature_c": round(temp_c, 2),
            "humidity_pct": round(humidity, 1),
            "pressure_hpa": round(pressure, 2),
            "gas_resistance_kohm": round(gas_res_kohm, 2),
            "voc_index": round(voc_index, 1),

            # Particulate Matter (SPS30)
            "pm1_0_ug_m3": round(pm1_0, 1),
            "pm2_5_ug_m3": round(pm2_5, 1),
            "pm4_0_ug_m3": round(pm4_0, 1),
            "pm10_0_ug_m3": round(pm10_0, 1),
            "pm_ratio": round(pm2_5 / max(1.0, pm10_0), 3),

            # Thermal Radiance (MLX90640 32x24)
            "thermal_ambient_c": round(ir_ambient, 2),
            "thermal_max_c": round(ir_max, 2),
            "thermal_delta_c": round(ir_max - ir_ambient, 2),
            "thermal_gradient_c_per_sec": round(thermal_gradient, 2),
            "sobel_gradient_magnitude": round(sobel_mag, 2),
            "sobel_vector": [round(sobel_vec[0], 3), round(sobel_vec[1], 3)],
            "thermal_matrix": thermal_matrix.round(1).tolist(),

            # Acoustic Pyrolysis Classifier (INMP441)
            "acoustic_crackle_hz": round(acoustic_hz, 2),
            "acoustic_spectral_ratio": round(acoustic_spectral_ratio, 3),

            # Inference Decisions
            "ai_fusion": ai_verdict,
            "naive_threshold": naive_verdict,
            "effective_alert_level": ai_verdict["alert_level"] if self.ab_mode == "ai" else naive_verdict["alert_level"],
            "effective_level_name": ai_verdict["level_name"] if self.ab_mode == "ai" else naive_verdict["level_name"],
            "effective_fti": effective_fti,

            # Propagation & Evacuation
            "wind": {
                "speed_ms": round(wind_speed, 1),
                "speed_kmh": round(wind_speed * 3.6, 1),
                "heading_deg": round(wind_dir, 1)
            },
            "spread_dynamics": spread_info,

            # Hardware Health & Autonomous Fallback
            "hardware": {
                "battery_v": round(node["battery_voltage"] - (0.02 if scenario == "wildfire" else 0.0), 2),
                "battery_pct": 94 if node["battery_voltage"] > 3.90 else 82,
                "power_tier": 0 if node["battery_voltage"] >= 3.30 else 1,
                "rssi_dbm": node["rssi_dbm"],
                "snr_db": node["snr_db"],
                "gpio5_piezo_siren": gpio_siren_active,
                "strobe_beacon_active": gpio_siren_active,
                "lora_p2p_mesh_flooding": lora_p2p_active,
                "spiffs_blackbox_logs": node["flash_logs_count"] + (self.packet_seq % 200)
            }
        }

    def get_all_nodes_telemetry(self) -> List[Dict[str, Any]]:
        return [self.sample_telemetry(nid) for nid in self.nodes.keys()]
