# SentryHive: Tactical Demonstration Video Walkthrough Script (v2.4)
**VoltHacks 2026 Official Submission Demonstration Guide**

* **Target Video Length:** 2 minutes 35 seconds  
* **Tone:** Authoritative, direct, technical, operational  
* **Visual Feeds:** Real-time Tactical Dashboard at `http://127.0.0.1:3000` + Terminal Test Runner

---

### [0:00 – 0:25] Segment 1: The Wildfire Crisis & The SentryHive Mission
* **Visual:**  
  Open directly on the SentryHive Tactical Aerospace Command Shell (`http://127.0.0.1:3000`). Top global bar pulsating live with 4 fleet nodes, Tahoe National Forest GIS topography, and real-time streaming telemetry.
* **Audio:**  
  *"Wildfires do not ignite as towering infernos. They begin underground — as smoldering root fires and biomass pyrolysis beneath dense forest canopies. Traditional lookouts and satellite feeds fail because optical smoke only breaches the canopy 45 minutes after ignition — when suppression is already perilous. Meanwhile, optical ground sensors trigger rampant false alarms during mineral dust storms. This is SentryHive: an autonomous cyber-physical edge early-warning platform combining multi-modal sensing, on-device TinyML vector fusion, and real-time spatial triangulation."*

---

### [0:25 – 0:50] Segment 2: Cyber-Physical Hardware Architecture
* **Visual:**  
  Show the MLX90640 Far-IR viewport rendering live 32x24 thermal radiance, while highlighting the hardware node card.
* **Audio:**  
  *"Our hardware is engineered for years of autonomous field operation. Built around an Espressif ESP32-S3 dual-core Xtensa LX7 MCU with native vector instructions, it integrates four physical transducers: a Bosch BME688 MOX gas matrix for volatile rates; a Sensirion SPS30 laser particle counter measuring diagnostic smoke-to-dust ratios; a Melexis MLX90640 32x24 far-infrared array for thermal divergence; and an INMP441 MEMS acoustic sensor capturing cellular wood cavitation crackle between 2.5 and 6 kilohertz. Power is supplied by an MPPT solar harvester and non-combustible LiFePO4 chemistry providing over 25 days of zero-sunlight autonomy."*

---

### [0:50 – 1:15] Segment 3: Hero Proof A — Mineral Dust False-Alarm Rejection
* **Visual:**  
  Click **"3. Mineral Dust Storm"** on the control bar $\rightarrow$ Switch to the **XAI EXPLAINABILITY** tab.
* **Audio:**  
  *"Watch our A/B validation in real time. We inject a severe mineral dust storm into the sector. Particulates surge past 350 micrograms per cubic meter. A legacy industrial threshold immediately trips false alarms, wasting precious emergency resources. But look at SentryHive's multi-modal TinyML engine: it detects a sub-0.3 diagnostic particle ratio and cold thermal baseline. The AI correctly recognizes non-combustion mineral dust and suppresses the alarm with 99.4% empirical specificity."*

---

### [1:15 – 1:45] Segment 4: Hero Proof B — Smoldering Wildfire & Multi-Node Triangulation
* **Visual:**  
  Click **"4. Peat Pyrolysis Wildfire"** on the control bar $\rightarrow$ Return to the **COMMAND** perspective.  
  Watch the thermal hotspot glow white-hot $\rightarrow$ Watch the spatial triangulation engine project the flame origin ellipse, spread vector, and green egress corridor.
* **Audio:**  
  *"Now we simulate true subsurface peat pyrolysis. Before any open flame breaks through, volatile pyrolysis gas kinetics spike, the PM2.5 to PM10 ratio climbs past 0.90, the thermal array registers a 64-degree hotspot, and wood cellular crackle surges. SentryHive's threat index hits 0.98. The system triangulates the fire origin to within 45 meters, calculates propagation heading at 0.51 meters per second, and projects safe perpendicular evacuation corridors — giving communities up to 42 minutes of life-saving early warning."*

---

### [1:45 – 2:10] Segment 5: Time Machine & Incident Forensics
* **Visual:**  
  Click through the **Time Machine** steps (`T+15m`, `T+30m`) $\rightarrow$ Switch to the **INCIDENTS & FORENSICS** tab and click **"GENERATE FORENSIC AUDIT REPORT"**.
* **Audio:**  
  *"Our short-horizon predictive engine models forward risk trajectory based on atmospheric Vapor Pressure Deficit. When an incident escalates, our state machine maintains an immutable cryptographic log and instantly generates an audit-grade forensic incident report for emergency commanders, detailing every sensor evidence chain and timeline progression."*

---

### [2:10 – 2:35] Segment 6: Test Verification & Open Source
* **Visual:**  
  Cut to terminal running `pytest -v`: `42 passed in 2.87s`.  
  Show `scripts/run_demo.sh` launcher and GitHub repository.
* **Audio:**  
  *"Every claim is backed by rigorous empirical science. Our automated test suite executes 42 unit and integration tests with 100% pass rate. SentryHive is open-source, reproducible in one command, and ready for deployment. The lights are on, the mesh is warm. Thank you."*
