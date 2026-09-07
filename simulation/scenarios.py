"""Deterministic Scenarios for SentryHive Wildfire Simulation.

Provides repeatable test benchmarks:
1. Normal Forest Baseline (Clean diurnal cycles, no ignition)
2. Controlled Campfire (Localized heat, moderate CO/VOC, but zero rapid propagation)
3. False Positive Dust Storm (High PM10, high PM2.5, but normal gas resistance and ambient thermal)
4. Smoldering Peat & Root Wildfire (High pyrolysis CO/VOC, high PM2.5/PM10 ratio, sharp thermal IR anomaly, acoustic crackle)
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
import math
import numpy as np

@dataclass
class ScenarioEvent:
    time_s: float
    description: str
    parameter_deltas: Dict[str, float]

class SimulationScenario:
    def __init__(self, name: str, duration_s: float, description: str):
        self.name = name
        self.duration_s = duration_s
        self.description = description
        self.events: List[ScenarioEvent] = []

    def get_telemetry_modifier(self, elapsed_s: float) -> Dict[str, float]:
        return {}

class NormalForestBaselineScenario(SimulationScenario):
    def __init__(self, duration_s: float = 300.0):
        super().__init__("Normal Forest Baseline", duration_s, "Clean diurnal forest baseline with no combustion.")

    def get_telemetry_modifier(self, elapsed_s: float) -> Dict[str, float]:
        # Diurnal microclimate fluctuation
        diurnal = math.sin(elapsed_s * 2.0 * math.pi / 86400.0)
        return {
            "temp_c_delta": diurnal * 2.5,
            "humidity_delta": -diurnal * 5.0,
            "co_ppm": 0.2 + 0.05 * math.sin(elapsed_s * 0.1),
            "voc_index": 45.0 + 5.0 * math.cos(elapsed_s * 0.05),
            "pm2_5": 5.0 + 1.2 * math.sin(elapsed_s * 0.2),
            "pm10": 8.0 + 2.0 * math.cos(elapsed_s * 0.2),
            "thermal_delta_c": 0.5,
            "acoustic_hz": 0.05,
            "is_fire": False
        }

class ControlledCampfireScenario(SimulationScenario):
    def __init__(self, duration_s: float = 300.0):
        super().__init__("Controlled Campfire", duration_s, "Localized campfire with high VOC and localized warm spot, but low acoustic and steady particulates.")

    def get_telemetry_modifier(self, elapsed_s: float) -> Dict[str, float]:
        campfire_active = elapsed_s > 30.0
        intensity = min(1.0, (elapsed_s - 30.0) / 45.0) if campfire_active else 0.0
        return {
            "temp_c_delta": intensity * 3.0,
            "humidity_delta": -intensity * 4.0,
            "co_ppm": 0.5 + intensity * 2.2,
            "voc_index": 60.0 + intensity * 120.0,
            "pm2_5": 8.0 + intensity * 28.0,
            "pm10": 12.0 + intensity * 35.0,
            "thermal_delta_c": intensity * 14.0,
            "acoustic_hz": intensity * 0.8,
            "is_fire": False # Campfire is non-wildfire
        }

class FalsePositiveDustStormScenario(SimulationScenario):
    def __init__(self, duration_s: float = 300.0):
        super().__init__("False Positive Dust Storm", duration_s, "Severe particulate surge (PM10 > 250, PM2.5 > 80) due to mineral dust, but cold thermals and clean gas.")

    def get_telemetry_modifier(self, elapsed_s: float) -> Dict[str, float]:
        storm_active = elapsed_s > 20.0
        intensity = min(1.0, (elapsed_s - 20.0) / 30.0) if storm_active else 0.0
        return {
            "temp_c_delta": -intensity * 1.5,
            "humidity_delta": -intensity * 15.0,
            "co_ppm": 0.2, # No combustion CO
            "voc_index": 40.0, # Normal VOC
            "pm2_5": 6.0 + intensity * 95.0,
            "pm10": 10.0 + intensity * 380.0, # Massive coarse dust
            "thermal_delta_c": 0.2, # Zero thermal hotspot
            "acoustic_hz": 0.02, # No wood crackle
            "is_fire": False
        }

class SmolderingPeatWildfireScenario(SimulationScenario):
    def __init__(self, duration_s: float = 300.0):
        super().__init__("Smoldering Peat & Root Wildfire", duration_s, "Pre-canopy ignition: heavy pyrolysis VOCs, ultra-fine PM2.5, hotspot divergence, and high crackle.")

    def get_telemetry_modifier(self, elapsed_s: float) -> Dict[str, float]:
        ignition_active = elapsed_s > 25.0
        intensity = min(1.0, (elapsed_s - 25.0) / 40.0) if ignition_active else 0.0
        return {
            "temp_c_delta": intensity * 12.5,
            "humidity_delta": -intensity * 28.0,
            "co_ppm": 0.4 + intensity * 18.5,
            "voc_index": 50.0 + intensity * 420.0,
            "pm2_5": 7.0 + intensity * 165.0,
            "pm10": 11.0 + intensity * 185.0, # Very high PM2.5/PM10 ratio (~0.9)
            "thermal_delta_c": intensity * 38.0,
            "acoustic_hz": intensity * 14.5, # Aggressive cavitation/crackle
            "is_fire": True
        }

class ScenarioRunner:
    def __init__(self):
        self.scenarios = {
            "normal": NormalForestBaselineScenario(),
            "campfire": ControlledCampfireScenario(),
            "dust_storm": FalsePositiveDustStormScenario(),
            "wildfire": SmolderingPeatWildfireScenario()
        }

    def run_scenario(self, scenario_key: str, step_count: int = 60, step_dt: float = 1.0) -> List[Dict[str, Any]]:
        scenario = self.scenarios.get(scenario_key, self.scenarios["normal"])
        history = []
        for step in range(step_count):
            t = step * step_dt
            mod = scenario.get_telemetry_modifier(t)
            mod["time_s"] = t
            history.append(mod)
        return history
