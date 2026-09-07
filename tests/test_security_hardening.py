import pytest
from starlette.testclient import TestClient
from backend.app.main import app

client = TestClient(app)

def test_security_reject_nan_infinity_coordinates():
    # Send non-numeric / malformed coordinates as raw JSON string
    raw_payload = '{"latitude": "not_a_number", "longitude": -120.14, "fire_intensity_mw": 25.0}'
    r = client.post(
        "/api/v1/simulation/ignite",
        content=raw_payload,
        headers={"Content-Type": "application/json"}
    )
    assert r.status_code == 422 # Unprocessable Entity

def test_security_reject_out_of_bounds_coordinates():
    # Latitude > 90
    bad_lat = {
        "latitude": 95.0,
        "longitude": -120.14,
        "fire_intensity_mw": 25.0
    }
    r = client.post("/api/v1/simulation/ignite", json=bad_lat)
    assert r.status_code == 422
    
    # Longitude > 180
    bad_lon = {
        "latitude": 39.0,
        "longitude": 185.0,
        "fire_intensity_mw": 25.0
    }
    r = client.post("/api/v1/simulation/ignite", json=bad_lon)
    assert r.status_code == 422

def test_security_reject_negative_physical_parameters():
    # Negative wind speed
    bad_wind = {
        "latitude": 39.18,
        "longitude": -120.14,
        "fire_intensity_mw": 25.0,
        "wind_speed_m_s": -15.0
    }
    r = client.post("/api/v1/simulation/ignite", json=bad_wind)
    assert r.status_code == 422

def test_security_safe_incident_report_sanitization():
    # Path traversal attempts are safely rejected with 404/400 by ASGI router
    r = client.get("/api/v1/incidents/..%2F..%2Fetc%2Fpasswd/report")
    assert r.status_code in (404, 400)

def test_security_fleet_scale_limits():
    # Exceed maximum node limit (> 100)
    oversized_fleet = {
        "node_count": 500,
        "center_latitude": 39.18,
        "center_longitude": -120.14
    }
    r = client.post("/api/v1/fleet/scale", json=oversized_fleet)
    assert r.status_code == 422
