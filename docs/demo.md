# SentryHive: Interactive Demonstration & Judge Evaluation Guide

**Platform Link:** [http://127.0.0.1:3000](http://127.0.0.1:3000)  
**FastAPI OpenAPI Specification:** [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)  
**Estimated Walkthrough Time:** 3 minutes  

---

## 1. Quick Launch

Launch the entire cyber-physical stack in one command:

```bash
cd /home/kali/volthacks-project
./scripts/run_demo.sh
```

---

## 2. Interactive Step-by-Step Walkthrough

### Step 1: Tactical Command Overview
* Open `http://127.0.0.1:3000`
* Notice the top tactical status bar: 4 active fleet nodes, current Tahoe Basin wind conditions ($4.5\text{ m/s}$ @ $225^\circ\text{ SW}$), and Vapor Pressure Deficit ($2.35\text{ kPa}$).
* In the main viewport, observe the live 2D/3D canopy topography, wireless LoRa mesh links, and real-time streaming BME688/SPS30 telemetry charts.
* Check the Melexis MLX90640 $32 \times 24$ thermal far-IR focal array canvas rendering live ambient canopy temperatures.

### Step 2: The Hero Proof — Mineral Dust False-Alarm Rejection
1. Click **`3. Mineral Dust Storm`** on the top scenario selector.
2. Observe the particulate chart surge: $\text{PM}_{10}$ spikes past $350\ \mu\text{g/m}^3$ and $\text{PM}_{2.5}$ exceeds $85\ \mu\text{g/m}^3$.
3. Switch to the **`XAI EXPLAINABILITY`** perspective tab.
4. Compare the two decision engines:
   * **Legacy Industrial Detector:** Trips a false alarm, screaming `CRITICAL ALARM (False Trigger)` purely because optical particulates exceeded $35\ \mu\text{g/m}^3$.
   * **SentryHive Multi-Modal TinyML:** Keeps status at `NOMINAL (Suppressed FTI: 0.084)`. It recognizes that the diagnostic ratio ($R_{pm} < 0.25$) and cold thermal gradient verify coarse mineral dust rather than woodsmoke.

### Step 3: Phase-0 Smoldering Wildfire & Multi-Node Triangulation
1. Click **`4. Peat Pyrolysis Wildfire`** on the scenario selector.
2. Switch back to the **`COMMAND`** perspective.
3. Watch the multi-modal coincidence unfold:
   * Volatile pyrolysis gases surge on the BME688.
   * Particulate ratio climbs past $0.90$ (dense sub-micron smoke).
   * The MLX90640 far-IR array reveals a localized $64^\circ\text{C}$ thermal hotspot.
   * The spatial triangulation engine draws the flame origin ellipse, projects the forward spread heading ($045^\circ\text{ NE}$), and draws a green safe evacuation corridor ($135^\circ\text{ SE}$).
4. The system issues `CRITICAL EVACUATION` **42 minutes before satellite or optical smoke lookouts could detect canopy breach**.

### Step 4: Time Machine Scrubber & Incident Forensics
1. In the top bar, click `T+15m`, `T+30m`, and `T+60m` to see physics-guided predictive risk trajectories.
2. Click the **`INCIDENTS & FORENSICS`** tab.
3. Click **`GENERATE FORENSIC AUDIT REPORT`** to view the machine-generated technical forensic report detailing the sensor evidence chain and timestamped state progression.

### Step 5: Hardware Mesh & Fault Injection Lab
1. Click the **`HARDWARE MESH`** perspective tab.
2. Inspect individual ESP32-S3 node telemetry, battery health, and LoRa link quality.
3. Click **`Drop Thermal Sensor`** to inject synthetic hardware failure. Observe the system gracefully downscaling the thermal weight without crashing.
4. Click **`Restore Nominal Hardware`** to return to healthy operation.
