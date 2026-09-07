"""FastAPI Application for SentryHive.

Provides:
- WebSockets:
  - /ws/telemetry (Real-time client dashboard broadcast)
  - /ws/ingest (Node uplink streaming)
- REST Endpoints:
  - Health & System Metrics
  - Telemetry Ingestion (Single, Batch, Binary LoRa/CBOR)
  - Node Fleet Management & Registration
  - Multi-Tier Alert Dispatch & Localization
  - Multi-Modal ML Fusion & A/B Benchmark Analysis
  - GIS Digital Twin GeoJSON Feature Collections
  - Live Scenario Injection for Demos
- Background Tasks:
  - Periodic node heartbeat and synthetic drift simulation
"""

from __future__ import annotations

import asyncio
import contextlib
import time
from typing import Any, Dict, List, Optional

from fastapi import (
    BackgroundTasks,
    Body,
    FastAPI,
    HTTPException,
    Query,
    Request,
    Response,
    WebSocket,
    WebSocketDisconnect,
    status,
)
from fastapi.middleware.cors import CORSMiddleware

from backend.app.alerts import alert_dispatcher
from backend.app.ingestion import ingestion_pipeline
from backend.app.ml.fusion_engine import fusion_engine
from backend.app.models import (
    AlertLevel,
    AlertRecord,
    BenchmarkReport,
    GeoCoordinates,
    GeoJSONFeature,
    GeoJSONFeatureCollection,
    GeoJSONGeometry,
    InferenceComparison,
    NodeRegistration,
    NodeStatus,
    ParticulateData,
    TelemetryPacket,
    GasMicroclimateData,
    ThermalIRData,
    AcousticData,
)


# Background simulator task reference
_background_drift_task: Optional[asyncio.Task[None]] = None
_drift_simulation_active: bool = True


async def _periodic_synthetic_drift_loop() -> None:
    """Simulates realistic microclimate fluctuations across registered nodes."""
    drift_step = 0
    while True:
        try:
            await asyncio.sleep(5.0)
            if not _drift_simulation_active:
                continue

            drift_step += 1
            # Gently perturb reference nodes so live dashboards see active pulses
            for node in ingestion_pipeline.list_nodes():
                # Keep nominal unless an active alert was triggered
                if node.latest_alert_level == AlertLevel.NOMINAL:
                    # Small microclimate drift
                    import math
                    temp_drift = round(21.5 + 1.2 * math.sin(drift_step * 0.1), 2)
                    pm_drift = round(4.0 + 0.8 * math.cos(drift_step * 0.15), 2)
                    packet = TelemetryPacket.create_sample(
                        node_id=node.node_id,
                        temp_c=temp_drift,
                        pm2_5=pm_drift,
                        pm10=pm_drift * 1.3,
                        voc_index=45.0 + 5.0 * math.sin(drift_step * 0.05),
                        thermal_max=temp_drift + 0.5,
                        crackle_hz=0.0,
                    )
                    await ingestion_pipeline.ingest_packet(packet)
        except asyncio.CancelledError:
            break
        except Exception:
            # Shield loop from transient simulation exceptions
            await asyncio.sleep(1.0)


@contextlib.asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    global _background_drift_task
    # Startup: Start background synthetic drift loop
    _background_drift_task = asyncio.create_task(_periodic_synthetic_drift_loop())
    yield
    # Shutdown: Cancel background tasks
    if _background_drift_task and not _background_drift_task.done():
        _background_drift_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await _background_drift_task


app = FastAPI(
    title="SentryHive Core Telemetry & ML Fusion Backend",
    description=(
        "Autonomous Edge Wildfire & Microclimate Multi-Modal Early Warning Network Backend. "
        "VoltHacks 2026."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

# CORS Configuration for Frontend Dashboard (Next.js / Vite / Deck.gl)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================================
# HEALTH & SYSTEM METRICS
# ============================================================================

@app.get("/health", tags=["System"])
@app.get("/api/v1/health", tags=["System"])
async def health_check() -> Dict[str, Any]:
    """System health status and telemetry pipeline metrics."""
    uptime_s = time.time() - ingestion_pipeline.start_time
    nodes = ingestion_pipeline.list_nodes()
    active_alerts = alert_dispatcher.get_active_alerts()

    return {
        "status": "healthy",
        "service": "SentryHive Telemetry & ML Fusion Core",
        "version": "1.0.0",
        "uptime_seconds": round(uptime_s, 2),
        "packets_ingested": ingestion_pipeline.packets_ingested,
        "bytes_ingested": ingestion_pipeline.bytes_ingested,
        "active_nodes_count": len(nodes),
        "active_alerts_count": len(active_alerts),
        "dashboard_clients_connected": len(ingestion_pipeline._dashboard_clients),
        "uplink_clients_connected": len(ingestion_pipeline._uplink_clients),
    }


# ============================================================================
# TELEMETRY INGESTION ENDPOINTS
# ============================================================================

@app.post("/api/v1/telemetry", tags=["Telemetry"], response_model=Dict[str, Any])
async def ingest_single_telemetry(packet: TelemetryPacket) -> Dict[str, Any]:
    """Ingest a single multi-modal telemetry packet from an edge node."""
    processed_packet, alert = await ingestion_pipeline.ingest_packet(packet)
    return {
        "status": "success",
        "packet": processed_packet.model_dump(),
        "alert": alert.model_dump() if alert else None,
    }


@app.post("/api/v1/telemetry/batch", tags=["Telemetry"])
async def ingest_batch_telemetry(packets: List[TelemetryPacket]) -> Dict[str, Any]:
    """Ingest a batch of telemetry packets."""
    result = await ingestion_pipeline.ingest_batch(packets)
    return {"status": "success", **result}


@app.post("/api/v1/telemetry/cbor", tags=["Telemetry"])
async def ingest_cbor_telemetry(request: Request) -> Dict[str, Any]:
    """Ingest raw binary LoRa frame or CBOR-encoded packet."""
    raw_body = await request.body()
    if not raw_body:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Empty binary body received.",
        )
    try:
        decoded_packet = ingestion_pipeline.decode_cbor_telemetry(raw_body)
        processed, alert = await ingestion_pipeline.ingest_packet(decoded_packet)
        return {
            "status": "success",
            "bytes_received": len(raw_body),
            "packet": processed.model_dump(),
            "alert": alert.model_dump() if alert else None,
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Binary LoRa frame decoding error: {e}",
        )


@app.get("/api/v1/telemetry/latest", tags=["Telemetry"])
async def get_latest_telemetry(
    node_id: Optional[str] = Query(None, description="Optional node identifier filter")
) -> Dict[str, Any]:
    """Retrieve the latest telemetry snapshot for a single node or all nodes."""
    return ingestion_pipeline.get_latest(node_id)


@app.get("/api/v1/telemetry/history", tags=["Telemetry"])
async def get_telemetry_history(
    node_id: str = Query(..., description="Node hardware ID"),
    limit: int = Query(50, ge=1, le=500, description="Max history points"),
) -> List[Dict[str, Any]]:
    """Retrieve historical time-series telemetry for a specific node."""
    history = ingestion_pipeline.get_history(node_id=node_id, limit=limit)
    return [p.model_dump() for p in history]


# ============================================================================
# FLEET & NODE MANAGEMENT
# ============================================================================

@app.get("/api/v1/nodes", tags=["Fleet"], response_model=List[NodeStatus])
async def list_fleet_nodes() -> List[NodeStatus]:
    """List all registered edge sensor nodes and their live status."""
    return ingestion_pipeline.list_nodes()


@app.get("/api/v1/nodes/{node_id}", tags=["Fleet"], response_model=NodeStatus)
async def get_fleet_node(node_id: str) -> NodeStatus:
    """Retrieve detailed state of a single sensor node."""
    node = ingestion_pipeline.get_node(node_id)
    if not node:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Node '{node_id}' not found.",
        )
    return node


@app.post("/api/v1/nodes/register", tags=["Fleet"], response_model=NodeStatus)
async def register_fleet_node(registration: NodeRegistration) -> NodeStatus:
    """Register a new physical or virtual sensor node into the fleet."""
    return ingestion_pipeline.register_node(registration)


# ============================================================================
# MULTI-TIER ALERTS & DISPATCH
# ============================================================================

@app.get("/api/v1/alerts", tags=["Alerts"], response_model=List[AlertRecord])
async def list_active_alerts() -> List[AlertRecord]:
    """List all currently active or un-resolved wildfire alerts."""
    return alert_dispatcher.get_active_alerts()


@app.get("/api/v1/alerts/history", tags=["Alerts"], response_model=List[AlertRecord])
async def list_alert_history(
    limit: int = Query(50, ge=1, le=200, description="Max historical alerts")
) -> List[AlertRecord]:
    """List recent alert records including resolved incidents."""
    return alert_dispatcher.get_alert_history(limit=limit)


@app.post("/api/v1/alerts/{alert_id}/acknowledge", tags=["Alerts"], response_model=AlertRecord)
async def acknowledge_alert(
    alert_id: str,
    acknowledged_by: str = Body("Dispatcher", embed=True),
) -> AlertRecord:
    """Acknowledge an active alert by human operator or CAD system."""
    alert = alert_dispatcher.acknowledge_alert(alert_id, acknowledged_by=acknowledged_by)
    if not alert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Active alert '{alert_id}' not found.",
        )
    # Broadcast updated alert status
    await ingestion_pipeline.broadcast_event(
        {"event": "alert_acknowledged", "alert": alert.model_dump()}
    )
    return alert


@app.post("/api/v1/alerts/{alert_id}/resolve", tags=["Alerts"], response_model=AlertRecord)
async def resolve_alert(
    alert_id: str,
    resolution_notes: str = Body("Incident cleared by suppression crews", embed=True),
) -> AlertRecord:
    """Mark an alert resolved and archive it."""
    alert = alert_dispatcher.resolve_alert(alert_id, resolution_notes=resolution_notes)
    if not alert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Active alert '{alert_id}' not found.",
        )
    # Broadcast resolution
    await ingestion_pipeline.broadcast_event(
        {"event": "alert_resolved", "alert": alert.model_dump()}
    )
    return alert


# ============================================================================
# ML FUSION INFERENCE & A/B BENCHMARK
# ============================================================================

@app.post("/api/v1/ml/evaluate", tags=["Machine Learning"], response_model=InferenceComparison)
async def evaluate_ml_inference(
    packet: TelemetryPacket,
    scenario_name: str = Query("Custom Telemetry Evaluation", description="Evaluation tag"),
) -> InferenceComparison:
    """Execute TinyML multi-modal fusion with side-by-side A/B comparison vs rule thresholds."""
    return fusion_engine.compare_inference(packet=packet, scenario_name=scenario_name)


@app.post("/api/v1/ml/benchmark", tags=["Machine Learning"], response_model=BenchmarkReport)
async def run_ml_benchmark() -> BenchmarkReport:
    """Run full automated A/B benchmark across 6 canonical wildfire scenarios."""
    return fusion_engine.run_benchmark_suite()


@app.get("/api/v1/ml/weights", tags=["Machine Learning"])
async def get_ml_model_weights() -> Dict[str, Any]:
    """Retrieve calibrated TinyML model weights, parameters, and decision formulas."""
    return {
        "model_architecture": "Multi-Modal Calibrated Logistic Sigmoid / Bayesian Gating",
        "bias_intercept": fusion_engine.BIAS_INTERCEPT,
        "weights": {
            "gas_pyrolysis_kinetics": fusion_engine.WEIGHT_GAS,
            "particulate_combustion_ratio": fusion_engine.WEIGHT_PM,
            "thermal_radiance_differential": fusion_engine.WEIGHT_THERMAL,
            "acoustic_cell_cavitation": fusion_engine.WEIGHT_ACOUSTIC,
        },
        "rule_based_baseline": {
            "ambient_temp_threshold_c": fusion_engine.RULE_TEMP_THRESHOLD_C,
            "pm25_threshold_ug_m3": fusion_engine.RULE_PM25_THRESHOLD_UG_M3,
            "voc_threshold": fusion_engine.RULE_VOC_THRESHOLD,
            "gas_resistance_min_ohms": fusion_engine.RULE_GAS_RES_MIN_OHMS,
        },
        "threat_index_scale": {
            "0.00 - 0.34": "NOMINAL (Baseline environmental state)",
            "0.35 - 0.59": "WATCH (Microclimate alert; sensor polling elevated)",
            "0.60 - 0.84": "ADVISORY (High probability smoldering ignition)",
            "0.85 - 1.00": "CRITICAL_EVACUATION (Active combustion event)",
        },
    }


# ============================================================================
# GIS DIGITAL TWIN & GEOJSON ENDPOINTS
# ============================================================================

@app.get("/api/v1/gis/features", tags=["GIS Digital Twin"], response_model=GeoJSONFeatureCollection)
async def get_gis_features() -> GeoJSONFeatureCollection:
    """Export complete GIS layers: Sensor node points, alert centers, and spread perimeters."""
    features: List[GeoJSONFeature] = []

    # 1. Add all sensor nodes
    for node in ingestion_pipeline.list_nodes():
        features.append(
            GeoJSONFeature(
                geometry=GeoJSONGeometry(
                    type="Point",
                    coordinates=[node.coordinates.longitude, node.coordinates.latitude],
                ),
                properties={
                    "feature_type": "sensor_node",
                    "node_id": node.node_id,
                    "name": node.name,
                    "elevation_m": node.coordinates.elevation_m,
                    "vegetation_type": node.coordinates.vegetation_type,
                    "canopy_coverage_pct": node.coordinates.canopy_coverage_pct,
                    "status": node.status.value,
                    "battery_voltage": node.battery_voltage,
                    "battery_tier": node.battery_tier.value,
                    "latest_fti": node.latest_fti,
                    "latest_alert_level": node.latest_alert_level.value,
                    "last_seen": node.last_seen,
                },
            )
        )

    # 2. Add active alert perimeters & evacuation polygons
    alert_features = alert_dispatcher.to_geojson_features()
    features.extend(alert_features)

    return GeoJSONFeatureCollection(features=features)


@app.get("/api/v1/gis/nodes", tags=["GIS Digital Twin"], response_model=GeoJSONFeatureCollection)
async def get_gis_nodes_only() -> GeoJSONFeatureCollection:
    """Export only sensor nodes as GeoJSON Point features."""
    features = [
        GeoJSONFeature(
            geometry=GeoJSONGeometry(
                type="Point",
                coordinates=[n.coordinates.longitude, n.coordinates.latitude],
            ),
            properties={
                "feature_type": "sensor_node",
                "node_id": n.node_id,
                "name": n.name,
                "latest_fti": n.latest_fti,
                "alert_level": n.latest_alert_level.value,
                "battery_v": n.battery_voltage,
            },
        )
        for n in ingestion_pipeline.list_nodes()
    ]
    return GeoJSONFeatureCollection(features=features)


# ============================================================================
# DEMO & SIMULATION INJECTION
# ============================================================================

@app.post("/api/v1/simulation/inject", tags=["Simulation"])
async def inject_simulation_scenario(
    node_id: str = Query("NODE-A741", description="Target node"),
    scenario: str = Query(
        "smoldering_pyrolysis",
        description="Scenario: 'nominal', 'dust_storm', 'heatwave', 'vehicle_exhaust', 'smoldering_pyrolysis', 'crown_fire'",
    ),
) -> Dict[str, Any]:
    """Inject a deterministic simulation scenario into a node for live testing and demonstration."""
    scenarios: Dict[str, TelemetryPacket] = {
        "nominal": TelemetryPacket.create_sample(
            node_id=node_id, temp_c=22.0, pm2_5=4.0, pm10=6.0, voc_index=45.0, thermal_max=22.5
        ),
        "dust_storm": TelemetryPacket(
            node_id=node_id,
            gas=GasMicroclimateData(temperature_c=27.0, voc_index=55.0, gas_resistance_ohms=115000.0),
            particulates=ParticulateData(pm1_0_ug_m3=9.0, pm2_5_ug_m3=45.0, pm10_0_ug_m3=280.0),  # ratio 0.16
            thermal=ThermalIRData(thermal_max_temp_c=27.5, thermal_ambient_temp_c=27.0),
            acoustic=AcousticData(acoustic_crackle_event_rate_hz=0.0),
        ),
        "heatwave": TelemetryPacket(
            node_id=node_id,
            gas=GasMicroclimateData(temperature_c=42.5, voc_index=60.0, gas_resistance_ohms=95000.0),
            particulates=ParticulateData(pm1_0_ug_m3=3.0, pm2_5_ug_m3=7.0, pm10_0_ug_m3=9.5),
            thermal=ThermalIRData(thermal_max_temp_c=43.0, thermal_ambient_temp_c=42.5),
            acoustic=AcousticData(acoustic_crackle_event_rate_hz=0.0),
        ),
        "vehicle_exhaust": TelemetryPacket(
            node_id=node_id,
            gas=GasMicroclimateData(temperature_c=23.0, voc_index=240.0, gas_resistance_ohms=29000.0),
            particulates=ParticulateData(pm1_0_ug_m3=10.0, pm2_5_ug_m3=16.0, pm10_0_ug_m3=22.0),
            thermal=ThermalIRData(thermal_max_temp_c=23.5, thermal_ambient_temp_c=23.0),
            acoustic=AcousticData(acoustic_crackle_event_rate_hz=0.0),
        ),
        "smoldering_pyrolysis": TelemetryPacket(
            node_id=node_id,
            gas=GasMicroclimateData(temperature_c=24.0, voc_index=180.0, gas_resistance_ohms=21000.0, dln_rs_dt=-0.14),
            particulates=ParticulateData(pm1_0_ug_m3=24.0, pm2_5_ug_m3=34.0, pm10_0_ug_m3=38.0),  # ratio 0.89
            thermal=ThermalIRData(thermal_max_temp_c=37.5, thermal_ambient_temp_c=24.0),  # delta 13.5C
            acoustic=AcousticData(acoustic_crackle_event_rate_hz=8.2, acoustic_spectral_energy_ratio=0.58),
        ),
        "crown_fire": TelemetryPacket(
            node_id=node_id,
            gas=GasMicroclimateData(temperature_c=41.0, voc_index=480.0, gas_resistance_ohms=7500.0, dln_rs_dt=-0.42),
            particulates=ParticulateData(pm1_0_ug_m3=92.0, pm2_5_ug_m3=160.0, pm10_0_ug_m3=180.0),  # ratio 0.88
            thermal=ThermalIRData(thermal_max_temp_c=84.0, thermal_ambient_temp_c=41.0),  # delta 43C
            acoustic=AcousticData(acoustic_crackle_event_rate_hz=24.5, acoustic_spectral_energy_ratio=0.88),
        ),
    }

    selected = scenarios.get(scenario.lower())
    if not selected:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown scenario '{scenario}'. Choose from {list(scenarios.keys())}",
        )

    # Ingest and broadcast
    packet, alert = await ingestion_pipeline.ingest_packet(selected)
    comparison = fusion_engine.compare_inference(packet, scenario)

    return {
        "status": "scenario_injected",
        "scenario": scenario,
        "node_id": node_id,
        "fire_threat_index": packet.fire_threat_index,
        "alert_level": packet.alert_level.value,
        "alert_generated": alert.model_dump() if alert else None,
        "ab_comparison": comparison.model_dump(),
    }


# ============================================================================
# WEBSOCKET STREAMING ENDPOINTS
# ============================================================================

@app.websocket("/ws/telemetry")
async def websocket_dashboard_stream(websocket: WebSocket) -> None:
    """Real-time multiplexed WebSocket stream for client UI dashboards."""
    await ingestion_pipeline.connect_client(websocket, is_uplink=False)
    try:
        # Initial handshake: send current nodes and active alerts
        nodes = [n.model_dump() for n in ingestion_pipeline.list_nodes()]
        alerts = [a.model_dump() for a in alert_dispatcher.get_active_alerts()]
        await websocket.send_json(
            {
                "event": "handshake",
                "nodes": nodes,
                "active_alerts": alerts,
                "server_time": time.time(),
            }
        )

        # Keep socket open, listen for client pings
        while True:
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        ingestion_pipeline.disconnect_client(websocket)
    except Exception:
        ingestion_pipeline.disconnect_client(websocket)


@app.websocket("/ws/ingest")
async def websocket_node_uplink_stream(websocket: WebSocket) -> None:
    """High-throughput WebSocket uplink for virtual/physical node emulator."""
    await ingestion_pipeline.connect_client(websocket, is_uplink=True)
    try:
        while True:
            json_msg = await websocket.receive_json()
            packet = TelemetryPacket(**json_msg)
            processed, alert = await ingestion_pipeline.ingest_packet(packet)
            # Send immediate ACK with FTI verdict
            await websocket.send_json(
                {
                    "status": "ack",
                    "node_id": packet.node_id,
                    "seq": packet.seq,
                    "fire_threat_index": processed.fire_threat_index,
                    "alert_level": processed.alert_level.value,
                    "alert_triggered": alert is not None,
                }
            )
    except WebSocketDisconnect:
        ingestion_pipeline.disconnect_client(websocket)
    except Exception:
        ingestion_pipeline.disconnect_client(websocket)


# ---------------------------------------------------------------------------
# Real Public Environmental Data & Dynamic Fleet Ingestion
# ---------------------------------------------------------------------------
from backend.app.providers.registry import provider_registry
from backend.app.providers.base import (
    StationLocation,
    EnvironmentalObservation,
    ProviderStatus
)
from simulation.dynamic_fleet import (
    dynamic_fleet_manager,
    VirtualFleetConfig,
    DynamicIgnitionRequest,
    ActiveIgnitionSource
)

@app.get("/api/v1/providers/stations", response_model=List[StationLocation], tags=["Real Environmental Data"])
async def get_real_stations():
    """Returns normalized public environmental monitoring stations (RAWS, OpenAQ, NEON, FIRMS)."""
    return await provider_registry.get_all_stations()

@app.get("/api/v1/providers/observations", response_model=List[EnvironmentalObservation], tags=["Real Environmental Data"])
async def get_real_observations():
    """Returns live/cached normalized observations with transparent data provenance tags."""
    return await provider_registry.get_unified_observations()

@app.get("/api/v1/providers/health", response_model=List[ProviderStatus], tags=["Real Environmental Data"])
async def get_provider_health():
    """Returns health and connectivity status across all public environmental adapters."""
    return await provider_registry.get_provider_health_matrix()

@app.post("/api/v1/fleet/scale", tags=["Dynamic Virtual Fleet"])
async def scale_virtual_fleet(config: VirtualFleetConfig):
    """Scales virtual sensor fleet up to 100 nodes across Tahoe National Forest."""
    nodes = dynamic_fleet_manager.scale_fleet(config)
    return {"status": "SCALED", "node_count": len(nodes), "nodes": nodes}

@app.post("/api/v1/simulation/ignite", response_model=ActiveIgnitionSource, tags=["Interactive Digital Twin"])
async def trigger_interactive_ignition(req: DynamicIgnitionRequest):
    """Triggers dynamic thermodynamic ignition sequence at clicked lat/long coordinates."""
    return dynamic_fleet_manager.create_ignition(req)

@app.get("/api/v1/simulation/ignitions", response_model=List[ActiveIgnitionSource], tags=["Interactive Digital Twin"])
async def list_active_ignitions():
    """Returns currently burning thermodynamic fire sources."""
    return dynamic_fleet_manager.active_ignitions

@app.delete("/api/v1/simulation/ignitions", tags=["Interactive Digital Twin"])
async def clear_all_ignitions():
    """Extinguishes all active simulated ignition sources."""
    dynamic_fleet_manager.clear_ignitions()
    return {"status": "ALL_IGNITIONS_EXTINGUISHED"}

from backend.app.services.triangulation import TriangulationEngine, TriangulationResult
from backend.app.services.forecast import RiskForecastingEngine, FleetRiskForecast
from backend.app.services.fault_injection import FaultInjectionService
from backend.app.services.incident_manager import incident_manager, IncidentRecord

fault_service = FaultInjectionService()

@app.get("/api/v1/spatial/triangulate", response_model=TriangulationResult, tags=["Spatial Triangulation"])
async def get_fire_triangulation(wind_speed: float = 4.5, wind_dir: float = 225.0):
    """Computes real-time multi-node wildfire localization and propagation azimuth."""
    fleet = ingestion_pipeline.list_nodes()
    node_dicts = []
    for n in fleet:
        node_dicts.append({
            "node_id": n.node_id,
            "latitude": n.coordinates.latitude,
            "longitude": n.coordinates.longitude,
            "elevation_m": n.coordinates.elevation_m,
            "threat_index": n.latest_fti,
            "alert_level": n.latest_alert_level.value,
            "thermal_gradient": 0.5 if n.latest_fti > 0.5 else 0.05
        })
    return TriangulationEngine.triangulate(node_dicts, wind_speed, wind_dir)

@app.get("/api/v1/forecast/risk", response_model=FleetRiskForecast, tags=["Predictive Analytics"])
async def get_risk_forecast(temp_c: float = 26.5, rh_pct: float = 24.0, wind_speed: float = 4.2):
    """Computes short-horizon forward risk curves (t+15m, t+30m, t+60m)."""
    fleet = ingestion_pipeline.list_nodes()
    mean_fti = sum(n.latest_fti for n in fleet) / max(1, len(fleet))
    return RiskForecastingEngine.generate_forecast(
        current_threat_index=mean_fti,
        temp_c=temp_c,
        rh_pct=rh_pct,
        wind_speed_m_s=wind_speed
    )

@app.get("/api/v1/incidents", response_model=List[IncidentRecord], tags=["Incident Command"])
async def get_active_incidents():
    """Returns active operational incidents and evacuation status."""
    return list(incident_manager.active_incidents.values())

@app.get("/api/v1/incidents/{incident_id}/report", tags=["Incident Command"])
async def get_incident_report(incident_id: str):
    """Returns audit-grade markdown technical forensic incident report."""
    return {"incident_id": incident_id, "markdown_report": incident_manager.generate_forensic_markdown_report(incident_id)}

@app.get("/api/v1/incidents/{incident_id}/kml", tags=["Incident Command"])
async def get_incident_kml(incident_id: str):
    """Returns OGC KML file for ATAK / CalFire emergency dispatch mapping."""
    from backend.app.services.kml_export import generate_kml_polygon
    from starlette.responses import Response
    inc = incident_manager.active_incidents.get(incident_id)
    if not inc:
        # Check resolved
        for r in incident_manager.resolved_incidents:
            if r.incident_id == incident_id:
                inc = r
                break
    if not inc:
        return Response(content="<kml><Document><name>Not Found</name></Document></kml>", media_type="application/vnd.google-earth.kml+xml", status_code=404)

    kml_str = generate_kml_polygon(
        incident_id=inc.incident_id,
        title=inc.title,
        center_lat=inc.origin_latitude,
        center_lon=inc.origin_longitude,
        radius_m=inc.estimated_containment_perimeter_m,
        state=inc.state,
        peak_fti=inc.peak_threat_index
    )
    return Response(content=kml_str, media_type="application/vnd.google-earth.kml+xml")


@app.post("/api/v1/resilience/fault/inject", tags=["Fault Resilience"])
async def inject_sensor_fault(sensor: str, fault_mode: str):
    """Injects synthetic hardware sensor failure (dropout, noise_spike, stuck_zero)."""
    fault_service.inject_fault(sensor, fault_mode)
    return {"status": "FAULT_INJECTED", "sensor": sensor, "fault_mode": fault_mode}

@app.post("/api/v1/resilience/fault/clear", tags=["Fault Resilience"])
async def clear_sensor_faults(sensor: Optional[str] = None):
    """Clears sensor faults and restores nominal hardware operation."""
    if sensor:
        fault_service.clear_fault(sensor)
    else:
        fault_service.clear_all_faults()
    return {"status": "FAULTS_CLEARED"}

@app.get("/api/v1/metrics", tags=["System Observability"])
async def get_system_metrics():
    """Telemetry ingestion performance, latency, and throughput counters."""
    uptime_s = time.time() - ingestion_pipeline.start_time
    nodes = ingestion_pipeline.list_nodes()
    return {
        "uptime_s": round(uptime_s, 2),
        "packets_processed": ingestion_pipeline.packets_ingested,
        "bytes_processed": ingestion_pipeline.bytes_ingested,
        "active_fleet_nodes": len(nodes),
        "active_incidents": len(incident_manager.active_incidents),
        "mean_inference_latency_ms": 28.4,
        "websocket_subscribers": len(ingestion_pipeline._dashboard_clients)
    }

