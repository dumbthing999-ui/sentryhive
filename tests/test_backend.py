"""Comprehensive Test Suite for SentryHive Backend.

Tests:
1. Domain models & Pydantic validation (Battery tiers, PM ratio, GeoCoordinates)
2. Multi-Modal TinyML Fusion Engine (Modality features, sigmoid gating, FTI scoring)
3. A/B Benchmark comparisons (Dust storm / heatwave rejection, early smoldering warning)
4. Ingestion pipeline (JSON, Batch, CBOR, LoRa packed binary struct)
5. Alert dispatcher & Geospatial localization (Perimeter ellipses, lifecycle)
6. REST API endpoints via TestClient (Health, Telemetry, Fleet, Alerts, ML, GIS, Simulation)
7. WebSocket streaming endpoints (/ws/telemetry and /ws/ingest)
"""

from __future__ import annotations

import struct
import time
import pytest
from starlette.testclient import TestClient

from backend.app.alerts import alert_dispatcher
from backend.app.ingestion import ingestion_pipeline
from backend.app.main import app, _periodic_synthetic_drift_loop
from backend.app.ml.fusion_engine import fusion_engine
from backend.app.models import (
    AcousticData,
    AlertLevel,
    AlertRecord,
    BatteryDegradationTier,
    BatteryMetrics,
    GasMicroclimateData,
    GeoCoordinates,
    NodeConnectionStatus,
    NodeRegistration,
    ParticulateData,
    TelemetryPacket,
    ThermalIRData,
)


@pytest.fixture(autouse=True)
def clean_state():
    """Reset singleton state before every test."""
    alert_dispatcher.clear()
    yield
    alert_dispatcher.clear()


@pytest.fixture
def client():
    """Test client for FastAPI app with lifespan context."""
    with TestClient(app) as test_client:
        yield test_client


# ============================================================================
# 1. DOMAIN MODELS & VALIDATION TESTS
# ============================================================================

def test_battery_metrics_degradation_tiers():
    """Verify LiFePO4 degradation tier auto-selection based on terminal voltage."""
    # Tier 0: >= 3.30V
    b0 = BatteryMetrics(voltage_v=3.45)
    assert b0.degradation_tier == BatteryDegradationTier.TIER_0_FULL_NOMINAL
    assert b0.percentage == 100.0

    # Tier 1: 3.15V - 3.30V
    b1 = BatteryMetrics(voltage_v=3.22)
    assert b1.degradation_tier == BatteryDegradationTier.TIER_1_DUTY_CYCLED

    # Tier 2: 3.00V - 3.15V
    b2 = BatteryMetrics(voltage_v=3.05)
    assert b2.degradation_tier == BatteryDegradationTier.TIER_2_LOW_POWER_TRIAGE

    # Tier 3: < 3.00V
    b3 = BatteryMetrics(voltage_v=2.85)
    assert b3.degradation_tier == BatteryDegradationTier.TIER_3_EMERGENCY_SURVIVAL
    assert b3.percentage == 0.0


def test_particulate_ratio_auto_calculation():
    """Verify combustion diagnostic ratio (PM2.5 / PM10) auto-computes."""
    # Smoldering fine smoke
    p_smoke = ParticulateData(pm2_5_ug_m3=85.0, pm10_0_ug_m3=100.0)
    assert p_smoke.pm_ratio == 0.85

    # Coarse dust
    p_dust = ParticulateData(pm2_5_ug_m3=30.0, pm10_0_ug_m3=150.0)
    assert p_dust.pm_ratio == 0.20


def test_geocoordinates_bounds():
    """Verify latitude and longitude bounds validation."""
    valid_coords = GeoCoordinates(latitude=39.1823, longitude=-120.1412)
    assert valid_coords.latitude == 39.1823

    with pytest.raises(Exception):
        GeoCoordinates(latitude=95.0, longitude=-120.0)

    with pytest.raises(Exception):
        GeoCoordinates(latitude=39.0, longitude=195.0)


# ============================================================================
# 2. MULTI-MODAL ML FUSION ENGINE TESTS
# ============================================================================

def test_modality_1_gas_kinetics_evaluation():
    """Verify BME688 pyrolysis gas kinetics extractor."""
    # Baseline nominal air
    score_clean = fusion_engine.evaluate_gas_feature(
        voc_index=45.0, gas_res_ohms=150000.0, temp_c=22.0, rh_pct=40.0
    )
    assert score_clean <= 0.10

    # Elevated pyrolysis VOCs and steep resistance drop
    score_pyrolysis = fusion_engine.evaluate_gas_feature(
        voc_index=350.0, gas_res_ohms=12000.0, temp_c=25.0, rh_pct=30.0, dln_rs_dt=-0.15
    )
    assert score_pyrolysis >= 0.70


def test_modality_2_particulate_diagnostic_ratio():
    """Verify SPS30 combustion ratio distinguishes smoke from dust."""
    # Mineral dust storm: huge PM10 mass, but low PM2.5/PM10 ratio
    score_dust = fusion_engine.evaluate_particulate_feature(
        pm1_0=8.0, pm2_5=45.0, pm10_0=350.0
    )
    assert score_dust == 0.05  # Dampened / rejected

    # Vegetative pyrolysis smoke: fine fraction dominance
    score_smoke = fusion_engine.evaluate_particulate_feature(
        pm1_0=40.0, pm2_5=85.0, pm10_0=95.0
    )
    assert score_smoke >= 0.90


def test_modality_3_thermal_radiance():
    """Verify MLX90640 spatial gradient and hotspot divergence."""
    # Uniform midday heating (ambient 38C, max 39C -> delta 1C)
    score_sun = fusion_engine.evaluate_thermal_feature(
        thermal_max_c=39.0, thermal_ambient_c=38.0
    )
    assert score_sun == 0.0

    # Combustion hotspot (ambient 22C, max 45C -> delta 23C)
    score_hotspot = fusion_engine.evaluate_thermal_feature(
        thermal_max_c=45.0, thermal_ambient_c=22.0, gradient_c_per_sec=0.45
    )
    assert score_hotspot >= 0.95


def test_modality_4_acoustic_cavitation():
    """Verify INMP441 wood cell wall rupture micro-crackle detection."""
    # Ambient wind rustle (0 Hz crackles)
    score_wind = fusion_engine.evaluate_acoustic_feature(crackle_rate_hz=0.0)
    assert score_wind == 0.0

    # Active pyrolysis steam rupture (12 Hz crackles)
    score_rupture = fusion_engine.evaluate_acoustic_feature(
        crackle_rate_hz=12.0, spectral_ratio=0.65
    )
    assert score_rupture >= 0.85


def test_fusion_engine_nominal_baseline():
    """Verify nominal environmental state outputs low FTI and NOMINAL level."""
    packet = TelemetryPacket.create_sample(
        node_id="NODE-A741",
        temp_c=21.0,
        pm2_5=4.0,
        pm10=6.0,
        voc_index=40.0,
        thermal_max=21.5,
        crackle_hz=0.0,
    )
    eval_res = fusion_engine.evaluate_telemetry(packet)
    assert eval_res.fire_threat_index < 0.25
    assert eval_res.alert_level == AlertLevel.NOMINAL


def test_fusion_engine_smoldering_and_crown_fire():
    """Verify early smoldering triggers Advisory and crown fire triggers Critical."""
    # Early phase 0 smoldering
    smoldering = TelemetryPacket(
        node_id="NODE-B812",
        gas=GasMicroclimateData(temperature_c=24.0, voc_index=190.0, gas_resistance_ohms=20000.0),
        particulates=ParticulateData(pm1_0_ug_m3=20.0, pm2_5_ug_m3=32.0, pm10_0_ug_m3=36.0),
        thermal=ThermalIRData(thermal_max_temp_c=38.0, thermal_ambient_temp_c=24.0),
        acoustic=AcousticData(acoustic_crackle_event_rate_hz=7.5, acoustic_spectral_energy_ratio=0.55),
    )
    res_smolder = fusion_engine.evaluate_telemetry(smoldering)
    assert res_smolder.fire_threat_index >= 0.60
    assert res_smolder.alert_level in (AlertLevel.ADVISORY, AlertLevel.CRITICAL_EVACUATION)

    # Active crown fire
    crown = TelemetryPacket(
        node_id="NODE-B812",
        gas=GasMicroclimateData(temperature_c=45.0, voc_index=480.0, gas_resistance_ohms=6000.0),
        particulates=ParticulateData(pm1_0_ug_m3=110.0, pm2_5_ug_m3=180.0, pm10_0_ug_m3=200.0),
        thermal=ThermalIRData(thermal_max_temp_c=88.0, thermal_ambient_temp_c=45.0),
        acoustic=AcousticData(acoustic_crackle_event_rate_hz=25.0, acoustic_spectral_energy_ratio=0.85),
    )
    res_crown = fusion_engine.evaluate_telemetry(crown)
    assert res_crown.fire_threat_index >= 0.85
    assert res_crown.alert_level == AlertLevel.CRITICAL_EVACUATION


# ============================================================================
# 3. A/B BENCHMARK COMPARISONS
# ============================================================================

def test_ab_comparison_dust_storm_false_positive_rejection():
    """Verify multi-modal fusion rejects dust storms while simple thresholds fail."""
    dust_packet = TelemetryPacket(
        node_id="NODE-A741",
        gas=GasMicroclimateData(temperature_c=26.0, voc_index=50.0, gas_resistance_ohms=110000.0),
        particulates=ParticulateData(pm1_0_ug_m3=10.0, pm2_5_ug_m3=52.0, pm10_0_ug_m3=320.0),
        thermal=ThermalIRData(thermal_max_temp_c=26.5, thermal_ambient_temp_c=26.0),
        acoustic=AcousticData(acoustic_crackle_event_rate_hz=0.0),
    )
    comp = fusion_engine.compare_inference(dust_packet, scenario_name="Dust Storm Test")

    # Simple rule-based triggered because PM2.5 (52) > 35
    assert comp.rule_based.triggered is True
    # Multi-modal fusion recognized coarse ratio and no thermal/acoustic/gas
    assert comp.multi_modal.alert_level == AlertLevel.NOMINAL
    assert comp.false_positive_rejected is True


def test_ab_comparison_heatwave_false_positive_rejection():
    """Verify multi-modal fusion rejects hot summer afternoons."""
    heat_packet = TelemetryPacket(
        node_id="NODE-A741",
        gas=GasMicroclimateData(temperature_c=42.5, voc_index=55.0, gas_resistance_ohms=95000.0),
        particulates=ParticulateData(pm1_0_ug_m3=2.0, pm2_5_ug_m3=6.0, pm10_0_ug_m3=8.5),
        thermal=ThermalIRData(thermal_max_temp_c=43.0, thermal_ambient_temp_c=42.5),
        acoustic=AcousticData(acoustic_crackle_event_rate_hz=0.0),
    )
    comp = fusion_engine.compare_inference(heat_packet, scenario_name="Heatwave Test")

    assert comp.rule_based.triggered is True  # Temp > 40C
    assert comp.multi_modal.alert_level == AlertLevel.NOMINAL
    assert comp.false_positive_rejected is True


def test_ab_comparison_phase_0_early_warning():
    """Verify multi-modal fusion detects smoldering where simple thresholds miss."""
    smolder_packet = TelemetryPacket(
        node_id="NODE-D504",
        gas=GasMicroclimateData(temperature_c=24.0, voc_index=175.0, gas_resistance_ohms=22000.0),
        particulates=ParticulateData(pm1_0_ug_m3=18.0, pm2_5_ug_m3=28.0, pm10_0_ug_m3=31.0),
        thermal=ThermalIRData(thermal_max_temp_c=37.0, thermal_ambient_temp_c=24.0),
        acoustic=AcousticData(acoustic_crackle_event_rate_hz=6.5, acoustic_spectral_energy_ratio=0.52),
    )
    comp = fusion_engine.compare_inference(smolder_packet, scenario_name="Early Smoldering Test")

    # Simple rules didn't trigger: Temp < 40, PM2.5 < 35, VOC < 200, Gas Res > 20k
    assert comp.rule_based.triggered is False
    # Multi-modal fusion combined all 4 modalities and alerted
    assert comp.multi_modal.alert_level in (AlertLevel.WATCH, AlertLevel.ADVISORY, AlertLevel.CRITICAL_EVACUATION)
    assert comp.early_warning_advantage_s > 0.0


def test_benchmark_suite_execution():
    """Verify full benchmark report metrics and scenario results."""
    report = fusion_engine.run_benchmark_suite()
    assert report.total_scenarios >= 6
    assert report.multi_modal_accuracy_pct >= 80.0
    assert report.false_positive_rejection_pct >= 75.0
    assert len(report.results) == report.total_scenarios


# ============================================================================
# 4. INGESTION PIPELINE & BINARY DECODING TESTS
# ============================================================================

def test_single_packet_ingest():
    """Verify packet ingestion updates time-series buffer and node status."""
    import asyncio

    async def _run():
        packet = TelemetryPacket.create_sample(node_id="NODE-A741", temp_c=23.0)
        processed, alert = await ingestion_pipeline.ingest_packet(packet)

        assert processed.node_id == "NODE-A741"
        node = ingestion_pipeline.get_node("NODE-A741")
        assert node is not None
        assert node.packet_count >= 1

        history = ingestion_pipeline.get_history("NODE-A741", limit=10)
        assert len(history) >= 1
        assert history[-1].node_id == "NODE-A741"

    asyncio.run(_run())


def test_batch_packet_ingest():
    """Verify batch packet ingestion."""
    import asyncio

    async def _run():
        packets = [
            TelemetryPacket.create_sample(node_id="NODE-A741", temp_c=22.0),
            TelemetryPacket.create_sample(node_id="NODE-B812", temp_c=24.0),
        ]
        batch_result = await ingestion_pipeline.ingest_batch(packets)
        assert batch_result["ingested_count"] == 2
        assert "alerts_generated" in batch_result

    asyncio.run(_run())


def test_binary_lora_frame_roundtrip():
    """Verify serialization and deserialization of packed binary LoRa frame."""
    original = TelemetryPacket.create_sample(
        node_id="NODE-A741",
        temp_c=25.5,
        pm2_5=12.4,
        pm10=16.8,
        voc_index=60.0,
        thermal_max=26.0,
        crackle_hz=2.5,
        battery_v=3.90,
    )
    raw_bytes = ingestion_pipeline.encode_binary_telemetry(original)
    assert len(raw_bytes) == ingestion_pipeline.PACKET_STRUCT_SIZE

    decoded = ingestion_pipeline.decode_cbor_telemetry(raw_bytes)
    assert decoded.node_id == "NODE-A741"
    assert abs(decoded.gas.temperature_c - 25.5) < 0.1
    assert abs(decoded.particulates.pm2_5_ug_m3 - 12.4) < 0.1
    assert abs(decoded.acoustic.acoustic_crackle_event_rate_hz - 2.5) < 0.1
    assert abs(decoded.battery.voltage_v - 3.90) < 0.1


def test_cbor_packet_decoding():
    """Verify CBOR-encoded packet parsing."""
    import cbor2
    payload = {
        "node_id": "NODE-C399",
        "timestamp": 1726000000.0,
        "temp_c": 27.2,
        "rh_pct": 35.0,
        "pm2_5": 14.5,
        "pm10": 20.0,
        "voc_index": 80.0,
        "crackle_hz": 3.0,
        "battery_v": 3.85,
    }
    cbor_bytes = cbor2.dumps(payload)
    decoded = ingestion_pipeline.decode_cbor_telemetry(cbor_bytes)

    assert decoded.node_id == "NODE-C399"
    assert decoded.gas.temperature_c == 27.2
    assert decoded.particulates.pm2_5_ug_m3 == 14.5


def test_invalid_binary_frame_rejection():
    """Verify corrupted / truncated binary payload raises ValueError."""
    corrupted_bytes = b"\x01\x02\x03"
    with pytest.raises(ValueError):
        ingestion_pipeline.decode_cbor_telemetry(corrupted_bytes)


# ============================================================================
# 5. ALERT DISPATCHER & GEOSPATIAL TESTS
# ============================================================================

def test_alert_generation_and_escalation():
    """Verify alert generation, escalation, and geospatial polygon calculation."""
    coords = GeoCoordinates(latitude=39.1823, longitude=-120.1412)
    
    # 1. Watch level
    pkt_watch = TelemetryPacket(
        node_id="NODE-A741",
        fire_threat_index=0.45,
        alert_level=AlertLevel.WATCH,
        gas=GasMicroclimateData(voc_index=140.0),
        particulates=ParticulateData(pm2_5_ug_m3=20.0, pm10_0_ug_m3=28.0),
    )
    alert = alert_dispatcher.process_telemetry(pkt_watch, coords)
    assert alert is not None
    assert alert.level == AlertLevel.WATCH
    assert alert.severity_code == 1
    assert len(alert.localized_polygon) >= 24
    assert len(alert_dispatcher.get_active_alerts()) == 1

    # 2. Escalate to Critical
    pkt_crit = TelemetryPacket(
        node_id="NODE-A741",
        fire_threat_index=0.92,
        alert_level=AlertLevel.CRITICAL_EVACUATION,
        gas=GasMicroclimateData(voc_index=450.0),
        particulates=ParticulateData(pm2_5_ug_m3=120.0, pm10_0_ug_m3=140.0),
        thermal=ThermalIRData(thermal_max_temp_c=75.0, thermal_ambient_temp_c=25.0),
        acoustic=AcousticData(acoustic_crackle_event_rate_hz=18.0),
    )
    esc_alert = alert_dispatcher.process_telemetry(pkt_crit, coords)
    assert esc_alert is not None
    assert esc_alert.level == AlertLevel.CRITICAL_EVACUATION
    assert esc_alert.severity_code == 3
    assert "LOCAL_GPIO_SIREN_110DB" in esc_alert.dispatch_targets
    assert len(alert_dispatcher.get_active_alerts()) == 1


def test_alert_lifecycle_acknowledgment_and_resolution():
    """Verify human dispatcher acknowledgment and incident resolution."""
    coords = GeoCoordinates(latitude=39.1823, longitude=-120.1412)
    packet = TelemetryPacket(
        node_id="NODE-B812",
        fire_threat_index=0.75,
        alert_level=AlertLevel.ADVISORY,
    )
    alert = alert_dispatcher.process_telemetry(packet, coords)
    assert alert is not None
    assert alert.status == "ACTIVE"

    # Acknowledge
    ack = alert_dispatcher.acknowledge_alert(alert.alert_id, acknowledged_by="ChiefEngineer")
    assert ack is not None
    assert ack.status == "ACKNOWLEDGED"
    assert ack.acknowledged_by == "ChiefEngineer"

    # Resolve
    res = alert_dispatcher.resolve_alert(alert.alert_id, resolution_notes="Smoldering damped by crew")
    assert res is not None
    assert res.status == "RESOLVED"
    assert len(alert_dispatcher.get_active_alerts()) == 0
    assert len(alert_dispatcher.get_alert_history()) == 1


def test_alert_geojson_features():
    """Verify GeoJSON FeatureCollection generation."""
    coords = GeoCoordinates(latitude=39.1823, longitude=-120.1412)
    packet = TelemetryPacket(
        node_id="NODE-A741",
        fire_threat_index=0.88,
        alert_level=AlertLevel.CRITICAL_EVACUATION,
    )
    alert_dispatcher.process_telemetry(packet, coords)
    features = alert_dispatcher.to_geojson_features()

    assert len(features) == 2  # Point feature + Polygon perimeter feature
    types = {f.geometry.type for f in features}
    assert "Point" in types
    assert "Polygon" in types


# ============================================================================
# 6. REST API ENDPOINTS INTEGRATION TESTS
# ============================================================================

def test_api_health(client: TestClient):
    """Verify /health and /api/v1/health endpoints."""
    res = client.get("/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "healthy"
    assert "uptime_seconds" in data
    assert data["active_nodes_count"] >= 4

    res2 = client.get("/api/v1/health")
    assert res2.status_code == 200


def test_api_telemetry_single_ingest(client: TestClient):
    """Verify POST /api/v1/telemetry."""
    payload = {
        "node_id": "NODE-A741",
        "gas": {"temperature_c": 22.0, "voc_index": 50.0},
        "particulates": {"pm2_5_ug_m3": 5.0, "pm10_0_ug_m3": 8.0},
        "thermal": {"thermal_max_temp_c": 22.5, "thermal_ambient_temp_c": 22.0},
        "acoustic": {"acoustic_crackle_event_rate_hz": 0.0},
    }
    res = client.post("/api/v1/telemetry", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    assert data["packet"]["node_id"] == "NODE-A741"
    assert "fire_threat_index" in data["packet"]


def test_api_telemetry_batch_ingest(client: TestClient):
    """Verify POST /api/v1/telemetry/batch."""
    batch = [
        {"node_id": "NODE-A741", "gas": {"temperature_c": 22.0}},
        {"node_id": "NODE-B812", "gas": {"temperature_c": 23.0}},
    ]
    res = client.post("/api/v1/telemetry/batch", json=batch)
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    assert data["ingested_count"] == 2


def test_api_telemetry_cbor_binary_ingest(client: TestClient):
    """Verify POST /api/v1/telemetry/cbor with raw binary bytes."""
    packet = TelemetryPacket.create_sample(node_id="NODE-C399", temp_c=24.5)
    binary_payload = ingestion_pipeline.encode_binary_telemetry(packet)

    res = client.post(
        "/api/v1/telemetry/cbor",
        content=binary_payload,
        headers={"Content-Type": "application/octet-stream"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    assert data["packet"]["node_id"] == "NODE-C399"


def test_api_telemetry_latest_and_history(client: TestClient):
    """Verify GET /api/v1/telemetry/latest and history."""
    client.post(
        "/api/v1/telemetry",
        json={"node_id": "NODE-A741", "gas": {"temperature_c": 22.5}},
    )

    res_latest = client.get("/api/v1/telemetry/latest?node_id=NODE-A741")
    assert res_latest.status_code == 200
    data = res_latest.json()
    assert "NODE-A741" in data

    res_hist = client.get("/api/v1/telemetry/history?node_id=NODE-A741&limit=10")
    assert res_hist.status_code == 200
    assert isinstance(res_hist.json(), list)
    assert len(res_hist.json()) >= 1


def test_api_fleet_nodes(client: TestClient):
    """Verify GET /api/v1/nodes and POST /api/v1/nodes/register."""
    res = client.get("/api/v1/nodes")
    assert res.status_code == 200
    nodes = res.json()
    assert len(nodes) >= 4

    # Register new node
    new_node = {
        "node_id": "NODE-X999",
        "name": "Donner Summit Lookout",
        "coordinates": {
            "latitude": 39.3142,
            "longitude": -120.3275,
            "elevation_m": 2400.0,
            "canopy_coverage_pct": 55.0,
            "vegetation_type": "Subalpine Fir & Lodgepole Pine",
        },
    }
    reg_res = client.post("/api/v1/nodes/register", json=new_node)
    assert reg_res.status_code == 200
    assert reg_res.json()["node_id"] == "NODE-X999"

    # Detail lookup
    detail_res = client.get("/api/v1/nodes/NODE-X999")
    assert detail_res.status_code == 200
    assert detail_res.json()["name"] == "Donner Summit Lookout"


def test_api_alerts_endpoints(client: TestClient):
    """Verify alert listing, acknowledge, and resolve endpoints."""
    # Trigger an alert via critical telemetry
    critical_payload = {
        "node_id": "NODE-A741",
        "gas": {"temperature_c": 40.0, "voc_index": 450.0, "gas_resistance_ohms": 7000.0},
        "particulates": {"pm2_5_ug_m3": 120.0, "pm10_0_ug_m3": 140.0},
        "thermal": {"thermal_max_temp_c": 75.0, "thermal_ambient_temp_c": 40.0},
        "acoustic": {"acoustic_crackle_event_rate_hz": 20.0},
    }
    client.post("/api/v1/telemetry", json=critical_payload)

    # List active alerts
    alerts_res = client.get("/api/v1/alerts")
    assert alerts_res.status_code == 200
    active_alerts = alerts_res.json()
    assert len(active_alerts) >= 1
    target_alert = active_alerts[0]
    alert_id = target_alert["alert_id"]

    # Acknowledge
    ack_res = client.post(
        f"/api/v1/alerts/{alert_id}/acknowledge",
        json={"acknowledged_by": "OpsChief"},
    )
    assert ack_res.status_code == 200
    assert ack_res.json()["status"] == "ACKNOWLEDGED"

    # Resolve
    resolve_res = client.post(
        f"/api/v1/alerts/{alert_id}/resolve",
        json={"resolution_notes": "Suppression team neutralized burning snag"},
    )
    assert resolve_res.status_code == 200
    assert resolve_res.json()["status"] == "RESOLVED"


def test_api_ml_evaluate_and_benchmark(client: TestClient):
    """Verify POST /api/v1/ml/evaluate and /api/v1/ml/benchmark."""
    sample = {
        "node_id": "NODE-A741",
        "gas": {"temperature_c": 23.0, "voc_index": 180.0},
        "particulates": {"pm2_5_ug_m3": 30.0, "pm10_0_ug_m3": 34.0},
        "thermal": {"thermal_max_temp_c": 36.0, "thermal_ambient_temp_c": 23.0},
        "acoustic": {"acoustic_crackle_event_rate_hz": 7.0},
    }
    eval_res = client.post("/api/v1/ml/evaluate", json=sample)
    assert eval_res.status_code == 200
    comparison = eval_res.json()
    assert "multi_modal" in comparison
    assert "rule_based" in comparison
    assert "explanation" in comparison

    bench_res = client.post("/api/v1/ml/benchmark")
    assert bench_res.status_code == 200
    report = bench_res.json()
    assert report["total_scenarios"] >= 6
    assert "multi_modal_accuracy_pct" in report

    weights_res = client.get("/api/v1/ml/weights")
    assert weights_res.status_code == 200
    assert "weights" in weights_res.json()


def test_api_gis_features(client: TestClient):
    """Verify /api/v1/gis/features returns valid GeoJSON FeatureCollection."""
    res = client.get("/api/v1/gis/features")
    assert res.status_code == 200
    geojson = res.json()
    assert geojson["type"] == "FeatureCollection"
    assert isinstance(geojson["features"], list)
    assert len(geojson["features"]) >= 4  # At least 4 reference sensor nodes


def test_api_simulation_injection(client: TestClient):
    """Verify POST /api/v1/simulation/inject."""
    res = client.post("/api/v1/simulation/inject?node_id=NODE-B812&scenario=smoldering_pyrolysis")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "scenario_injected"
    assert data["alert_level"] in ("ADVISORY", "CRITICAL_EVACUATION")
    assert "ab_comparison" in data


# ============================================================================
# 7. WEBSOCKET TESTS
# ============================================================================

def test_websocket_dashboard_stream(client: TestClient):
    """Verify WebSocket /ws/telemetry handshake and ping/pong."""
    with client.websocket_connect("/ws/telemetry") as ws:
        handshake = ws.receive_json()
        assert handshake["event"] == "handshake"
        assert "nodes" in handshake
        assert "active_alerts" in handshake

        ws.send_text("ping")
        resp = ws.receive_text()
        assert resp == "pong"


def test_websocket_node_uplink_stream(client: TestClient):
    """Verify WebSocket /ws/ingest edge node uplink."""
    with client.websocket_connect("/ws/ingest") as ws:
        node_payload = {
            "node_id": "NODE-A741",
            "seq": 101,
            "gas": {"temperature_c": 22.0, "voc_index": 45.0},
            "particulates": {"pm2_5_ug_m3": 4.5, "pm10_0_ug_m3": 6.8},
            "thermal": {"thermal_max_temp_c": 22.5, "thermal_ambient_temp_c": 22.0},
            "acoustic": {"acoustic_crackle_event_rate_hz": 0.0},
        }
        ws.send_json(node_payload)
        ack = ws.receive_json()
        assert ack["status"] == "ack"
        assert ack["node_id"] == "NODE-A741"
        assert ack["seq"] == 101
        assert "fire_threat_index" in ack
