// SentryHive Tactical Aerospace Dashboard & Digital Twin Controller v2.4

let currentScenario = 'normal';
let isPaused = false;
let currentTimeOffset = 0; // minutes
let timeStep = 0;

// Tab Navigation
document.querySelectorAll('.nav-tab').forEach(tab => {
    tab.addEventListener('click', () => {
        document.querySelectorAll('.nav-tab').forEach(t => t.classList.remove('active'));
        document.querySelectorAll('.perspective-view').forEach(v => v.classList.remove('active'));
        tab.classList.add('active');
        const viewId = `view-${tab.getAttribute('data-tab')}`;
        const viewEl = document.getElementById(viewId);
        if (viewEl) viewEl.classList.add('active');
    });
});

// Chart.js Setup
const gasCtx = document.getElementById('gas-chart').getContext('2d');
const pmCtx = document.getElementById('pm-chart').getContext('2d');

const chartOpts = {
    responsive: true,
    maintainAspectRatio: false,
    animation: false,
    scales: {
        x: { grid: { color: 'rgba(255,255,255,0.04)' }, ticks: { color: '#64748b', font: { family: 'monospace', size: 9 } } },
        y: { grid: { color: 'rgba(255,255,255,0.04)' }, ticks: { color: '#64748b', font: { family: 'monospace', size: 9 } } }
    },
    plugins: {
        legend: { labels: { color: '#94a3b8', font: { family: 'monospace', size: 10 } } }
    }
};

const gasChart = new Chart(gasCtx, {
    type: 'line',
    data: {
        labels: Array(25).fill(''),
        datasets: [
            { label: 'VOC Index (BME688)', data: Array(25).fill(45), borderColor: '#00d2ff', borderWidth: 1.8, tension: 0.2 },
            { label: 'CO ppm (MOX Array)', data: Array(25).fill(0.25), borderColor: '#ffab00', borderWidth: 1.8, tension: 0.2 }
        ]
    },
    options: chartOpts
});

const pmChart = new Chart(pmCtx, {
    type: 'line',
    data: {
        labels: Array(25).fill(''),
        datasets: [
            { label: 'PM2.5 (µg/m³)', data: Array(25).fill(8), borderColor: '#00e676', borderWidth: 1.8, tension: 0.2 },
            { label: 'PM10 (µg/m³)', data: Array(25).fill(12), borderColor: '#818cf8', borderWidth: 1.8, tension: 0.2 }
        ]
    },
    options: chartOpts
});

// Canvases
const gisCanvas = document.getElementById('gis-map');
const gisCtx = gisCanvas.getContext('2d');
const thCanvas = document.getElementById('thermal-canvas');
const thCtx = thCanvas.getContext('2d');

const nodes = [
    { id: 'NODE-A741', name: 'Ridgecrest', x: 260, y: 170, lat: 39.1823, lon: -120.1412, fti: 0.03 },
    { id: 'NODE-B812', name: 'Eagle Rock', x: 520, y: 150, lat: 39.1874, lon: -120.1345, fti: 0.02 },
    { id: 'NODE-C903', name: 'Alpine Meadow', x: 380, y: 320, lat: 39.1765, lon: -120.1489, fti: 0.04 },
    { id: 'NODE-D104', name: 'Granite Chief', x: 650, y: 290, lat: 39.1912, lon: -120.1280, fti: 0.02 }
];

function drawGISMap() {
    gisCtx.fillStyle = '#070c14';
    gisCtx.fillRect(0, 0, gisCanvas.width, gisCanvas.height);

    // Subtle Terrain Elevation Contours
    gisCtx.strokeStyle = 'rgba(255, 255, 255, 0.035)';
    gisCtx.lineWidth = 1;
    for (let r = 70; r < 600; r += 45) {
        gisCtx.beginPath();
        gisCtx.arc(440, 230, r, 0, Math.PI * 2);
        gisCtx.stroke();
    }

    // Wireless Mesh Interconnects
    gisCtx.strokeStyle = 'rgba(0, 210, 255, 0.25)';
    gisCtx.setLineDash([4, 4]);
    gisCtx.beginPath();
    gisCtx.moveTo(nodes[0].x, nodes[0].y);
    gisCtx.lineTo(nodes[1].x, nodes[1].y);
    gisCtx.lineTo(nodes[3].x, nodes[3].y);
    gisCtx.lineTo(nodes[2].x, nodes[2].y);
    gisCtx.closePath();
    gisCtx.stroke();
    gisCtx.setLineDash([]);

    // Draw Sensor Nodes
    nodes.forEach(n => {
        // Sensing coverage ring
        gisCtx.fillStyle = 'rgba(0, 210, 255, 0.04)';
        gisCtx.beginPath();
        gisCtx.arc(n.x, n.y, 65, 0, Math.PI * 2);
        gisCtx.fill();

        // Node center
        gisCtx.fillStyle = '#00d2ff';
        gisCtx.beginPath();
        gisCtx.arc(n.x, n.y, 5, 0, Math.PI * 2);
        gisCtx.fill();

        // Node Label
        gisCtx.fillStyle = '#94a3b8';
        gisCtx.font = '10px monospace';
        gisCtx.fillText(`${n.id} [${n.name}]`, n.x + 8, n.y - 4);
    });

    // Triangulated Anomaly Overlay during Wildfire
    if (currentScenario === 'wildfire') {
        const originX = 390 + Math.sin(timeStep * 0.05) * 8;
        const originY = 295;

        // Rothermel Plume Envelope
        const plumeGrad = gisCtx.createRadialGradient(originX, originY, 10, originX + 70, originY - 40, 160);
        plumeGrad.addColorStop(0, 'rgba(255, 23, 68, 0.75)');
        plumeGrad.addColorStop(0.4, 'rgba(255, 171, 0, 0.35)');
        plumeGrad.addColorStop(1, 'rgba(255, 23, 68, 0)');
        gisCtx.fillStyle = plumeGrad;
        gisCtx.beginPath();
        gisCtx.arc(originX, originY, 130, 0, Math.PI * 2);
        gisCtx.fill();

        // Origin Ellipse
        gisCtx.strokeStyle = '#ff1744';
        gisCtx.lineWidth = 2;
        gisCtx.beginPath();
        gisCtx.ellipse(originX, originY, 45, 28, Math.PI / 4, 0, Math.PI * 2);
        gisCtx.stroke();

        // Forward Spread Vector Arrow
        gisCtx.strokeStyle = '#ffab00';
        gisCtx.lineWidth = 3;
        gisCtx.beginPath();
        gisCtx.moveTo(originX, originY);
        gisCtx.lineTo(originX + 95, originY - 60);
        gisCtx.stroke();
        gisCtx.fillStyle = '#ffab00';
        gisCtx.font = 'bold 11px monospace';
        gisCtx.fillText('Propagation: 0.51 m/s @ 45° NE', originX + 40, originY - 70);

        // Orthogonal Safe Evacuation Corridor
        gisCtx.strokeStyle = '#00e676';
        gisCtx.lineWidth = 3;
        gisCtx.beginPath();
        gisCtx.moveTo(originX, originY);
        gisCtx.lineTo(originX + 110, originY + 80);
        gisCtx.stroke();
        gisCtx.fillStyle = '#00e676';
        gisCtx.fillText('Optimal Evacuation Azimuth: 135° SE', originX + 75, originY + 100);
    }
}

function drawThermalMatrix(scenario) {
    const w = 32;
    const h = 24;
    const cellW = thCanvas.width / w;
    const cellH = thCanvas.height / h;

    for (let y = 0; y < h; y++) {
        for (let x = 0; x < w; x++) {
            let temp = 21.0 + Math.random() * 1.2;

            if (scenario === 'wildfire') {
                const dist = Math.hypot(x - 17, y - 13);
                if (dist < 7) {
                    temp += Math.max(0, (7 - dist) * 7.2) + Math.random() * 2.0;
                }
            } else if (scenario === 'campfire') {
                const dist = Math.hypot(x - 16, y - 12);
                if (dist < 3.5) {
                    temp += Math.max(0, (3.5 - dist) * 4.0);
                }
            }

            const norm = Math.min(1.0, Math.max(0, (temp - 20) / 45));
            const r = Math.floor(norm * 255);
            const g = Math.floor(Math.sin(norm * Math.PI) * 190);
            const b = Math.floor((1.0 - norm) * 190);

            thCtx.fillStyle = `rgb(${r},${g},${b})`;
            thCtx.fillRect(x * cellW, y * cellH, cellW + 0.5, cellH + 0.5);
        }
    }
}

function updateTelemetryTick() {
    if (isPaused) return;
    timeStep++;

    drawGISMap();
    drawThermalMatrix(currentScenario);

    const threatBadge = document.getElementById('global-threat-badge');
    const incidentTag = document.getElementById('incident-status-tag');
    const triOrigin = document.getElementById('tri-origin-val');
    const triVel = document.getElementById('tri-vel-val');
    const triHeading = document.getElementById('tri-heading-val');
    const triEgress = document.getElementById('tri-egress-val');

    let voc = 45, co = 0.25, pm25 = 7, pm10 = 11;
    let gasW = 0.05, pmW = 0.08, thW = 0.02, acW = 0.01;

    if (currentScenario === 'normal') {
        threatBadge.className = 'pv nominal';
        threatBadge.innerText = 'NOMINAL';
        incidentTag.className = 'metric-pill green';
        incidentTag.innerText = 'SURVEILLANCE NORMAL';
        triOrigin.innerText = 'NO ANOMALY';
        triVel.innerText = '0.00 m/s';
        triHeading.innerText = '--';
        triEgress.className = 'mv secure';
        triEgress.innerText = 'NORMAL PATROL';

        document.getElementById('xai-legacy-verdict').className = 'verdict-banner secure';
        document.getElementById('xai-legacy-verdict').innerText = 'NORMAL (Clean)';
        document.getElementById('xai-sentry-verdict').className = 'verdict-banner secure';
        document.getElementById('xai-sentry-verdict').innerText = 'NOMINAL (FTI: 0.028)';

        gasW = 0.05; pmW = 0.08; thW = 0.02; acW = 0.01;
    } else if (currentScenario === 'dust_storm') {
        pm25 = 88 + Math.random() * 8;
        pm10 = 350 + Math.random() * 25; // Coarse dust surge
        threatBadge.className = 'pv nominal';
        threatBadge.innerText = 'NOMINAL (Filtered)';
        incidentTag.className = 'metric-pill green';
        incidentTag.innerText = 'DUST STORM SUPPRESSED';

        document.getElementById('xai-legacy-verdict').className = 'verdict-banner';
        document.getElementById('xai-legacy-verdict').innerText = 'CRITICAL ALARM (False Trigger)';
        document.getElementById('xai-legacy-text').innerText = 'Triggered! PM2.5 > 80 ug/m3 exceeded. Single-sensor detector cannot differentiate.';

        document.getElementById('xai-sentry-verdict').className = 'verdict-banner secure';
        document.getElementById('xai-sentry-verdict').innerText = 'NOMINAL (Suppressed FTI: 0.084)';
        document.getElementById('xai-sentry-text').innerText = 'Diagnostic particle ratio (0.25) & cold thermal gradient verify mineral dust. Alarm rejected.';

        gasW = 0.06; pmW = 0.12; thW = 0.01; acW = 0.01;
    } else if (currentScenario === 'wildfire') {
        voc = 450 + Math.random() * 35;
        co = 17.2 + Math.random() * 3;
        pm25 = 180 + Math.random() * 15;
        pm10 = 200 + Math.random() * 15;

        threatBadge.className = 'pv critical';
        threatBadge.innerText = 'CRITICAL EVACUATION';
        incidentTag.className = 'metric-pill red';
        incidentTag.innerText = 'ACTIVE INCIDENT (INC-2026-A741)';

        triOrigin.innerText = '39.1795° N, -120.1448° W';
        triVel.innerText = '0.51 m/s';
        triHeading.innerText = '045° NE';
        triEgress.className = 'mv alert';
        triEgress.innerText = 'EVACUATE AZIMUTH 135° SE';

        document.getElementById('xai-legacy-verdict').className = 'verdict-banner';
        document.getElementById('xai-legacy-verdict').innerText = 'CRITICAL (Delayed Alert)';
        document.getElementById('xai-sentry-verdict').className = 'verdict-banner';
        document.getElementById('xai-sentry-verdict').innerText = 'CRITICAL (Lead Time: +42m)';
        document.getElementById('xai-sentry-text').innerText = 'Multi-modal coincidence confirmed: Cellular wood cavitation + pyrolysis gas kinetic runaway.';

        gasW = 0.88; pmW = 0.94; thW = 0.96; acW = 0.89;
    }

    // Update XAI Bars
    document.getElementById('bar-gas').style.width = `${gasW * 100}%`;
    document.getElementById('val-gas').innerText = gasW.toFixed(2);
    document.getElementById('bar-pm').style.width = `${pmW * 100}%`;
    document.getElementById('val-pm').innerText = pmW.toFixed(2);
    document.getElementById('bar-th').style.width = `${thW * 100}%`;
    document.getElementById('val-th').innerText = thW.toFixed(2);
    document.getElementById('bar-ac').style.width = `${acW * 100}%`;
    document.getElementById('val-ac').innerText = acW.toFixed(2);

    // Update charts
    gasChart.data.datasets[0].data.shift();
    gasChart.data.datasets[0].data.push(voc);
    gasChart.data.datasets[1].data.shift();
    gasChart.data.datasets[1].data.push(co);
    gasChart.update();

    pmChart.data.datasets[0].data.shift();
    pmChart.data.datasets[0].data.push(pm25);
    pmChart.data.datasets[1].data.shift();
    pmChart.data.datasets[1].data.push(pm10);
    pmChart.update();
}

// Scenario Controls
document.querySelectorAll('.scen-btn').forEach(btn => {
    btn.addEventListener('click', () => {
        document.querySelectorAll('.scen-btn').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        currentScenario = btn.getAttribute('data-scenario');
    });
});

// Play / Pause Time Machine
document.getElementById('btn-play-pause').addEventListener('click', (e) => {
    isPaused = !isPaused;
    e.target.innerText = isPaused ? '▶ RESUME' : '⏸ PAUSE';
});

// Time step buttons
document.querySelectorAll('.t-step').forEach(btn => {
    btn.addEventListener('click', () => {
        document.querySelectorAll('.t-step').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        currentTimeOffset = parseInt(btn.getAttribute('data-t'));
    });
});

// Fault Controls
document.querySelectorAll('.fault-btn').forEach(btn => {
    btn.addEventListener('click', () => {
        if (btn.id === 'btn-clear-faults') {
            alert('Nominal sensor health restored across all nodes.');
        } else {
            const s = btn.getAttribute('data-sensor');
            const m = btn.getAttribute('data-mode');
            alert(`Synthetic hardware failure injected: ${s.toUpperCase()} [${m.toUpperCase()}]`);
        }
    });
});

// Forensic Report Generator
document.getElementById('btn-export-report').addEventListener('click', () => {
    const reportBox = document.getElementById('report-content');
    reportBox.innerText = `# SENTRYHIVE INCIDENT FORENSIC AUDIT REPORT
Incident Reference: INC-2026-A741
Classification: Wildland-Urban Interface (WUI) Pre-Canopy Pyrolysis Ignition
Sector: Tahoe National Forest Sector Alpha-4 (Lat: 39.1820° N, Lon: -120.1410° W)
Detection Phase: Subsurface Root Smoldering (T-42m before canopy breach)

Operational State: CRITICAL_EVACUATION
Peak Multi-Modal Threat Index: 0.984 / 1.000
Active Reporting Nodes: NODE-A741, NODE-C903
Estimated Flame Perimeter: 480.0 meters
Recommended Egress Azimuth: 135° SE (Orthogonal to 045° NE spread heading)

Multi-Modal Cryptographic Evidence Chain:
1. Gas Kinetics (BME688 MOX): dln(Rs)/dt = -0.052 /s | VOC Index: 462.0
2. Particle Scatter (SPS30): PM2.5 = 182.0 ug/m3 | Ratio PM2.5/PM10 = 0.910 (Sub-micron woodsmoke)
3. Thermal Radiance (MLX90640): Hotspot 64.2°C | Gradient: +2.8°C/s
4. Acoustic Cavitation (INMP441): Ultrasonic wood crackle = 15.2 events/s in 2.5kHz-6kHz band

Verdict: Validated Ground-Truth Wildfire Ignition. Evacuation Warning Issued 42 Minutes Ahead of Satellite Feeds.`;
});

// Populate Hardware Node Cards
const nodeContainer = document.getElementById('node-cards-container');
if (nodeContainer) {
    nodes.forEach(n => {
        const card = document.createElement('div');
        card.className = 'node-card';
        card.innerHTML = `
            <h4>${n.id} [${n.name}]</h4>
            <div class="node-card-stat"><span class="k">MCU:</span><span class="v">ESP32-S3 (Xtensa LX7)</span></div>
            <div class="node-card-stat"><span class="k">Battery:</span><span class="v">3.95V (LiFePO4)</span></div>
            <div class="node-card-stat"><span class="k">Uptime:</span><span class="v">18.4 days</span></div>
            <div class="node-card-stat"><span class="k">LoRa Link:</span><span class="v">-76 dBm (SNR 9.2dB)</span></div>
            <div class="node-card-stat"><span class="k">TinyML Core:</span><span class="v" style="color: #00e676;">OPERATIONAL (28.4ms)</span></div>
        `;
        nodeContainer.appendChild(card);
    });
}

setInterval(updateTelemetryTick, 1000);
updateTelemetryTick();
