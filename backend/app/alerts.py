"""Wildfire Alert Dispatcher with Geospatial Localization.

Manages multi-tier wildfire alerts:
- WATCH (Level 1, FTI 0.35 - 0.59)
- ADVISORY (Level 2, FTI 0.60 - 0.84)
- CRITICAL EVACUATION (Level 3, FTI >= 0.85)

Generates localized propagation polygons, evacuation zones,
and handles alert lifecycles and multi-channel dispatch targets.
"""

from __future__ import annotations

import math
import time
from typing import Dict, List, Optional, Tuple

from backend.app.models import (
    AlertLevel,
    AlertRecord,
    GeoCoordinates,
    GeoJSONFeature,
    GeoJSONFeatureCollection,
    GeoJSONGeometry,
    TelemetryPacket,
)


class AlertDispatcher:
    """Centralized Wildfire Alert Dispatcher and Geospatial Localizer."""

    def __init__(self) -> None:
        self._active_alerts: Dict[str, AlertRecord] = {}  # alert_id -> AlertRecord
        self._node_active_alert_map: Dict[str, str] = {}  # node_id -> alert_id
        self._alert_history: List[AlertRecord] = []

    def clear(self) -> None:
        """Reset internal alert registry (useful for test isolation)."""
        self._active_alerts.clear()
        self._node_active_alert_map.clear()
        self._alert_history.clear()

    @staticmethod
    def identify_triggering_modalities(packet: TelemetryPacket) -> List[str]:
        """Identify which physical sensor modalities contributed to threat detection."""
        triggers: List[str] = []

        # Modality 1: Gas kinetics
        if (
            packet.gas.voc_index > 120.0
            or packet.gas.gas_resistance_ohms < 30000.0
            or packet.gas.dln_rs_dt < -0.05
        ):
            triggers.append("pyrolysis_gas_kinetics")

        # Modality 2: Particulate combustion ratio
        pm_ratio = (
            packet.particulates.pm_ratio
            if packet.particulates.pm_ratio is not None
            else (
                packet.particulates.pm2_5_ug_m3 / packet.particulates.pm10_0_ug_m3
                if packet.particulates.pm10_0_ug_m3 > 0
                else 0.0
            )
        )
        if packet.particulates.pm2_5_ug_m3 > 25.0 and pm_ratio > 0.60:
            triggers.append("fine_aerosol_combustion_ratio")

        # Modality 3: Thermal radiance
        delta_t = packet.thermal.thermal_max_temp_c - packet.thermal.thermal_ambient_temp_c
        if delta_t > 7.0 or packet.thermal.thermal_gradient_c_per_sec > 0.2:
            triggers.append("localized_thermal_gradient")

        # Modality 4: Acoustic cavitation
        if (
            packet.acoustic.acoustic_crackle_event_rate_hz > 2.0
            or packet.acoustic.acoustic_spectral_energy_ratio > 0.30
        ):
            triggers.append("biomass_cell_rupture_cavitation")

        return triggers

    @staticmethod
    def calculate_localized_polygon(
        center_lat: float,
        center_lon: float,
        radius_meters: float,
        wind_speed_kmh: float = 12.0,
        wind_bearing_deg: float = 45.0,
        num_points: int = 24,
    ) -> List[List[float]]:
        """Compute an elliptical perimeter polygon aligned with ambient wind vector.
        
        GeoJSON coordinate format: [ [lon, lat], [lon, lat], ... , [lon, lat] ]
        """
        coords: List[List[float]] = []
        earth_radius = 6378137.0  # WGS84 meters

        # Elongate downstream along wind bearing, compress upwind
        wind_rad = math.radians(wind_bearing_deg)
        stretch_factor = 1.0 + min(2.5, wind_speed_kmh / 15.0)

        # Wind displacement center shift
        displacement_m = radius_meters * 0.35 * (stretch_factor - 1.0)
        disp_dx = displacement_m * math.sin(wind_rad)
        disp_dy = displacement_m * math.cos(wind_rad)

        shifted_center_lat = center_lat + (disp_dy / earth_radius) * (180.0 / math.pi)
        shifted_center_lon = center_lon + (disp_dx / (earth_radius * math.cos(math.radians(center_lat)))) * (180.0 / math.pi)

        for i in range(num_points):
            theta = (2.0 * math.pi * i) / num_points
            
            # Local ellipse calculation
            rx = radius_meters
            ry = radius_meters * stretch_factor

            # Rotate to wind bearing
            x = rx * math.cos(theta)
            y = ry * math.sin(theta)
            x_rot = x * math.cos(wind_rad) - y * math.sin(wind_rad)
            y_rot = x * math.sin(wind_rad) + y * math.cos(wind_rad)

            dlat = (y_rot / earth_radius) * (180.0 / math.pi)
            dlon = (x_rot / (earth_radius * math.cos(math.radians(center_lat)))) * (180.0 / math.pi)

            point_lat = round(shifted_center_lat + dlat, 6)
            point_lon = round(shifted_center_lon + dlon, 6)
            coords.append([point_lon, point_lat])

        # Close the GeoJSON ring
        coords.append(coords[0])
        return coords

    def process_telemetry(
        self,
        packet: TelemetryPacket,
        node_coords: GeoCoordinates,
        wind_speed_kmh: float = 14.0,
        wind_bearing_deg: float = 45.0,
    ) -> Optional[AlertRecord]:
        """Evaluate packet and generate, escalate, or resolve an alert."""
        fti = packet.fire_threat_index
        level = packet.alert_level

        # If nominal, resolve any existing active alert for this node
        if level == AlertLevel.NOMINAL:
            existing_alert_id = self._node_active_alert_map.get(packet.node_id)
            if existing_alert_id and existing_alert_id in self._active_alerts:
                self.resolve_alert(
                    existing_alert_id,
                    resolution_notes="Threat subsided: Telemetry returned to nominal baseline."
                )
            return None

        # Determine radii and dispatch targets based on level
        if level == AlertLevel.CRITICAL_EVACUATION:
            radius_m = 950.0
            evac_radius_m = 2500.0
            targets = [
                "DASHBOARD_WEBSOCKET",
                "LOCAL_GPIO_SIREN_110DB",
                "LOCAL_STROBE_ACTIVATION",
                "LORA_P2P_FLOOD_BROADCAST",
                "EMERGENCY_EVACUATION_CAD",
                "CAL_FIRE_MUTUAL_AID",
            ]
            desc = (
                f"CRITICAL WILDFIRE EVACUATION TRIGGER: Node {packet.node_id} detected active combustion "
                f"(FTI: {fti:.2f}). Autonomous GPIO strobe/siren fired. LoRa flood activated."
            )
        elif level == AlertLevel.ADVISORY:
            radius_m = 450.0
            evac_radius_m = 1200.0
            targets = [
                "DASHBOARD_WEBSOCKET",
                "LORA_MESH_STAGE_ALOHA",
                "FIRST_RESPONDER_DISPATCH",
                "CAD_PRIORITY",
            ]
            desc = (
                f"SMOLDERING PYROLYSIS ADVISORY: Node {packet.node_id} detected pre-ignition kinetics "
                f"(FTI: {fti:.2f}). Neighboring nodes requested for cross-verification."
            )
        else:  # WATCH
            radius_m = 180.0
            evac_radius_m = 600.0
            targets = [
                "DASHBOARD_WEBSOCKET",
                "INCIDENT_LOG",
                "CAD_ADVISORY",
            ]
            desc = (
                f"MICROCLIMATE ELEVATED WATCH: Node {packet.node_id} registered elevated risk "
                f"(FTI: {fti:.2f}). Increased polling cadence activated."
            )

        triggers = self.identify_triggering_modalities(packet)
        polygon = self.calculate_localized_polygon(
            center_lat=node_coords.latitude,
            center_lon=node_coords.longitude,
            radius_meters=radius_m,
            wind_speed_kmh=wind_speed_kmh,
            wind_bearing_deg=wind_bearing_deg,
        )

        existing_alert_id = self._node_active_alert_map.get(packet.node_id)
        if existing_alert_id and existing_alert_id in self._active_alerts:
            # Update and escalate existing alert
            alert = self._active_alerts[existing_alert_id]
            alert.level = level
            alert.severity_code = level.severity_code
            alert.fire_threat_index = fti
            alert.radius_meters = radius_m
            alert.evacuation_radius_meters = evac_radius_m
            alert.localized_polygon = polygon
            alert.triggering_modalities = triggers
            alert.description = desc
            alert.dispatch_targets = targets
            alert.timestamp = packet.timestamp
            return alert
        else:
            # Create new alert record
            alert = AlertRecord(
                node_id=packet.node_id,
                level=level,
                severity_code=level.severity_code,
                fire_threat_index=fti,
                timestamp=packet.timestamp,
                coordinates=node_coords,
                localized_polygon=polygon,
                radius_meters=radius_m,
                evacuation_radius_meters=evac_radius_m,
                triggering_modalities=triggers,
                description=desc,
                dispatch_targets=targets,
                status="ACTIVE",
            )
            self._active_alerts[alert.alert_id] = alert
            self._node_active_alert_map[packet.node_id] = alert.alert_id
            self._alert_history.append(alert)
            return alert

    def acknowledge_alert(self, alert_id: str, acknowledged_by: str = "IncidentCommander") -> Optional[AlertRecord]:
        """Mark an active alert as acknowledged by human dispatch/incident commander."""
        alert = self._active_alerts.get(alert_id)
        if alert:
            alert.status = "ACKNOWLEDGED"
            alert.acknowledged_by = acknowledged_by
            alert.acknowledged_at = time.time()
            return alert
        return None

    def resolve_alert(self, alert_id: str, resolution_notes: str = "Subsided") -> Optional[AlertRecord]:
        """Resolve and archive an alert."""
        alert = self._active_alerts.pop(alert_id, None)
        if alert:
            alert.status = "RESOLVED"
            alert.resolved_at = time.time()
            alert.resolution_notes = resolution_notes
            self._node_active_alert_map.pop(alert.node_id, None)
            return alert
        return None

    def get_active_alerts(self) -> List[AlertRecord]:
        """Return list of all currently active or acknowledged alerts."""
        return list(self._active_alerts.values())

    def get_alert_history(self, limit: int = 50) -> List[AlertRecord]:
        """Return historic alerts newest first."""
        return sorted(self._alert_history, key=lambda a: a.timestamp, reverse=True)[:limit]

    def to_geojson_features(self) -> List[GeoJSONFeature]:
        """Export active alerts as GeoJSON Features for Mapbox/Deck.gl visualization."""
        features: List[GeoJSONFeature] = []
        for alert in self._active_alerts.values():
            # 1. Alert Point Feature
            features.append(
                GeoJSONFeature(
                    geometry=GeoJSONGeometry(
                        type="Point",
                        coordinates=[alert.coordinates.longitude, alert.coordinates.latitude],
                    ),
                    properties={
                        "feature_type": "alert_center",
                        "alert_id": alert.alert_id,
                        "node_id": alert.node_id,
                        "level": alert.level.value,
                        "severity_code": alert.severity_code,
                        "fire_threat_index": alert.fire_threat_index,
                        "description": alert.description,
                        "status": alert.status,
                    },
                )
            )

            # 2. Alert Perimeter Polygon Feature
            if alert.localized_polygon:
                features.append(
                    GeoJSONFeature(
                        geometry=GeoJSONGeometry(
                            type="Polygon",
                            coordinates=[alert.localized_polygon],
                        ),
                        properties={
                            "feature_type": "fire_spread_perimeter",
                            "alert_id": alert.alert_id,
                            "level": alert.level.value,
                            "radius_meters": alert.radius_meters,
                            "evacuation_radius_meters": alert.evacuation_radius_meters,
                        },
                    )
                )

        return features


# Global singleton instance
alert_dispatcher = AlertDispatcher()
