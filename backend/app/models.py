"""Pydantic schemas and domain models for SentryHive.

Covers multi-modal sensor telemetry, node health, battery power tiers,
spatial coordinates, multi-tier wildfire alerts, A/B ML comparison verdicts,
and GeoJSON digital twin representations.
"""

from __future__ import annotations

import enum
import time
import uuid
from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field, field_validator, model_validator


class BatteryDegradationTier(int, enum.Enum):
    """LiFePO4 Power Management Degradation Tiers.
    
    TIER 0: >= 3.30V (Full Nominal: 1Hz inference, 60s LoRa check-in)
    TIER 1: 3.15V - 3.30V (Duty-Cycled: thermal 0.25Hz, acoustic 50%, 120s check-in)
    TIER 2: 3.00V - 3.15V (Low-Power Triage: thermal/acoustic off, BME/SPS 0.1Hz, 300s check-in)
    TIER 3: < 3.00V (Emergency Survival: deep sleep ULP wakeup, 1800s heartbeat)
    """
    TIER_0_FULL_NOMINAL = 0
    TIER_1_DUTY_CYCLED = 1
    TIER_2_LOW_POWER_TRIAGE = 2
    TIER_3_EMERGENCY_SURVIVAL = 3


class AlertLevel(str, enum.Enum):
    """Multi-tier wildfire threat classification."""
    NOMINAL = "NOMINAL"
    WATCH = "WATCH"
    ADVISORY = "ADVISORY"
    CRITICAL_EVACUATION = "CRITICAL_EVACUATION"

    @classmethod
    def from_severity_code(cls, code: int) -> "AlertLevel":
        mapping = {
            0: cls.NOMINAL,
            1: cls.WATCH,
            2: cls.ADVISORY,
            3: cls.CRITICAL_EVACUATION
        }
        return mapping.get(code, cls.NOMINAL)

    @property
    def severity_code(self) -> int:
        mapping = {
            self.NOMINAL: 0,
            self.WATCH: 1,
            self.ADVISORY: 2,
            self.CRITICAL_EVACUATION: 3
        }
        return mapping[self]


class NodeConnectionStatus(str, enum.Enum):
    """Operational connection status of an edge sensor node."""
    ONLINE = "ONLINE"
    DEGRADED = "DEGRADED"
    OFFLINE = "OFFLINE"
    EMERGENCY = "EMERGENCY"


class GeoCoordinates(BaseModel):
    """Geospatial coordinates and terrain metadata for a sensor node."""
    latitude: float = Field(..., ge=-90.0, le=90.0, description="Latitude in decimal degrees")
    longitude: float = Field(..., ge=-180.0, le=180.0, description="Longitude in decimal degrees")
    elevation_m: float = Field(default=0.0, description="Elevation above sea level in meters")
    canopy_coverage_pct: float = Field(default=75.0, ge=0.0, le=100.0, description="Forest canopy density %")
    vegetation_type: str = Field(default="Mixed Conifer / Pine", description="Fuel bed classification")


class BatteryMetrics(BaseModel):
    """Battery state and power degradation tracking."""
    voltage_v: float = Field(default=3.95, ge=0.0, le=5.0, description="Cell terminal voltage in Volts")
    percentage: float = Field(default=95.0, ge=0.0, le=100.0, description="Estimated state of charge %")
    degradation_tier: BatteryDegradationTier = Field(
        default=BatteryDegradationTier.TIER_0_FULL_NOMINAL,
        description="Active power management tier"
    )

    @model_validator(mode="before")
    @classmethod
    def determine_tier_from_voltage(cls, data: Any) -> Any:
        if isinstance(data, dict):
            voltage = data.get("voltage_v")
            if voltage is not None and "degradation_tier" not in data:
                if voltage >= 3.30:
                    data["degradation_tier"] = BatteryDegradationTier.TIER_0_FULL_NOMINAL
                elif voltage >= 3.15:
                    data["degradation_tier"] = BatteryDegradationTier.TIER_1_DUTY_CYCLED
                elif voltage >= 3.00:
                    data["degradation_tier"] = BatteryDegradationTier.TIER_2_LOW_POWER_TRIAGE
                else:
                    data["degradation_tier"] = BatteryDegradationTier.TIER_3_EMERGENCY_SURVIVAL
                if "percentage" not in data:
                    # Estimate percentage for LiFePO4: 3.0V -> 0%, 3.4V -> 100%
                    pct = max(0.0, min(100.0, (voltage - 2.9) / (3.45 - 2.9) * 100.0))
                    data["percentage"] = round(pct, 1)
        return data


class GasMicroclimateData(BaseModel):
    """Bosch Sensortec BME688 MOX gas & ambient environmental telemetry."""
    temperature_c: float = Field(default=21.5, description="Ambient air temperature in Celsius")
    relative_humidity_pct: float = Field(default=42.0, ge=0.0, le=100.0, description="Relative humidity %")
    barometric_pressure_hpa: float = Field(default=1013.25, description="Barometric pressure in hPa")
    gas_resistance_ohms: float = Field(default=125000.0, ge=0.0, description="MOX surface resistance in Ohms")
    voc_index: float = Field(default=50.0, ge=0.0, description="VOC index (1-500 scale)")
    dln_rs_dt: float = Field(default=0.0, description="Logarithmic rate of change d(ln Rs)/dt in s^-1")


class ParticulateData(BaseModel):
    """Sensirion SPS30 laser scattering particulate matter telemetry."""
    pm1_0_ug_m3: float = Field(default=2.5, ge=0.0, description="PM1.0 mass concentration in ug/m3")
    pm2_5_ug_m3: float = Field(default=4.8, ge=0.0, description="PM2.5 mass concentration in ug/m3")
    pm4_0_ug_m3: float = Field(default=5.6, ge=0.0, description="PM4.0 mass concentration in ug/m3")
    pm10_0_ug_m3: float = Field(default=6.2, ge=0.0, description="PM10 mass concentration in ug/m3")
    typical_particle_size_um: float = Field(default=0.45, ge=0.0, description="Typical particle diameter in um")
    pm_ratio: Optional[float] = Field(default=None, description="Combustion diagnostic ratio PM2.5 / PM10")

    @model_validator(mode="after")
    def calculate_pm_ratio(self) -> "ParticulateData":
        if self.pm_ratio is None:
            if self.pm10_0_ug_m3 > 0.001:
                self.pm_ratio = round(self.pm2_5_ug_m3 / self.pm10_0_ug_m3, 4)
            else:
                self.pm_ratio = 0.0
        return self


class ThermalIRData(BaseModel):
    """Melexis MLX90640 32x24 Far-IR thermopile array telemetry."""
    thermal_max_temp_c: float = Field(default=22.8, description="Peak hotspot temperature in Celsius")
    thermal_ambient_temp_c: float = Field(default=21.5, description="Spatial background median in Celsius")
    thermal_gradient_c_per_sec: float = Field(default=0.05, description="Thermal divergence rate in C/s")
    thermal_plume_velocity_mm_s: float = Field(default=0.0, description="Convective centroid drift speed in mm/s")
    raw_grid: Optional[List[float]] = Field(default=None, description="Optional 768-pixel flattened IR array")


class AcousticData(BaseModel):
    """InvenSense INMP441 MEMS microphone acoustic cavitation classifier telemetry."""
    acoustic_crackle_event_rate_hz: float = Field(
        default=0.0, ge=0.0, description="Cell wall rupture micro-crackle rate in Hz"
    )
    acoustic_spectral_energy_ratio: float = Field(
        default=0.05, ge=0.0, le=1.0, description="Energy fraction in 1.5kHz-4.5kHz pyrolysis band"
    )
    acoustic_crackle_probability: float = Field(
        default=0.01, ge=0.0, le=1.0, description="Neural network INT8 crackle detection confidence"
    )


class TelemetryPacket(BaseModel):
    """Complete multi-modal sensor telemetry frame emitted by a SentryHive node."""
    node_id: str = Field(..., description="Unique node identifier e.g. 'NODE-A741'")
    timestamp: float = Field(default_factory=time.time, description="Unix timestamp in seconds")
    seq: int = Field(default=0, ge=0, description="Sequence packet counter")
    battery: BatteryMetrics = Field(default_factory=BatteryMetrics)
    gas: GasMicroclimateData = Field(default_factory=GasMicroclimateData)
    particulates: ParticulateData = Field(default_factory=ParticulateData)
    thermal: ThermalIRData = Field(default_factory=ThermalIRData)
    acoustic: AcousticData = Field(default_factory=AcousticData)
    
    # ML Fusion Verdict (computed on edge or verified by backend)
    fire_threat_index: float = Field(
        default=0.0, ge=0.0, le=1.0, description="Unified Fire Threat Index (FTI) 0.0 - 1.0"
    )
    alert_level: AlertLevel = Field(default=AlertLevel.NOMINAL, description="Threat classification")
    fallback_flags: int = Field(default=0, description="Edge fallback execution bitmask")

    @classmethod
    def create_sample(
        cls,
        node_id: str = "NODE-A741",
        temp_c: float = 22.0,
        pm2_5: float = 5.0,
        pm10: float = 7.0,
        voc_index: float = 50.0,
        thermal_max: float = 22.5,
        crackle_hz: float = 0.0,
        battery_v: float = 3.95,
    ) -> "TelemetryPacket":
        """Factory helper for generating synthetic packets."""
        return cls(
            node_id=node_id,
            battery=BatteryMetrics(voltage_v=battery_v),
            gas=GasMicroclimateData(
                temperature_c=temp_c,
                voc_index=voc_index,
                gas_resistance_ohms=120000.0 if voc_index < 100 else 18000.0,
            ),
            particulates=ParticulateData(
                pm2_5_ug_m3=pm2_5,
                pm10_0_ug_m3=pm10,
            ),
            thermal=ThermalIRData(
                thermal_max_temp_c=thermal_max,
                thermal_ambient_temp_c=temp_c,
            ),
            acoustic=AcousticData(
                acoustic_crackle_event_rate_hz=crackle_hz,
            ),
        )


class NodeRegistration(BaseModel):
    """Registration schema for onboarding a physical or virtual sensor node."""
    node_id: str = Field(..., min_length=3, max_length=32, description="Node hardware ID")
    name: str = Field(..., description="Human-readable node location name")
    coordinates: GeoCoordinates = Field(...)
    firmware_version: str = Field(default="v1.0.4-esp32s3", description="Firmware build tag")
    installed_at: float = Field(default_factory=time.time, description="Deployment timestamp")


class NodeStatus(BaseModel):
    """Live state of an operational SentryHive node."""
    node_id: str
    name: str
    coordinates: GeoCoordinates
    status: NodeConnectionStatus = NodeConnectionStatus.ONLINE
    battery_tier: BatteryDegradationTier = BatteryDegradationTier.TIER_0_FULL_NOMINAL
    battery_voltage: float = 3.95
    last_seen: float = Field(default_factory=time.time)
    packet_count: int = 0
    packet_loss_rate: float = 0.0
    latest_fti: float = 0.0
    latest_alert_level: AlertLevel = AlertLevel.NOMINAL
    rssi_dbm: float = -74.0
    snr_db: float = 9.5
    firmware_version: str = "v1.0.4-esp32s3"


class AlertRecord(BaseModel):
    """Dispatched wildfire alert event with spatial localization."""
    alert_id: str = Field(default_factory=lambda: f"ALT-{uuid.uuid4().hex[:8].upper()}")
    node_id: str
    level: AlertLevel
    severity_code: int = Field(..., ge=0, le=3)
    fire_threat_index: float = Field(..., ge=0.0, le=1.0)
    timestamp: float = Field(default_factory=time.time)
    coordinates: GeoCoordinates
    localized_polygon: List[List[float]] = Field(
        default_factory=list, description="GeoJSON coordinates array for perimeter polygon"
    )
    radius_meters: float = Field(default=250.0, description="Estimated alert boundary radius")
    evacuation_radius_meters: float = Field(default=1000.0, description="Evacuation buffer zone radius")
    triggering_modalities: List[str] = Field(
        default_factory=list, description="Active sensor modalities exceeding baseline"
    )
    description: str = Field(..., description="Actionable incident summary")
    dispatch_targets: List[str] = Field(
        default_factory=lambda: ["DASHBOARD_WEBSOCKET", "LORA_MESH_EMERGENCY", "INCIDENT_LOG"],
        description="Downstream channels notified"
    )
    status: str = Field(default="ACTIVE", description="ACTIVE, ACKNOWLEDGED, or RESOLVED")
    acknowledged_by: Optional[str] = None
    acknowledged_at: Optional[float] = None
    resolved_at: Optional[float] = None
    resolution_notes: Optional[str] = None


class RuleBasedEvaluation(BaseModel):
    """Result of naive single-variable threshold evaluation."""
    triggered: bool
    alert_level: AlertLevel
    violated_rules: List[str]
    rule_score: float = Field(..., ge=0.0, le=1.0)


class MultiModalEvaluation(BaseModel):
    """Result of TinyML multi-modal Bayesian fusion inference."""
    fire_threat_index: float = Field(..., ge=0.0, le=1.0)
    alert_level: AlertLevel
    gas_feature: float
    pm_feature: float
    thermal_feature: float
    acoustic_feature: float
    raw_logit: float
    inference_time_ms: float


class InferenceComparison(BaseModel):
    """A/B Benchmark comparison of Multi-Modal Fusion vs Simple Rule-Based."""
    sample_id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    multi_modal: MultiModalEvaluation
    rule_based: RuleBasedEvaluation
    agreement: bool
    false_positive_rejected: bool
    early_warning_advantage_s: float = Field(
        default=0.0, description="Estimated early warning lead time in seconds"
    )
    scenario: str
    explanation: str


class BenchmarkScenarioResult(BaseModel):
    """Result summary for a single scenario evaluated in the benchmark."""
    scenario_name: str
    description: str
    ground_truth: str
    multi_modal_verdict: AlertLevel
    multi_modal_fti: float
    rule_based_verdict: AlertLevel
    rule_based_triggered: bool
    correct_classification: bool
    false_alarm: bool
    missed_detection: bool
    notes: str


class BenchmarkReport(BaseModel):
    """Full A/B Benchmark report proving false positive rejection."""
    timestamp: float = Field(default_factory=time.time)
    total_scenarios: int
    multi_modal_accuracy_pct: float
    rule_based_accuracy_pct: float
    false_positive_rejection_pct: float
    results: List[BenchmarkScenarioResult]
    summary: str


class GeoJSONGeometry(BaseModel):
    type: str
    coordinates: Any


class GeoJSONFeature(BaseModel):
    type: str = "Feature"
    geometry: GeoJSONGeometry
    properties: Dict[str, Any]


class GeoJSONFeatureCollection(BaseModel):
    type: str = "FeatureCollection"
    features: List[GeoJSONFeature]
