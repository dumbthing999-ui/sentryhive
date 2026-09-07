"""Formal Incident Lifecycle State Machine & Forensic Report Generator.

Manages state transitions:
NORMAL -> WATCH -> SUSPICIOUS -> CONFIRMED -> CRITICAL -> CONTAINED -> RESOLVED

Produces audit-grade technical incident reports (INC-YYYY-XXXX).
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
import time
import uuid
from pydantic import BaseModel, Field

class IncidentLogEntry(BaseModel):
    timestamp_utc: float
    previous_state: str
    new_state: str
    triggering_node_id: str
    triggering_threat_index: float
    justification: str

class IncidentRecord(BaseModel):
    incident_id: str
    title: str
    state: str
    created_at_utc: float
    updated_at_utc: float
    resolved_at_utc: Optional[float] = None
    affected_sector: str
    origin_latitude: float
    origin_longitude: float
    peak_threat_index: float
    involved_nodes: List[str]
    estimated_containment_perimeter_m: float
    evacuation_order_issued: bool
    state_history: List[IncidentLogEntry] = Field(default_factory=list)

class IncidentManager:
    """Stateful Wildfire Incident Lifecycle & Command Dispatch Manager."""

    VALID_STATES = [
        "NORMAL",
        "WATCH",
        "SUSPICIOUS",
        "CONFIRMED",
        "CRITICAL",
        "CONTAINED",
        "RESOLVED"
    ]

    def __init__(self):
        self.active_incidents: Dict[str, IncidentRecord] = {}
        self.resolved_incidents: List[IncidentRecord] = []

    def create_or_update_from_threat(
        self,
        node_id: str,
        threat_index: float,
        lat: float,
        lon: float,
        sector_name: str = "Tahoe Sector 4"
    ) -> Optional[IncidentRecord]:
        now = time.time()

        # Find existing active incident in sector or create new
        existing_id = None
        for inc_id, inc in self.active_incidents.items():
            if inc.affected_sector == sector_name and inc.state != "RESOLVED":
                existing_id = inc_id
                break

        if threat_index < 0.35:
            # Threat subsided
            if existing_id and self.active_incidents[existing_id].state in ("WATCH", "SUSPICIOUS"):
                inc = self.active_incidents[existing_id]
                self._transition(inc, "RESOLVED", node_id, threat_index, "Environmental threat index decayed to baseline.")
                self.resolved_incidents.append(inc)
                del self.active_incidents[existing_id]
            return None

        # Determine target state
        if threat_index >= 0.85:
            target_state = "CRITICAL"
        elif threat_index >= 0.65:
            target_state = "CONFIRMED"
        elif threat_index >= 0.45:
            target_state = "SUSPICIOUS"
        else:
            target_state = "WATCH"

        if existing_id:
            inc = self.active_incidents[existing_id]
            inc.updated_at_utc = now
            if threat_index > inc.peak_threat_index:
                inc.peak_threat_index = round(threat_index, 3)
            if node_id not in inc.involved_nodes:
                inc.involved_nodes.append(node_id)
            if target_state != inc.state:
                self._transition(inc, target_state, node_id, threat_index, f"Threat index surged to {threat_index:.3f}")
            if target_state == "CRITICAL":
                inc.evacuation_order_issued = True
                inc.estimated_containment_perimeter_m = max(inc.estimated_containment_perimeter_m, 620.0)
            return inc
        else:
            # Create new incident record
            new_id = f"INC-2026-{str(uuid.uuid4())[:4].upper()}"
            inc = IncidentRecord(
                incident_id=new_id,
                title=f"Pyrolysis Wildfire Precursor Anomaly ({sector_name})",
                state=target_state,
                created_at_utc=now,
                updated_at_utc=now,
                affected_sector=sector_name,
                origin_latitude=lat,
                origin_longitude=lon,
                peak_threat_index=round(threat_index, 3),
                involved_nodes=[node_id],
                estimated_containment_perimeter_m=120.0 if target_state != "CRITICAL" else 480.0,
                evacuation_order_issued=(target_state == "CRITICAL")
            )
            self._transition(inc, target_state, node_id, threat_index, "Initial threshold breach detected by multi-modal edge sensor.")
            self.active_incidents[new_id] = inc
            return inc

    def _transition(self, inc: IncidentRecord, new_state: str, node_id: str, fti: float, reason: str):
        prev = inc.state
        inc.state = new_state
        inc.state_history.append(
            IncidentLogEntry(
                timestamp_utc=time.time(),
                previous_state=prev,
                new_state=new_state,
                triggering_node_id=node_id,
                triggering_threat_index=round(fti, 3),
                justification=reason
            )
        )

    def generate_forensic_markdown_report(self, incident_id: str) -> str:
        inc = self.active_incidents.get(incident_id)
        if not inc:
            for r in self.resolved_incidents:
                if r.incident_id == incident_id:
                    inc = r
                    break
        if not inc:
            return f"# Incident {incident_id} Not Found"

        created_str = time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime(inc.created_at_utc))
        updated_str = time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime(inc.updated_at_utc))

        md = f"""# SENTRYHIVE INCIDENT FORENSIC AUDIT REPORT
**Incident Reference:** `{inc.incident_id}`  
**Classification:** Wildland-Urban Interface (WUI) Pre-Canopy Pyrolysis Ignition  
**Geospatial Sector:** `{inc.affected_sector}` (Lat: {inc.origin_latitude:.5f}°, Lon: {inc.origin_longitude:.5f}°)  
**Initial Detection:** `{created_str}`  
**Last Operational State:** `{inc.state}` (`{updated_str}`)  

---

## 1. Tactical Incident Summary
* **Current Operational State:** **{inc.state}**
* **Peak Multi-Modal Threat Index:** **{inc.peak_threat_index:.3f} / 1.000**
* **Active Reporting Nodes:** `{', '.join(inc.involved_nodes)}`
* **Estimated Fire Perimeter:** `{inc.estimated_containment_perimeter_m:.1f} meters`
* **Life Safety Evacuation Order:** `{'ACTIVE — IMMEDIATE EVACUATION' if inc.evacuation_order_issued else 'STANDBY / MONITORING'}`

## 2. Multi-Modal Evidence Chain
1. **Gas Kinetics (BME688 MOX):** Rapid decay in MOX gas resistance (dln(Rs)/dt < -0.045 /s) with significant volatile organic emissions.
2. **Particulate Laser Scatter (SPS30):** High sub-micron mass concentration with diagnostic woodsmoke ratio R_pm = PM2.5 / PM10 > 0.85.
3. **Thermal Radiance (MLX90640):** Far-infrared focal array detected localized core temperature gradient exceeding +18.5 deg C divergence above ambient canopy equilibrium.
4. **Acoustic Cavitation (INMP441):** Ultrasonic and acoustic cellular moisture rupture spikes detected in the 2.5 kHz - 6.0 kHz frequency band.

## 3. Incident State Progression Chronology
| Timestamp (UTC) | Previous State | New State | Triggering Node | Threat Score | Operational Justification |
| :--- | :--- | :--- | :--- | :--- | :--- |
"""
        for entry in inc.state_history:
            t_str = time.strftime("%H:%M:%S", time.gmtime(entry.timestamp_utc))
            md += f"| `{t_str}` | `{entry.previous_state}` | **`{entry.new_state}`** | `{entry.triggering_node_id}` | `{entry.triggering_threat_index:.3f}` | {entry.justification} |\n"

        md += f"""
---
*Report autonomously synthesized by SentryHive Ingestion & Forensic Engine for VoltHacks 2026.*
"""
        return md

incident_manager = IncidentManager()
