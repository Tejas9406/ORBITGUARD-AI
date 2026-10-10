# SatShield — Aerospace Telemetry Anomaly Detection Backend

Production-ready backend for satellite telemetry health monitoring (ISRO Problem Statement SPACE-03), providing real-time statistical & ML anomaly detection, verifiable evidence output, and high-performance endpoints for the SatShield mission control dashboard.

## 🚀 Quick Start

### 1. Requirements
Ensure Python 3.11+ is installed. Install backend dependencies:
```bash
pip install -r backend/requirements.txt
```

### 2. Ingest Verified Telemetry & Baselines
Run the data ingestion pipeline to populate the local SQLite database (`satshield.db`) with NASA SMAP/MSL telemetry and ground-truth benchmark data:
```bash
python -m backend.ingest
```

### 3. Launch FastAPI Server
```bash
uvicorn backend.main:app --reload --port 8000
```
- Interactive OpenAPI Docs: `http://localhost:8000/docs`
- System Health Check: `http://localhost:8000/healthz`

---

## 📡 API Contract (For Person 1 — React Frontend)

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/healthz` | System health check |
| `GET` | `/channels` | List monitored telemetry channels with verified source & units |
| `GET` | `/timeseries?channel_id={id}&downsample={N}` | Fetch chronological telemetry sequence with optional decimation |
| `GET` | `/anomalies?channel_id={id}&method={m}` | Query detected anomaly windows with complete statistical evidence |
| `GET` | `/benchmarks` | Query verified precision/recall/F1 benchmark metrics |
| `POST` | `/run-detection` | Trigger in-process detection on-demand (`zscore` or `isoforest`) |

---

## 🧪 Automated Testing
Run the complete unit & integration test suite:
```bash
python -m pytest -v backend/tests
```
All 10 tests verify:
- Edge-case zero-division protection on constant telemetry ($\sigma = 0$)
- In-process Z-score spike capture and evidence extraction
- Multivariate Isolation Forest detection
- Full FastAPI endpoint schema validation and response codes
