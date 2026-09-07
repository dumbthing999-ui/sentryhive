# EVALUATION & PROJECT SELECTION (AGENT 1-4 CONSENSUS)

## Selected Project: SentryHive — Autonomous Edge Wildfire & Microclimate Multi-Modal Early Warning Network

### Why SentryHive?
1. **Perfect Theme Fit:** Hardware (distributed sensor node, MCU, LoRa/cellular packetization) + IoT (telemetry streaming, mesh synchronization, time-series telemetry) + Applied AI (multi-modal TinyML sensor fusion combining pyrolysis particulate kinetics, acoustic crackle frequency analysis, and thermal flux vectors).
2. **Deterministic & Spectacular Demo:**
   - Full virtualized/emulated hardware bus (I2C/SPI sensor simulation feeding real embedded firmware logic).
   - Real-time physics engine generating realistic atmospheric drift, pyrolysis kinetics, and combustion gas spikes.
   - High-throughput ingestion backend (FastAPI/WebSockets/MQTT).
   - Live interactive 3D digital twin GIS telemetry dashboard displaying canopy microclimates, sensor nodes, fire propagation vectors, and autonomous alert dispatches.
   - Offline edge fallback: Microcontroller-level decision policy dispatches emergency alerts even under total WAN blackout.
3. **The "Why Three Times" Test:**
   - *Why Hardware?* Atmospheric gas sensors (CO, NO2, VOC, PM2.5/PM10), acoustic transducers, and thermal IR arrays must be physically deployed in the wild.
   - *Why AI?* Simple threshold alerts produce 80%+ false positives (dust storms, humidity drops, vehicle exhaust, controlled campfires). TinyML multi-modal temporal fusion classifies true pyrolysis combustion signatures in sub-second intervals.
   - *Why This Project?* Wildfires cause catastrophic ecological and human loss; detecting smoldering ignition before canopy breach saves lives and acreage.

---

## Directory Architecture to be built:
```text
volthacks-project/
├── AGENTS.md
├── CLAUDE.md
├── README.md
├── docs/
│   ├── architecture.md
│   ├── hardware_bom.md
│   ├── ai_model_card.md
│   ├── decisions.md
│   └── demo_guide.md
├── firmware/
│   ├── include/
│   ├── src/
│   │   ├── main.cpp
│   │   ├── sensors/
│   │   └── tinyml/
│   └── platformio.ini
├── simulation/
│   ├── physics_engine.py
│   ├── virtual_node_emulator.py
│   └── scenarios/
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── api/
│   │   ├── ml/
│   │   └── services/
│   └── tests/
├── frontend/
│   └── (Interactive real-time telemetry GIS dashboard)
└── scripts/
    ├── dev.sh
    ├── test.sh
    └── run_demo.sh
```
