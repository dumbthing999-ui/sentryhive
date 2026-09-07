# SentryHive: Data Reality, Provenance Hierarchy & Resilient Ingestion

**Document Version:** 1.0.0  
**Target Specification:** VoltHacks 2026 Cyber-Physical Digital Twin Platform  

---

## 1. The Principle of Data Provenance

In environmental monitoring and wildfire intelligence platforms, ambiguity between **live physical observations**, **satellite detections**, and **synthetic simulations** erodes trust. SentryHive establishes an immutable, cryptographic data provenance tagging model at the ingestion layer.

Every telemetry record and environmental observation ingested into the platform carries a mandatory `provenance` metadata tag:

```text
                               DATA PROVENANCE HIERARCHY

  [ Real-World In-Situ Stations ]              [ Orbital Platforms ]
         │ (USFS RAWS, NEON)                          │ (NASA FIRMS)
         ▼                                            ▼
    PROVENANCE: LIVE / ECOLOGICAL                PROVENANCE: SATELLITE
         │                                            │
         └─────────────────────┬──────────────────────┘
                               │
                               ▼
                   [ Ingestion Normalizer ]
                               │
            ┌──────────────────┴──────────────────┐
            ▼                                     ▼
   (Network Disconnected)                (Virtual Sensor Mesh)
            │                                     │
            ▼                                     ▼
    PROVENANCE: CACHED                    PROVENANCE: SIMULATED
    (Local Fixture Fallback)              (ESP32-S3 TinyML Nodes)
```

---

## 2. Provenance Taxonomy & Display Standards

| Provenance Tag | Source System | Data Reality Description | Primary UI Indicator |
| :--- | :--- | :--- | :--- |
| `LIVE` | USFS RAWS / Regional Stations | Verified real-world meteorological sensor reading fetched over live network. | `● LIVE — USFS RAWS` (Cyan) |
| `SATELLITE` | NASA FIRMS (Aqua/Terra MODIS & Suomi VIIRS) | Orbital thermal infrared radiant heat anomaly ($338\text{ K}$, $\text{FRP} = 14.8\text{ MW}$). | `🛰 SATELLITE — NASA FIRMS` (Purple) |
| `ECOLOGICAL` | National Ecological Observatory Network | Research-grade flux tower measurements (canopy net radiation, biosphere VOC). | `🌿 ECOLOGICAL — NEON` (Emerald) |
| `AIR_QUALITY` | OpenAQ Tahoe Monitoring Network | Regional EPA-equivalent particulate ($\text{PM}_{2.5}, \text{PM}_{10}$) ground station. | `💨 AIR QUALITY — OpenAQ` (Indigo) |
| `CACHED` | Local Redis / SQLite / JSON Cache | Verified historical observation served when external network connectivity is lost. | `💾 CACHED — Offline Store` (Amber) |
| `SIMULATED` | SentryHive Virtual Sensor Nodes | Thermodynamic physics engine & on-device TinyML logistic sigmoid model output. | `⚡ SIMULATED — Virtual Node` (Blue) |

---

## 3. Resilient Multi-Tier Fallback Ladder

To ensure zero demo failure during live presentations or network-constrained judging evaluations, SentryHive executes a 4-tier fallback ladder:

```text
Tier 1: Live HTTPS API Request (2.0-second timeout)
   ↓ (If HTTP timeout, rate limit, or network severed)
Tier 2: High-Speed Local In-Memory Cache (TTL 15 minutes)
   ↓ (If cache unpopulated or cold boot)
Tier 3: Verified Offline Research Fixture (/data/fixtures/environmental_fixtures.json)
   ↓
Tier 4: Dynamic Physics Simulation Engine (simulation/physics_engine.py)
```

**Zero Silent Degradation Guarantee:** The system never silently transforms simulated data into a "live" tag. If the internet fails, the provider status immediately transitions to `OFFLINE_USING_FIXTURE`, and observations are explicitly stamped `CACHED` with age calculations.

---

## 4. Verification & Inspection Commands

Run automated provenance validation tests:

```bash
PYTHONPATH=. .venv/bin/pytest tests/test_real_data_and_fleet.py -v
```

Inspect live normalized observations and provenance tags via REST API:

```bash
curl -s http://127.0.0.1:8000/api/v1/providers/observations | python3 -m json.tool | head -n 35
```
