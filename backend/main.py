from fastapi import FastAPI, Depends, Query, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import Optional, List, Dict, Any
from pydantic import BaseModel

from .db import init_db, get_db
from .models import Channel, Telemetry, Anomaly, Benchmark
from .detectors import detect_zscore, detect_isoforest

from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield

app = FastAPI(
    title="SatShield API",
    description="Aerospace Telemetry Anomaly Detection & Subsystem Health Monitoring Backend for ISRO SPACE-03",
    version="1.0.0",
    lifespan=lifespan
)

# Configure CORS so React (Vite / localhost) can communicate seamlessly
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:3000",
        "*"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/healthz", tags=["System"])
def health_check():
    return {
        "status": "ok",
        "service": "SatShield Anomaly Detection Engine",
        "version": "1.0.0"
    }

# ----------------- Channel Endpoints -----------------

@app.get("/channels", tags=["Telemetry"])
def list_channels(source: Optional[str] = None, db: Session = Depends(get_db)):
    """
    List monitored spacecraft channels.
    Note: Subsystems and units for anonymized NASA channels are explicitly marked as unknown.
    """
    q = db.query(Channel)
    if source:
        q = q.filter(Channel.source.ilike(f"%{source}%"))
    
    channels = q.all()
    results = []
    for c in channels:
        anomaly_count = db.query(Anomaly).filter(Anomaly.channel_id == c.id).count()
        point_count = db.query(Telemetry).filter(Telemetry.channel_id == c.id).count()
        results.append({
            "id": c.id,
            "channel_key": c.channel_key,
            "source": c.source,
            "units": c.units,
            "subsystem": c.subsystem,
            "anomaly_type": c.anomaly_type,
            "point_count": point_count,
            "anomaly_count": anomaly_count,
            "meta_info": c.meta_info
        })
    return results

# ----------------- Telemetry Time-Series -----------------

@app.get("/timeseries", tags=["Telemetry"])
def get_timeseries(
    channel_id: int,
    start_step: Optional[int] = Query(None, description="Start timestep index"),
    end_step: Optional[int] = Query(None, description="End timestep index"),
    downsample: Optional[int] = Query(None, description="Target max points (e.g. 500) to downsample for UI"),
    db: Session = Depends(get_db)
):
    """
    Retrieve chronological telemetry sequence for a given channel.
    Supports decimation/downsampling to guarantee smooth Plotly renders.
    """
    ch = db.query(Channel).filter(Channel.id == channel_id).first()
    if not ch:
        raise HTTPException(status_code=404, detail="Channel not found")

    q = db.query(Telemetry).filter(Telemetry.channel_id == channel_id)
    if start_step is not None:
        q = q.filter(Telemetry.timestep >= start_step)
    if end_step is not None:
        q = q.filter(Telemetry.timestep <= end_step)

    rows = q.order_by(Telemetry.timestep).all()
    total_pts = len(rows)

    if downsample and total_pts > downsample and downsample > 0:
        step_stride = max(1, total_pts // downsample)
        selected_rows = rows[::step_stride]
    else:
        selected_rows = rows

    return {
        "channel_id": channel_id,
        "channel_key": ch.channel_key,
        "source": ch.source,
        "units": ch.units,
        "subsystem": ch.subsystem,
        "total_points": total_pts,
        "returned_points": len(selected_rows),
        "points": [
            {
                "timestep": r.timestep,
                "ts": r.ts,
                "value": round(r.value, 5)
            } for r in selected_rows
        ]
    }

# ----------------- Anomaly Detection Endpoints -----------------

@app.get("/anomalies", tags=["Anomalies"])
def get_anomalies(
    channel_id: Optional[int] = None,
    method: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Get detected anomaly windows and evidence payloads.
    """
    q = db.query(Anomaly)
    if channel_id is not None:
        q = q.filter(Anomaly.channel_id == channel_id)
    if method:
        q = q.filter(Anomaly.method == method)

    anomalies = q.order_by(Anomaly.start_step).all()
    results = []
    for a in anomalies:
        ch = db.query(Channel).filter(Channel.id == a.channel_id).first()
        results.append({
            "id": a.id,
            "channel_id": a.channel_id,
            "channel_key": ch.channel_key if ch else "Unknown",
            "source": ch.source if ch else "Unknown",
            "subsystem": ch.subsystem if ch else "Unknown",
            "start_step": a.start_step,
            "end_step": a.end_step,
            "window_start": a.window_start,
            "window_end": a.window_end,
            "score": a.score,
            "method": a.method,
            "severity": a.severity,
            "evidence": a.evidence
        })
    return results

class DetectionRequest(BaseModel):
    channel_id: int
    method: str = "zscore"  # "zscore" or "isoforest"
    window: Optional[int] = 100
    z_threshold: Optional[float] = 3.0
    contamination: Optional[float] = 0.015

@app.post("/run-detection", tags=["Anomalies"])
def run_in_process_detection(req: DetectionRequest, db: Session = Depends(get_db)):
    """
    Run in-process anomaly detection on-demand (no brittle subprocess scripts).
    """
    ch = db.query(Channel).filter(Channel.id == req.channel_id).first()
    if not ch:
        raise HTTPException(status_code=404, detail="Channel not found")

    rows = db.query(Telemetry).filter(Telemetry.channel_id == req.channel_id).order_by(Telemetry.timestep).all()
    if not rows:
        raise HTTPException(status_code=400, detail="No telemetry available for this channel")

    values = [r.value for r in rows]

    if req.method == "zscore":
        anomalies = detect_zscore(
            values,
            win=req.window or 100,
            z_threshold=req.z_threshold or 3.0
        )
    elif req.method == "isoforest":
        anomalies = detect_isoforest(
            values,
            contamination=req.contamination or 0.015
        )
    else:
        raise HTTPException(status_code=400, detail=f"Unsupported method: {req.method}. Choose 'zscore' or 'isoforest'.")

    # Save to database
    saved_count = 0
    for a in anomalies:
        start_r = rows[a["start_step"]]
        end_r = rows[a["end_step"]]
        obj = Anomaly(
            channel_id=ch.id,
            start_step=a["start_step"],
            end_step=a["end_step"],
            window_start=start_r.ts,
            window_end=end_r.ts,
            score=a["score"],
            method=a["method"],
            severity=a["severity"],
            evidence=a["evidence"],
            label=True
        )
        db.add(obj)
        saved_count += 1
    db.commit()

    return {
        "status": "success",
        "channel_key": ch.channel_key,
        "method": req.method,
        "new_anomalies_detected": saved_count,
        "anomalies": anomalies
    }

# ----------------- Model Evaluation & Benchmarks -----------------

@app.get("/benchmarks", tags=["Evaluation"])
def get_benchmarks(channel: Optional[str] = None, db: Session = Depends(get_db)):
    """
    Retrieve genuine benchmark evaluation metrics (Precision, Recall, F1)
    derived from expert-labeled NASA Telemanom dataset.
    """
    q = db.query(Benchmark)
    if channel:
        q = q.filter(Benchmark.channel == channel)
    
    rows = q.all()
    return [
        {
            "channel": r.channel,
            "method": r.method,
            "window_precision": r.precision,
            "window_recall": r.recall,
            "window_f1": r.f1
        } for r in rows
    ]
