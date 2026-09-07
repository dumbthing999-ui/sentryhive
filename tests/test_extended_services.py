import pytest
from starlette.testclient import TestClient
from backend.app.main import app
from backend.app.services.triangulation import TriangulationEngine
from backend.app.services.forecast import RiskForecastingEngine
from backend.app.services.fault_injection import FaultInjectionService
from backend.app.services.incident_manager import IncidentManager

client = TestClient(app)

def test_triangulation_service_no_anomaly():
    nodes = [
        {"node_id": "N1", "latitude": 39.18, "longitude": -120.14, "threat_index": 0.05, "alert_level": "NOMINAL"},
        {"node_id": "N2", "latitude": 39.19, "longitude": -120.13, "threat_index": 0.04, "alert_level": "NOMINAL"}
    ]
    res = TriangulationEngine.triangulate(nodes)
    assert res.is_active is False
    assert res.origin is None

def test_triangulation_service_with_fire_anomaly():
    nodes = [
        {"node_id": "N1", "latitude": 39.1820, "longitude": -120.1410, "threat_index": 0.94, "alert_level": "CRITICAL_EVACUATION", "thermal_gradient": 2.5},
        {"node_id": "N2", "latitude": 39.1860, "longitude": -120.1350, "threat_index": 0.88, "alert_level": "CRITICAL_EVACUATION", "thermal_gradient": 1.8},
        {"node_id": "N3", "latitude": 39.1790, "longitude": -120.1450, "threat_index": 0.12, "alert_level": "NOMINAL", "thermal_gradient": 0.02}
    ]
    res = TriangulationEngine.triangulate(nodes, wind_speed_m_s=5.0, wind_direction_deg=220.0)
    assert res.is_active is True
    assert res.origin is not None
    assert 39.18 <= res.origin.latitude <= 39.19
    assert -120.15 <= res.origin.longitude <= -120.13
    assert res.origin.reporting_nodes_count == 2
    assert "N1" in res.origin.contributing_node_ids
    assert res.spread is not None
    assert res.spread.velocity_m_per_s > 0.4
    assert res.spread.recommended_evacuation_azimuth_deg >= 0.0

def test_risk_forecasting_engine():
    forecast = RiskForecastingEngine.generate_forecast(
        current_threat_index=0.65,
        temp_c=28.0,
        rh_pct=18.0,
        wind_speed_m_s=5.5
    )
    assert len(forecast.forecast_points) == 3
    p15 = forecast.forecast_points[0]
    p30 = forecast.forecast_points[1]
    p60 = forecast.forecast_points[2]
    assert p15.horizon_minutes == 15
    assert p30.horizon_minutes == 30
    assert p60.horizon_minutes == 60
    assert p60.predicted_risk_probability >= p15.predicted_risk_probability
    assert forecast.atmospheric_vpd_kpa > 2.0 # Arid high risk

def test_fault_injection_service():
    fault_svc = FaultInjectionService()
    raw = {
        "temp_c": 24.0,
        "pm2_5": 12.0,
        "pm10": 18.0,
        "thermal_max": 25.5,
        "acoustic_hz": 0.2,
        "voc_idx": 45.0
    }
    
    # Baseline healthy
    t_clean, status_clean = fault_svc.apply_faults_to_telemetry(raw)
    assert status_clean.degraded_mode_active is False
    assert status_clean.overall_health_score == 0.98
    
    # Inject thermal sensor dropout
    fault_svc.inject_fault("thermal", "dropout")
    t_faulty, status_faulty = fault_svc.apply_faults_to_telemetry(raw)
    assert status_faulty.degraded_mode_active is True
    assert "THERMAL_DROPOUT" in status_faulty.active_faults
    assert t_faulty["thermal_gradient"] == 0.0
    assert status_faulty.sensors["thermal"].is_operational is False
    assert status_faulty.sensors["thermal"].attenuated_model_weight == 0.0

def test_incident_manager_lifecycle():
    mgr = IncidentManager()
    # Baseline - no incident
    inc0 = mgr.create_or_update_from_threat("NODE-1", 0.15, 39.18, -120.14)
    assert inc0 is None
    
    # Suspicious anomaly triggers incident creation
    inc1 = mgr.create_or_update_from_threat("NODE-1", 0.52, 39.18, -120.14, "Tahoe Sector Alpha")
    assert inc1 is not None
    assert inc1.state == "SUSPICIOUS"
    assert len(inc1.involved_nodes) == 1
    
    # Critical escalation
    inc2 = mgr.create_or_update_from_threat("NODE-2", 0.95, 39.182, -120.138, "Tahoe Sector Alpha")
    assert inc2.state == "CRITICAL"
    assert inc2.evacuation_order_issued is True
    assert len(inc2.involved_nodes) == 2
    assert inc2.peak_threat_index == 0.95
    
    # Verify audit report generated
    report = mgr.generate_forensic_markdown_report(inc2.incident_id)
    assert "SENTRYHIVE INCIDENT FORENSIC AUDIT REPORT" in report
    assert inc2.incident_id in report
    assert "CRITICAL" in report

def test_api_extended_endpoints():
    # 1. Spatial Triangulation
    r_tri = client.get("/api/v1/spatial/triangulate")
    assert r_tri.status_code == 200
    
    # 2. Risk Forecast
    r_fc = client.get("/api/v1/forecast/risk")
    assert r_fc.status_code == 200
    data_fc = r_fc.json()
    assert "forecast_points" in data_fc
    assert len(data_fc["forecast_points"]) == 3
    
    # 3. System Metrics
    r_met = client.get("/api/v1/metrics")
    assert r_met.status_code == 200
    data_met = r_met.json()
    assert "uptime_s" in data_met
    assert "mean_inference_latency_ms" in data_met
    
    # 4. Fault Injection & Clear
    r_inj = client.post("/api/v1/resilience/fault/inject?sensor=thermal&fault_mode=dropout")
    assert r_inj.status_code == 200
    r_clr = client.post("/api/v1/resilience/fault/clear")
    assert r_clr.status_code == 200
def test_incident_kml_export():
    from backend.app.services.incident_manager import incident_manager
    # Create incident
    inc = incident_manager.create_or_update_from_threat("NODE-TEST-KML", 0.92, 39.182, -120.141, "Tahoe Basin Test")
    assert inc is not None
    
    r = client.get(f"/api/v1/incidents/{inc.incident_id}/kml")
    assert r.status_code == 200
    assert "application/vnd.google-earth.kml+xml" in r.headers["content-type"]
    content = r.text
    assert "<?xml version=" in content
    assert "<kml" in content
    assert inc.incident_id in content
    assert "firePerimeter" in content
