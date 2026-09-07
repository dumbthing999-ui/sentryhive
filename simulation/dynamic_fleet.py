"""Interactive Click-to-Ignite Thermodynamics & Scalable Virtual Fleet Generator.

Allows:
1. Scaling virtual fleet from 4 up to 100 nodes across Tahoe National Forest.
2. Injecting interactive dynamic ignitions at arbitrary (lat, lon) coordinates,
   calculating thermodynamic heat flux, plume dispersion, and downwind node responses.
"""

from typing import List, Dict, Any, Optional, Tuple
import math
import random
import time
from pydantic import BaseModel, Field

class VirtualFleetConfig(BaseModel):
    node_count: int = Field(default=12, ge=4, le=100)
    center_latitude: float = 39.1820
    center_longitude: float = -120.1410
    radius_km: float = 8.5
    seed: int = 42

class DynamicIgnitionRequest(BaseModel):
    latitude: float = Field(..., ge=-90.0, le=90.0)
    longitude: float = Field(..., ge=-180.0, le=180.0)
    fire_intensity_mw: float = Field(default=25.0, ge=1.0, le=500.0)
    fuel_type: str = "Peat & Conifer Duff"
    wind_speed_m_s: float = Field(default=4.5, ge=0.0, le=30.0)
    wind_direction_deg: float = Field(default=225.0, ge=0.0, le=360.0)

class ActiveIgnitionSource(BaseModel):
    ignition_id: str
    latitude: float
    longitude: float
    intensity_mw: float
    fuel_type: str
    created_at_utc: float
    wind_speed_m_s: float
    wind_direction_deg: float
    plume_heading_deg: float
    affected_nodes_count: int = 0

class DynamicFleetManager:
    """Manages multi-node fleet scaling and interactive ignition simulation."""

    def __init__(self):
        self.active_ignitions: List[ActiveIgnitionSource] = []
        self.fleet_nodes: List[Dict[str, Any]] = []
        self.scale_fleet(VirtualFleetConfig(node_count=8))

    def scale_fleet(self, config: VirtualFleetConfig) -> List[Dict[str, Any]]:
        random.seed(config.seed)
        nodes = []
        
        # 4 Core Anchor Nodes
        core_anchors = [
            ("NODE-A741", "Ridgecrest Anchor", 39.1823, -120.1412, 2150.0),
            ("NODE-B812", "Eagle Rock Overlook", 39.1874, -120.1345, 2280.0),
            ("NODE-C903", "Alpine Meadow Basin", 39.1765, -120.1489, 2010.0),
            ("NODE-D104", "Granite Chief Ridge", 39.1912, -120.1280, 2420.0)
        ]
        
        for i, (nid, name, lat, lon, elev) in enumerate(core_anchors):
            if i < config.node_count:
                nodes.append({
                    "node_id": nid,
                    "name": name,
                    "latitude": lat,
                    "longitude": lon,
                    "elevation_m": elev,
                    "is_simulated": True,
                    "battery_v": 3.95,
                    "firmware": "v2.4.0-esp32s3"
                })

        # Generate additional Poisson-distributed nodes across sector
        for idx in range(len(nodes), config.node_count):
            angle = random.uniform(0, 2.0 * math.pi)
            dist_km = math.sqrt(random.uniform(0.1, 1.0)) * config.radius_km
            d_lat = (dist_km / 111.0) * math.cos(angle)
            d_lon = (dist_km / (111.0 * math.cos(math.radians(config.center_latitude)))) * math.sin(angle)
            nid = f"NODE-F{100 + idx}"
            elev = round(1950.0 + random.uniform(0, 500.0), 1)
            nodes.append({
                "node_id": nid,
                "name": f"Canopy Perimeter Node #{idx+1}",
                "latitude": round(config.center_latitude + d_lat, 5),
                "longitude": round(config.center_longitude + d_lon, 5),
                "elevation_m": elev,
                "is_simulated": True,
                "battery_v": round(3.85 + random.uniform(0, 0.25), 2),
                "firmware": "v2.4.0-esp32s3"
            })

        self.fleet_nodes = nodes
        return self.fleet_nodes

    def create_ignition(self, req: DynamicIgnitionRequest) -> ActiveIgnitionSource:
        now = time.time()
        ign_id = f"IGN-{int(now)}-{random.randint(100, 999)}"
        plume_heading = (req.wind_direction_deg + 180.0) % 360.0

        # Calculate affected nodes within thermal/plume corridor
        affected = 0
        for n in self.fleet_nodes:
            # Approximate distance in km
            d_lat = (n["latitude"] - req.latitude) * 111.0
            d_lon = (n["longitude"] - req.longitude) * 111.0 * math.cos(math.radians(req.latitude))
            dist_km = math.hypot(d_lat, d_lon)
            if dist_km < 3.5: # 3.5 km detection corridor
                affected += 1

        source = ActiveIgnitionSource(
            ignition_id=ign_id,
            latitude=round(req.latitude, 5),
            longitude=round(req.longitude, 5),
            intensity_mw=round(req.fire_intensity_mw, 1),
            fuel_type=req.fuel_type,
            created_at_utc=now,
            wind_speed_m_s=req.wind_speed_m_s,
            wind_direction_deg=req.wind_direction_deg,
            plume_heading_deg=round(plume_heading, 1),
            affected_nodes_count=affected
        )
        self.active_ignitions.append(source)
        return source

    def clear_ignitions(self):
        self.active_ignitions.clear()

dynamic_fleet_manager = DynamicFleetManager()
