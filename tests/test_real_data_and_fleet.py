import pytest
from starlette.testclient import TestClient
from backend.app.main import app
from backend.app.providers.base import DataProvenanceType
from backend.app.providers.registry import provider_registry
from simulation.dynamic_fleet import dynamic_fleet_manager, VirtualFleetConfig, DynamicIgnitionRequest

client = TestClient(app)

@pytest.mark.asyncio
async def test_provider_registry_stations():
    stations = await provider_registry.get_all_stations()
    assert len(stations) >= 4
    networks = {s.network for s in stations}
    assert "USFS RAWS" in networks
    assert "NASA EOS Orbital Constellation" in networks
    assert "OpenAQ Global Mesh" in networks
    assert "National Ecological Observatory Network" in networks

@pytest.mark.asyncio
async def test_provider_registry_observations_provenance():
    observations = await provider_registry.get_unified_observations()
    assert len(observations) >= 4
    provenance_types = {obs.provenance for obs in observations}
    assert DataProvenanceType.SATELLITE in provenance_types
    assert DataProvenanceType.ECOLOGICAL in provenance_types
    assert DataProvenanceType.AIR_QUALITY in provenance_types
    
    # Check RAWS data structure
    raws_obs = next(o for o in observations if o.provider_name == "USFS RAWS")
    assert raws_obs.temperature_c is not None
    assert raws_obs.fuel_moisture_10hr_pct is not None
    assert raws_obs.wind_speed_m_s is not None

def test_api_real_data_endpoints():
    # 1. Stations
    r_st = client.get("/api/v1/providers/stations")
    assert r_st.status_code == 200
    stations = r_st.json()
    assert len(stations) >= 4
    
    # 2. Observations
    r_obs = client.get("/api/v1/providers/observations")
    assert r_obs.status_code == 200
    observations = r_obs.json()
    assert len(observations) >= 4
    for o in observations:
        assert "provenance" in o
        assert "data_quality_score" in o
        
    # 3. Provider Health Matrix
    r_h = client.get("/api/v1/providers/health")
    assert r_h.status_code == 200
    health = r_h.json()
    assert len(health) == 4

def test_dynamic_fleet_scaling():
    # Scale to 15 nodes
    r_scale = client.post("/api/v1/fleet/scale", json={"node_count": 15, "center_latitude": 39.182, "center_longitude": -120.141})
    assert r_scale.status_code == 200
    data = r_scale.json()
    assert data["node_count"] == 15
    assert len(data["nodes"]) == 15
    
    # Verify bounds
    for n in data["nodes"]:
        assert 38.0 <= n["latitude"] <= 40.0
        assert -121.0 <= n["longitude"] <= -119.0
        assert n["is_simulated"] is True

def test_interactive_click_to_ignite():
    # Clear prior ignitions
    client.delete("/api/v1/simulation/ignitions")
    
    # Trigger ignition at Lake Tahoe shoreline
    ign_payload = {
        "latitude": 39.1825,
        "longitude": -120.1415,
        "fire_intensity_mw": 35.0,
        "fuel_type": "Dense Conifer & Duff",
        "wind_speed_m_s": 5.2,
        "wind_direction_deg": 225.0
    }
    r_ign = client.post("/api/v1/simulation/ignite", json=ign_payload)
    assert r_ign.status_code == 200
    ign = r_ign.json()
    assert ign["intensity_mw"] == 35.0
    assert ign["plume_heading_deg"] == 45.0 # (225 + 180) % 360
    assert ign["affected_nodes_count"] >= 1
    
    # List active ignitions
    r_list = client.get("/api/v1/simulation/ignitions")
    assert r_list.status_code == 200
    assert len(r_list.json()) == 1
    
    # Extinguish
    r_del = client.delete("/api/v1/simulation/ignitions")
    assert r_del.status_code == 200
    assert len(client.get("/api/v1/simulation/ignitions").json()) == 0
@pytest.mark.asyncio
async def test_observation_sha256_cryptographic_chaining():
    observations = await provider_registry.get_unified_observations()
    assert len(observations) >= 4
    for obs in observations:
        assert obs.cryptographic_sha256_hash is not None
        assert len(obs.cryptographic_sha256_hash) == 64
        # Verify deterministic hash
        from backend.app.providers.integrity import compute_observation_hash
        expected = compute_observation_hash(obs.model_dump())
        assert obs.cryptographic_sha256_hash == expected
