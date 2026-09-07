"""Multi-Node Wildfire Triangulation & Spread Propagation Engine.

Implements:
1. Spatial Anomaly Localization: Weighted centroid and confidence ellipse from multiple reporting nodes.
2. Propagation Vector Estimation: Spread velocity (m/s) and forward propagation azimuth (degrees).
3. Evacuation Corridor Optimization: Computes safe egress vectors orthogonal to fire propagation.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Tuple
import math
import numpy as np
from pydantic import BaseModel, Field

class TriangulatedOrigin(BaseModel):
    latitude: float
    longitude: float
    elevation_m: float
    confidence_pct: float
    semi_major_axis_m: float
    semi_minor_axis_m: float
    orientation_deg: float
    reporting_nodes_count: int
    contributing_node_ids: List[str]
    estimated_fire_area_hectares: float

class SpreadVector(BaseModel):
    velocity_m_per_s: float
    azimuth_deg: float
    flank_expansion_rate_m_s: float
    estimated_arrival_minutes: Dict[str, float] = Field(default_factory=dict)
    recommended_evacuation_azimuth_deg: float

class TriangulationResult(BaseModel):
    origin: Optional[TriangulatedOrigin]
    spread: Optional[SpreadVector]
    is_active: bool
    status: str
    calculation_timestamp_utc: float

class TriangulationEngine:
    """Calculates geospatial wildfire origin and propagation vectors from multi-node telemetry."""

    @staticmethod
    def haversine_distance_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        R = 6371000.0  # Earth radius in meters
        phi1 = math.radians(lat1)
        phi2 = math.radians(lat2)
        dphi = math.radians(lat2 - lat1)
        dlambda = math.radians(lon2 - lon1)
        a = math.sin(dphi / 2.0) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2.0) ** 2
        c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
        return R * c

    @staticmethod
    def triangulate(
        nodes: List[Dict[str, Any]],
        wind_speed_m_s: float = 4.5,
        wind_direction_deg: float = 225.0
    ) -> TriangulationResult:
        """
        Calculates origin coordinates weighted by node Fire Threat Index (FTI) and thermal anomaly.
        """
        import time
        now = time.time()

        # Filter nodes with active anomalies (FTI >= 0.50 or alert level >= ADVISORY)
        active_nodes = [
            n for n in nodes
            if n.get("threat_index", 0.0) >= 0.50 or n.get("alert_level") in ("ADVISORY", "CRITICAL_EVACUATION")
        ]

        if not active_nodes:
            return TriangulationResult(
                origin=None,
                spread=None,
                is_active=False,
                status="NO_ACTIVE_ANOMALY",
                calculation_timestamp_utc=now
            )

        # 1. Weighted Centroid Calculation
        total_weight = 0.0
        weighted_lat = 0.0
        weighted_lon = 0.0
        weighted_elev = 0.0
        weights = []
        lats = []
        lons = []

        for node in active_nodes:
            fti = node.get("threat_index", 0.5)
            th_grad = max(0.01, node.get("thermal_gradient", 0.1))
            # Weight is non-linear combination of threat score and thermal rate of rise
            w = math.pow(fti, 2.5) * (1.0 + th_grad)
            lat = node["latitude"]
            lon = node["longitude"]
            elev = node.get("elevation_m", 2000.0)

            weighted_lat += lat * w
            weighted_lon += lon * w
            weighted_elev += elev * w
            total_weight += w

            weights.append(w)
            lats.append(lat)
            lons.append(lon)

        center_lat = weighted_lat / total_weight
        center_lon = weighted_lon / total_weight
        center_elev = weighted_elev / total_weight

        # 2. Confidence Ellipse Calculation
        if len(active_nodes) >= 2:
            distances = [
                TriangulationEngine.haversine_distance_m(center_lat, center_lon, lat, lon)
                for lat, lon in zip(lats, lons)
            ]
            variance = np.var(distances) if len(distances) > 1 else 100.0
            std_dev = math.sqrt(variance)
            semi_major = max(40.0, std_dev * 1.6)
            semi_minor = max(25.0, std_dev * 0.9)
            confidence = min(98.5, 65.0 + len(active_nodes) * 8.5)
            est_area_ha = (math.pi * semi_major * semi_minor) / 10000.0
        else:
            semi_major = 75.0
            semi_minor = 50.0
            confidence = 72.0
            est_area_ha = 0.85

        # 3. Spread Vector Dynamics (Rothermel wind-driven propagation model with Orographic Slope Deflection)
        # Propagation follows downwind direction modified by terrain slope gradient
        spread_azimuth = (wind_direction_deg + 180.0) % 360.0

        # Orographic deflection: terrain elevation gradient exerts uphill thermal pull
        elevation_delta_m = max(-100.0, min(100.0, center_elev - 2000.0))
        slope_deflection_deg = math.atan2(elevation_delta_m, 1000.0) * (180.0 / math.pi) * 0.25
        adjusted_azimuth = (spread_azimuth + slope_deflection_deg) % 360.0

        # Spread rate scales exponentially with wind speed and uphill slope factor
        slope_factor = max(0.8, 1.0 + (elevation_delta_m / 500.0))
        base_spread_m_s = (0.15 + (wind_speed_m_s * 0.08)) * slope_factor
        flank_spread = base_spread_m_s * 0.35

        # Evacuation direction: 90 degrees orthogonal to spread vector away from plume
        evacuation_azimuth = (adjusted_azimuth + 90.0) % 360.0

        # Estimated arrival at reporting nodes
        eta_dict = {}
        for n in nodes:
            nid = n.get("node_id", "UNKNOWN")
            d = TriangulationEngine.haversine_distance_m(center_lat, center_lon, n["latitude"], n["longitude"])
            if d > 10.0:
                eta_minutes = round((d / base_spread_m_s) / 60.0, 1)
                eta_dict[nid] = eta_minutes

        origin = TriangulatedOrigin(
            latitude=round(center_lat, 6),
            longitude=round(center_lon, 6),
            elevation_m=round(center_elev, 1),
            confidence_pct=round(confidence, 1),
            semi_major_axis_m=round(semi_major, 1),
            semi_minor_axis_m=round(semi_minor, 1),
            orientation_deg=round(spread_azimuth, 1),
            reporting_nodes_count=len(active_nodes),
            contributing_node_ids=[n.get("node_id", "") for n in active_nodes],
            estimated_fire_area_hectares=round(est_area_ha, 2)
        )

        spread = SpreadVector(
            velocity_m_per_s=round(base_spread_m_s, 2),
            azimuth_deg=round(adjusted_azimuth, 1),
            flank_expansion_rate_m_s=round(flank_spread, 2),
            estimated_arrival_minutes=eta_dict,
            recommended_evacuation_azimuth_deg=round(evacuation_azimuth, 1)
        )

        return TriangulationResult(
            origin=origin,
            spread=spread,
            is_active=True,
            status="TRIANGULATED_FIRE_LOCATION",
            calculation_timestamp_utc=now
        )
