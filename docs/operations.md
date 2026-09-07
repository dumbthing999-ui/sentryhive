# SentryHive: Wildland-Urban Interface (WUI) Operational Runbook & Tactical Procedures

**Document Scope:** Standard Operating Procedures (SOP) for Incident Commanders, Dispatch Operators, and Field Technicians  

---

## 1. Tactical Incident Escalation Protocol

When an environmental anomaly occurs, the platform guides operators through a structured lifecycle:

```text
  [ PHASE 0: MONITORING ]
  - All nodes report FTI < 0.35
  - Action: Continuous autonomous surveillance. Sub-GHz LoRa mesh heartbeat every 60 seconds.

        ↓ (Coincident Volatile Gas Surge & Hotspot Detection)

  [ PHASE 1: WATCH (FTI 0.35 - 0.59) ]
  - Action: Automated camera slew & cross-node telemetry correlation check.
  - Dispatch: Automated notice to local ranger patrol.

        ↓ (Multi-Node Confirmation & High Particle Ratio R_pm > 0.65)

  [ PHASE 2: ADVISORY (FTI 0.60 - 0.84) ]
  - Action: Multi-node spatial triangulation calculates probable origin coordinates and spread heading.
  - Dispatch: Wildfire triage teams placed on 5-minute standby.

        ↓ (Acoustic Cavitation Crackle Confirmed & Hotspot Gradient Divergence)

  [ PHASE 3: CRITICAL EVACUATION (FTI >= 0.85) ]
  - Action: Immediate local physical siren and strobe beacon activation (Zero-WAN Life Safety Fallback).
  - Dispatch: Automated emergency community alerts with calculated orthogonal egress vectors (Azimuth 135° SE).
```

---

## 2. Operator Commands & Diagnostics

### Starting the Tactical Platform
```bash
cd /home/kali/volthacks-project
./scripts/run_demo.sh
```

### Checking Real-World Environmental Data Streams
Query normalized stations and satellite thermal feeds:
```bash
curl -s http://127.0.0.1:8000/api/v1/providers/stations | python3 -m json.tool
curl -s http://127.0.0.1:8000/api/v1/providers/observations | python3 -m json.tool
```

### Querying Multi-Node Spatial Triangulation
```bash
curl -s "http://127.0.0.1:8000/api/v1/spatial/triangulate?wind_speed=5.2&wind_dir=225.0" | python3 -m json.tool
```

### Generating Audit-Grade Incident Reports
```bash
curl -s http://127.0.0.1:8000/api/v1/incidents
curl -s http://127.0.0.1:8000/api/v1/incidents/INC-2026-XXXX/report
```
