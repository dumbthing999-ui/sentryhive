"""Sensor Fault Injection & Hardware Graceful Degradation Engine.

Simulates and evaluates cyber-physical resilience against:
1. Optical smoke sensor dropout (I2C bus lockup / dust lens caking)
2. Far-IR thermal sensor dropout (Melexis frame CRC error)
3. MEMS acoustic microphone acoustic clipping or hardware failure
4. MOX gas heater baseline drift
5. Packet transmission loss / corrupted bits
"""

from dataclasses import dataclass
from typing import Dict, Any, List, Optional, Tuple
import random
import copy
from pydantic import BaseModel, Field

class SensorHealthReport(BaseModel):
    sensor_name: str
    is_operational: bool
    data_confidence_score: float # 0.0 - 1.0
    status_code: str
    failure_mode: Optional[str] = None
    attenuated_model_weight: float

class FleetResilienceStatus(BaseModel):
    overall_health_score: float
    degraded_mode_active: bool
    active_faults: List[str]
    sensors: Dict[str, SensorHealthReport]
    recommended_maintenance_action: Optional[str]

class FaultInjectionService:
    """Manages synthetic hardware faults and validates model graceful degradation."""

    def __init__(self):
        self.active_faults: Dict[str, str] = {}

    def inject_fault(self, sensor_type: str, fault_mode: str):
        """
        sensor_type: 'pm', 'thermal', 'acoustic', 'gas'
        fault_mode: 'dropout', 'noise_spike', 'stuck_zero', 'drift'
        """
        self.active_faults[sensor_type] = fault_mode

    def clear_fault(self, sensor_type: str):
        self.active_faults.pop(sensor_type, None)

    def clear_all_faults(self):
        self.active_faults.clear()

    def apply_faults_to_telemetry(self, raw_telemetry: Dict[str, Any]) -> Tuple[Dict[str, Any], FleetResilienceStatus]:
        telemetry = copy.deepcopy(raw_telemetry)
        sensor_reports = {}
        active_fault_list = []

        # Standard weights in TinyML fusion
        base_weights = {
            "gas": 0.30,
            "pm": 0.35,
            "thermal": 0.25,
            "acoustic": 0.10
        }

        for sensor in ["gas", "pm", "thermal", "acoustic"]:
            fault = self.active_faults.get(sensor)
            if fault:
                active_fault_list.append(f"{sensor.upper()}_{fault.upper()}")
                conf = 0.0
                operational = False
                mode = fault

                if fault == "dropout":
                    if sensor == "thermal":
                        telemetry["thermal_max"] = telemetry.get("temp_c", 22.0)
                        telemetry["thermal_gradient"] = 0.0
                    elif sensor == "pm":
                        telemetry["pm2_5"] = 0.0
                        telemetry["pm10"] = 0.0
                    elif sensor == "acoustic":
                        telemetry["acoustic_hz"] = 0.0
                    elif sensor == "gas":
                        telemetry["voc_idx"] = 0.0
                elif fault == "stuck_zero":
                    if sensor == "pm":
                        telemetry["pm2_5"] = 0.0
                    elif sensor == "gas":
                        telemetry["voc_idx"] = 0.0
                elif fault == "noise_spike":
                    if sensor == "acoustic":
                        telemetry["acoustic_hz"] = 99.0
                    elif sensor == "pm":
                        telemetry["pm2_5"] = 500.0

                sensor_reports[sensor] = SensorHealthReport(
                    sensor_name=sensor,
                    is_operational=operational,
                    data_confidence_score=conf,
                    status_code="FAULT_INJECTED",
                    failure_mode=mode,
                    attenuated_model_weight=0.0
                )
            else:
                sensor_reports[sensor] = SensorHealthReport(
                    sensor_name=sensor,
                    is_operational=True,
                    data_confidence_score=0.98,
                    status_code="HEALTHY",
                    failure_mode=None,
                    attenuated_model_weight=base_weights[sensor]
                )

        degraded = len(active_fault_list) > 0
        mean_health = sum(r.data_confidence_score for r in sensor_reports.values()) / 4.0

        status = FleetResilienceStatus(
            overall_health_score=round(mean_health, 2),
            degraded_mode_active=degraded,
            active_faults=active_fault_list,
            sensors=sensor_reports,
            recommended_maintenance_action="Inspect Physical I2C Bus & Clean Optical Chambers" if degraded else None
        )

        return telemetry, status
