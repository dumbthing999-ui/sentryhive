#!/usr/bin/env bash
# SentryHive One-Click End-to-End Demo Orchestrator
# Starts backend ingestion server, begins node telemetry stream, and serves frontend.

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

echo "================================================================="
echo "  SENTRYHIVE: Autonomous Edge Wildfire Early Warning Network    "
echo "  VoltHacks 2026 Interactive Demonstration Runner                "
echo "================================================================="

VENV_PY="$ROOT_DIR/.venv/bin/python3"
if [ ! -f "$VENV_PY" ]; then
    VENV_PY="python3"
fi

# 1. Run Pre-flight Test Suite
echo "[1/3] Executing Automated Verification Test Suite..."
PYTHONPATH="$ROOT_DIR" "$VENV_PY" -m pytest tests/ -q

# 2. Launch FastAPI Telemetry Backend in background
echo "[2/3] Launching Telemetry Ingestion & TinyML Server (Port 8000)..."
PYTHONPATH="$ROOT_DIR" "$VENV_PY" -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 &
BACKEND_PID=$!

cleanup() {
    echo -e "\nShutting down SentryHive demo services..."
    kill "$BACKEND_PID" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

sleep 2

# 3. Serve Frontend Dashboard
echo "[3/3] Serving Interactive Digital Twin Dashboard on http://127.0.0.1:3000..."
cd "$ROOT_DIR/frontend"
"$VENV_PY" -m http.server 3000 --bind 127.0.0.1
