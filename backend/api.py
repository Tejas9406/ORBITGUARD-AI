import uvicorn
from fastapi import FastAPI, HTTPException, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import shutil
import tempfile
from datetime import datetime, timezone
from pathlib import Path
import os
import uuid
import uuid as uuid_pkg

from backend.coordinator import OrbitGuardPipeline
from backend.history import EvaluationHistory
from backend.esa_telemetry import ESATelemetryLoader
from backend.ingestion import ingest_nasa_channel, ingest_csv

app = FastAPI(title="OrbitGuard AI API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

esa_loader = ESATelemetryLoader()
history = EvaluationHistory()
ROOT = Path(__file__).resolve().parent

# Keep a simple memory cache for the run results so the UI can query it
RUNS_CACHE = {}
DATASETS_CACHE = {}

# Populate datasets on startup
try:
    esa_channels = esa_loader.list_channels()
    if esa_channels:
        DATASETS_CACHE["esa-opssat"] = {
            "id": "esa-opssat",
            "source": "ESA OPS-SAT-1",
            "validation_status": "AVAILABLE"
        }
except:
    pass

DATASETS_CACHE["nasa-smap"] = {
    "id": "nasa-smap",
    "source": "NASA SMAP/MSL",
    "validation_status": "AVAILABLE"
}

@app.get("/api/v1/health")
def health_check():
    return {"status": "ok"}

@app.get("/api/v1/datasets")
def get_datasets():
    return list(DATASETS_CACHE.values())

@app.post("/api/v1/datasets/upload")
async def upload_dataset(file: UploadFile = File(...)):
    with tempfile.NamedTemporaryFile(delete=False, suffix=".csv") as tmp:
        shutil.copyfileobj(file.file, tmp)
        tmp_path = tmp.name
        
    ds_id = f"custom-{uuid.uuid4().hex[:8]}"
    DATASETS_CACHE[ds_id] = {
        "id": ds_id,
        "source": file.filename,
        "validation_status": "AVAILABLE",
        "file_path": tmp_path
    }
    return DATASETS_CACHE[ds_id]

@app.get("/api/v1/datasets/{dataset_id}/channels")
def get_dataset_channels(dataset_id: str):
    channels = []
    if dataset_id == "esa-opssat":
        for cid in esa_loader.list_channels():
            channels.append({
                "id": cid,
                "name": cid,
                "subsystem": "OPS-SAT",
                "unit": "raw"
            })
    elif dataset_id == "nasa-smap":
        try:
            import pandas as pd
            df = pd.read_csv(ROOT / "labeled_anomalies.csv")
            for _, row in df.drop_duplicates(subset=["chan_id"]).iterrows():
                cid = row["chan_id"]
                subsys = row.get("spacecraft", "SMAP")
                channels.append({
                    "id": cid,
                    "name": cid,
                    "subsystem": subsys,
                    "unit": "raw"
                })
        except Exception as e:
            # Fallback if csv read fails
            channels.extend([
                {"id": "CADC0872", "name": "CADC0872", "subsystem": "SMAP", "unit": "raw"}
            ])
    elif dataset_id in DATASETS_CACHE:
        path = DATASETS_CACHE[dataset_id].get("file_path")
        # In a real scenario we'd parse the CSV columns, but for now we'll just allow a default channel
        channels.append({
            "id": "CustomChannel",
            "name": "Custom Upload Channel",
            "subsystem": "Custom",
            "unit": "raw"
        })
    else:
        raise HTTPException(status_code=404, detail="Dataset not found")
        
    return channels

@app.get("/api/v1/datasets/{dataset_id}/telemetry")
def get_telemetry_series(dataset_id: str, channel: str):
    observations = []
    try:
        if dataset_id == "esa-opssat":
            clean_cid = channel.replace("OPS-SAT-1 (ESA) - ", "").replace("ESA_OPSSAT_", "").replace("ESA_", "")
            telemetry_input, gt = esa_loader.to_canonical_input(clean_cid)
        elif dataset_id == "nasa-smap":
            telemetry_input = ingest_nasa_channel(ROOT, channel)
        elif dataset_id in DATASETS_CACHE:
            path = DATASETS_CACHE[dataset_id].get("file_path")
            telemetry_input = ingest_csv(path, channel_id="CustomChannel")
        else:
            raise HTTPException(status_code=404, detail="Dataset not found")

        signal = telemetry_input.target_signal
        timestamps = telemetry_input.metadata.get("timestamps")
        limit = min(1000, len(signal))
        
        for i in range(limit):
            ts = timestamps[i] if timestamps else datetime.now(timezone.utc).isoformat()
            observations.append({
                "timestamp": str(ts),
                "value": float(signal[i])
            })
    except Exception as e:
        import traceback
        traceback.print_exc()
        # Mock on failure
        for i in range(100):
            observations.append({"timestamp": datetime.now(timezone.utc).isoformat(), "value": 0.0})
            
    return {"observations": observations}

class RunAnalysisRequest(BaseModel):
    dataset_id: str
    channel: str

@app.post("/api/v1/analysis/run")
def run_analysis(req: RunAnalysisRequest):
    pipeline = OrbitGuardPipeline()
    try:
        weights_path = None
        gt = None
        
        if req.dataset_id == "esa-opssat":
            clean_cid = req.channel.replace("OPS-SAT-1 (ESA) - ", "").replace("ESA_OPSSAT_", "").replace("ESA_", "")
            telemetry_input, gt = esa_loader.to_canonical_input(clean_cid)
        elif req.dataset_id == "nasa-smap":
            telemetry_input = ingest_nasa_channel(ROOT, req.channel)
            weights_path = ROOT / "data" / "2018-05-19_15.00.10" / "models" / f"{req.channel}.h5"
        elif req.dataset_id in DATASETS_CACHE:
            path = DATASETS_CACHE[req.dataset_id].get("file_path")
            telemetry_input = ingest_csv(path, channel_id="CustomChannel")
        else:
            raise HTTPException(status_code=404, detail="Dataset not found")
            
        res = pipeline.run(
            telemetry_input=telemetry_input,
            ground_truth_ranges=gt,
            model_weights_path=weights_path,
            record_history=True
        )
        
        run_id = f"run_{uuid.uuid4().hex[:8]}"
        RUNS_CACHE[run_id] = res
        
        return {
            "run_id": run_id,
            "events": [], # The frontend asks for /events later
            "detectors": [d["detector_name"] for d in res.comparative_summary.to_dict(orient="records")]
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/analysis/{run_id}/events")
def get_run_events(run_id: str):
    if run_id not in RUNS_CACHE:
        return []
        
    res = RUNS_CACHE[run_id]
    events = []
    for idx, ev in enumerate(res.consensus_events):
        events.append({
            "id": f"evt-{idx}",
            "channel_id": getattr(res, "channel_id", "Unknown"),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "start_index": getattr(ev, "start", 0),
            "end_index": getattr(ev, "end", 0),
            "severity": "HIGH",
            "detectors": getattr(ev, "detectors_agreeing", []),
            "evidence": {
                "observed_value": 0.0,
                "peak_score": getattr(ev, "highest_score", 0.0),
                "unit": "raw",
                "physical_meaning": f"Consensus anomaly detected across {getattr(ev, 'agreement_count', 0)} models."
            }
        })
    return events

@app.get("/api/v1/analysis/{run_id}/health")
def get_run_health(run_id: str):
    if run_id not in RUNS_CACHE:
        raise HTTPException(status_code=404, detail="Run not found")
        
    res = RUNS_CACHE[run_id]
    num_events = len(res.consensus_events)
    status = "CRITICAL" if num_events > 0 else "NOMINAL"
    score = max(0, 100 - (num_events * 10))
    
    return {
        "run_id": run_id,
        "scope": "Channel Analysis",
        "channel_id": res.channel_id,
        "consensus_events": num_events,
        "executed_detectors": len(res.comparative_summary),
        "status": status,
        "health_indicator": score
    }

@app.get("/api/v1/history")
def get_history():
    runs = history.get_latest_runs(limit=100)
    history_list = []
    
    # Check if runs is empty
    if not runs.empty:
        for _, row in runs.iterrows():
            history_list.append({
                "run_id": row["run_id"],
                "dataset_id": "historical",
                "channel_id": "multi-channel" if row["channels_evaluated"] > 1 else "unknown",
                "event_count": 0,
                "duration_seconds": row["total_time_seconds"]
            })
            
    return history_list

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
