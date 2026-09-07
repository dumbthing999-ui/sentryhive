import pytest
from simulation.scenarios import (
    NormalForestBaselineScenario,
    ControlledCampfireScenario,
    FalsePositiveDustStormScenario,
    SmolderingPeatWildfireScenario,
    ScenarioRunner
)
from backend.app.ml.fusion_engine import MultiModalFusionEngine
from backend.app.models import (
    TelemetryPacket,
    BatteryMetrics,
    GasMicroclimateData,
    ParticulateData,
    ThermalIRData,
    AcousticData,
    AlertLevel
)

def test_normal_baseline_scenario():
    scenario = NormalForestBaselineScenario()
    state = scenario.get_telemetry_modifier(100.0)
    assert state["is_fire"] is False
    assert state["pm2_5"] < 15.0
    assert state["voc_index"] < 100.0

def test_dust_storm_rejection_by_ai():
    """Verify that multi-modal TinyML rejects dust storm as non-wildfire despite high PM."""
    scenario = FalsePositiveDustStormScenario()
    dust_state = scenario.get_telemetry_modifier(60.0) # Full storm
    assert dust_state["pm10"] > 200.0 # High particulate
    
    engine = MultiModalFusionEngine()
    packet = TelemetryPacket(
        node_id="NODE-TEST",
        timestamp=1788700000,
        seq=1,
        battery=BatteryMetrics(
            voltage_v=3.95,
            percentage=92.0
        ),
        gas=GasMicroclimateData(
            temperature_c=22.0 + dust_state["temp_c_delta"],
            relative_humidity_pct=30.0 + dust_state["humidity_delta"],
            barometric_pressure_hpa=1013.2,
            gas_resistance_ohms=45000.0,
            voc_index=dust_state["voc_index"]
        ),
        particulates=ParticulateData(
            pm1_0_ug_m3=25.0,
            pm2_5_ug_m3=dust_state["pm2_5"],
            pm4_0_ug_m3=150.0,
            pm10_0_ug_m3=dust_state["pm10"],
            typical_particle_size_um=4.5 # Coarse dust
        ),
        thermal=ThermalIRData(
            thermal_max_temp_c=22.0 + dust_state["thermal_delta_c"],
            thermal_ambient_temp_c=22.0,
            thermal_gradient_c_per_sec=0.01,
            thermal_plume_velocity_mm_s=0.0
        ),
        acoustic=AcousticData(
            acoustic_crackle_event_rate_hz=dust_state["acoustic_hz"],
            acoustic_spectral_energy_ratio=0.02
        )
    )
    
    comp = engine.compare_inference(packet)
    # Naive single-sensor threshold triggers false alarm on PM2.5 > 35
    assert comp.rule_based.triggered is True
    # SentryHive TinyML correctly rejects false alarm
    assert comp.multi_modal.alert_level == AlertLevel.NOMINAL
    assert comp.multi_modal.fire_threat_index < 0.60
    assert comp.false_positive_rejected is True

def test_smoldering_wildfire_detection():
    """Verify that multi-modal TinyML triggers rapid alarm on smoldering ignition."""
    scenario = SmolderingPeatWildfireScenario()
    fire_state = scenario.get_telemetry_modifier(80.0)
    assert fire_state["is_fire"] is True
    
    engine = MultiModalFusionEngine()
    packet = TelemetryPacket(
        node_id="NODE-TEST",
        timestamp=1788700000,
        seq=2,
        battery=BatteryMetrics(
            voltage_v=3.90,
            percentage=88.0
        ),
        gas=GasMicroclimateData(
            temperature_c=25.0 + fire_state["temp_c_delta"],
            relative_humidity_pct=max(5.0, 50.0 + fire_state["humidity_delta"]),
            barometric_pressure_hpa=1012.0,
            gas_resistance_ohms=8000.0,
            voc_index=fire_state["voc_index"]
        ),
        particulates=ParticulateData(
            pm1_0_ug_m3=80.0,
            pm2_5_ug_m3=fire_state["pm2_5"],
            pm4_0_ug_m3=170.0,
            pm10_0_ug_m3=fire_state["pm10"],
            typical_particle_size_um=0.45 # Fine wood pyrolysis smoke
        ),
        thermal=ThermalIRData(
            thermal_max_temp_c=25.0 + fire_state["thermal_delta_c"],
            thermal_ambient_temp_c=25.0,
            thermal_gradient_c_per_sec=2.4,
            thermal_plume_velocity_mm_s=15.0
        ),
        acoustic=AcousticData(
            acoustic_crackle_event_rate_hz=fire_state["acoustic_hz"],
            acoustic_spectral_energy_ratio=0.88
        )
    )
    
    comp = engine.compare_inference(packet)
    assert comp.multi_modal.fire_threat_index > 0.80
    assert comp.multi_modal.alert_level in (AlertLevel.ADVISORY, AlertLevel.CRITICAL_EVACUATION)
