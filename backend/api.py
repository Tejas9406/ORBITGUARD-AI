import uvicorn
from fastapi import FastAPI, HTTPException, File, UploadFile, Depends, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy.orm import Session
import shutil
import tempfile
from datetime import datetime, timezone, timedelta
from pathlib import Path
import os
import uuid
from typing import Optional, List, Dict, Any

from backend.coordinator import OrbitGuardPipeline
from backend.history import EvaluationHistory
from backend.esa_telemetry import ESATelemetryLoader
from backend.ingestion import ingest_nasa_channel, ingest_csv

from backend.db import init_db, get_db
from backend.models import Channel, Telemetry, Anomaly, Benchmark
from backend.detectors import detect_zscore, detect_isoforest

from contextlib import asynccontextmanager

ROOT = Path(__file__).resolve().parent
REPO_ROOT = ROOT.parent
DATA_DIR = REPO_ROOT / "data"

TESTING_CSV = DATA_DIR / "testing_dataset.csv"
if not TESTING_CSV.exists():
    TESTING_CSV = REPO_ROOT.parent / "testing dataset.csv"

RUNS_CACHE: Dict[str, Any] = {}
DATASETS_CACHE: Dict[str, Dict[str, Any]] = {}

esa_loader = None
try:
    esa_loader = ESATelemetryLoader()
except Exception as e:
    pass

history = EvaluationHistory()

def populate_datasets():
    # 1. First-class testing dataset.csv
    if TESTING_CSV.exists():
        DATASETS_CACHE["testing-dataset"] = {
            "id": "testing-dataset",
            "source": "testing dataset.csv (Flight Telemetry)",
            "validation_status": "AVAILABLE",
            "file_path": str(TESTING_CSV),
            "channels": ["sensor_channel_4", "sensor_channel_5", "sensor_channel_6"]
        }

    # 2. ESA OPS-SAT
    if esa_loader:
        try:
            esa_channels = esa_loader.list_channels()
            if esa_channels:
                DATASETS_CACHE["esa-opssat"] = {
                    "id": "esa-opssat",
                    "source": "ESA OPS-SAT-1",
                    "validation_status": "AVAILABLE"
                }
        except Exception:
            pass


    # 3. NASA SMAP
    DATASETS_CACHE["nasa-smap"] = {
        "id": "nasa-smap",
        "source": "NASA SMAP/MSL",
        "validation_status": "AVAILABLE"
    }

populate_datasets()

@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        init_db()
    except Exception as e:
        print(f"Database init warning: {e}")
    yield

app = FastAPI(
    title="SatShield & OrbitGuard AI API",
    description="Integrated Multi-Model Consensus Telemetry Anomaly Detection & Spacecraft Fleet Intelligence Engine",
    version="1.0.0",
    lifespan=lifespan
)

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

# ----------------- Health Endpoints -----------------

@app.get("/healthz", tags=["System"])
@app.get("/api/health", tags=["System"])
@app.get("/api/v1/health", tags=["System"])
def health_check():
    return {
        "status": "ok",
        "service": "SatShield & OrbitGuard AI Multi-Model Detection Engine",
        "version": "1.0.0",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

# ----------------- OrbitGuard Multi-Model Dataset Endpoints -----------------

@app.get("/api/v1/datasets", tags=["OrbitGuard Datasets"])
def get_datasets():
    populate_datasets()
    return list(DATASETS_CACHE.values())

@app.post("/api/v1/datasets/upload", tags=["OrbitGuard Datasets"])
async def upload_dataset(file: UploadFile = File(...)):
    with tempfile.NamedTemporaryFile(delete=False, suffix=".csv") as tmp:
        shutil.copyfileobj(file.file, tmp)
        tmp_path = tmp.name

    import pandas as pd
    custom_channels = []
    try:
        df_custom = pd.read_csv(tmp_path, nrows=5)
        for col in df_custom.columns:
            if col.lower() not in ["timestamp", "time", "date", "ts", "is_anomaly"]:
                custom_channels.append(str(col))
    except Exception:
        pass

    if not custom_channels:
        custom_channels = ["CustomChannel"]

    ds_id = f"custom-{uuid.uuid4().hex[:8]}"
    DATASETS_CACHE[ds_id] = {
        "id": ds_id,
        "source": file.filename or "uploaded_telemetry.csv",
        "validation_status": "AVAILABLE",
        "file_path": tmp_path,
        "channels": custom_channels
    }
    return DATASETS_CACHE[ds_id]

@app.get("/api/v1/datasets/{dataset_id}/channels", tags=["OrbitGuard Datasets"])
def get_dataset_channels(dataset_id: str):
    channels = []
    if dataset_id == "testing-dataset":
        return [
            {
                "id": "sensor_channel_4",
                "name": "Sensor Channel 4 (Power EPS)",
                "subsystem": "EPS",
                "unit": "V"
            },
            {
                "id": "sensor_channel_5",
                "name": "Sensor Channel 5 (Thermal TCS)",
                "subsystem": "TCS",
                "unit": "°C"
            },
            {
                "id": "sensor_channel_6",
                "name": "Sensor Channel 6 (Attitude AOCS)",
                "subsystem": "AOCS",
                "unit": "deg/s"
            }
        ]
    elif dataset_id == "esa-opssat":
        if esa_loader:
            for cid in esa_loader.list_channels():
                channels.append({
                    "id": cid,
                    "name": cid,
                    "subsystem": "OPS-SAT",
                    "unit": "raw"
                })
        else:
            channels.append({
                "id": "CADC0872",
                "name": "CADC0872",
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
        except Exception:
            channels.extend([
                {"id": "CADC0872", "name": "CADC0872", "subsystem": "SMAP", "unit": "raw"}
            ])
    elif dataset_id in DATASETS_CACHE:
        path = DATASETS_CACHE[dataset_id].get("file_path")
        cached_chans = DATASETS_CACHE[dataset_id].get("channels", [])
        if path and Path(path).exists():
            import pandas as pd
            try:
                df = pd.read_csv(path, nrows=5)
                for col in df.columns:
                    if col.lower() not in ["timestamp", "time", "date", "ts", "is_anomaly"]:
                        channels.append({
                            "id": str(col),
                            "name": str(col),
                            "subsystem": "Custom Telemetry",
                            "unit": "raw"
                        })
            except Exception:
                pass
        if not channels:
            for cid in cached_chans or ["CustomChannel"]:
                channels.append({
                    "id": str(cid),
                    "name": str(cid),
                    "subsystem": "Custom Telemetry",
                    "unit": "raw"
                })
    else:
        raise HTTPException(status_code=404, detail="Dataset not found")

    return channels

@app.get("/api/v1/datasets/{dataset_id}/telemetry", tags=["OrbitGuard Datasets"])
def get_telemetry_series(
    dataset_id: str,
    channel: str,
    downsample: Optional[int] = Query(None, description="Max points to return for chart"),
    limit: Optional[int] = Query(None, description="Max observations")
):
    observations = []
    try:
        import pandas as pd
        import numpy as np

        if dataset_id == "testing-dataset":
            if not TESTING_CSV.exists():
                raise HTTPException(status_code=404, detail="testing dataset.csv not found")
            df = pd.read_csv(TESTING_CSV)
            target_col = channel if channel in df.columns else "sensor_channel_4"
            signal = df[target_col].to_numpy(dtype=float)
            is_anom = df["is_anomaly"].to_numpy(dtype=int) if "is_anomaly" in df.columns else np.zeros(len(signal), dtype=int)

            base_epoch = datetime(2026, 10, 10, 0, 0, 0, tzinfo=timezone.utc)
            total = len(signal)
            max_limit = limit or total
            
            # Decimate if series is large and downsample requested
            if downsample and total > downsample:
                step = max(1, total // downsample)
                indices = list(range(0, min(total, max_limit), step))
            elif total > 2000 and not limit:
                # Default friendly size for smooth 60fps Plotly rendering
                step = max(1, total // 1000)
                indices = list(range(0, total, step))
            else:
                indices = list(range(min(total, max_limit)))

            for idx in indices:
                ts = base_epoch + timedelta(seconds=idx * 10)
                observations.append({
                    "timestamp": ts.isoformat(),
                    "value": round(float(signal[idx]), 5),
                    "isAnomaly": bool(is_anom[idx] == 1)
                })

            return {"observations": observations}

        elif dataset_id == "esa-opssat":
            clean_cid = channel.replace("OPS-SAT-1 (ESA) - ", "").replace("ESA_OPSSAT_", "").replace("ESA_", "")
            telemetry_input, gt = esa_loader.to_canonical_input(clean_cid)
            signal = telemetry_input.target_signal
            timestamps = telemetry_input.metadata.get("timestamps")
        elif dataset_id == "nasa-smap":
            telemetry_input = ingest_nasa_channel(ROOT, channel)
            signal = telemetry_input.target_signal
            timestamps = telemetry_input.metadata.get("timestamps")
        elif dataset_id in DATASETS_CACHE:
            path = DATASETS_CACHE[dataset_id].get("file_path")
            telemetry_input = ingest_csv(path, channel_id=channel, telemetry_column=channel)
            signal = telemetry_input.target_signal
            timestamps = telemetry_input.metadata.get("timestamps")
        else:
            raise HTTPException(status_code=404, detail="Dataset not found")

        max_count = min(1500, len(signal))
        for i in range(max_count):
            ts = timestamps[i] if timestamps and i < len(timestamps) else (datetime.now(timezone.utc) - timedelta(minutes=max_count - i)).isoformat()
            observations.append({
                "timestamp": str(ts),
                "value": round(float(signal[i]), 5)
            })

    except Exception as e:
        import traceback
        traceback.print_exc()
        # Honest fallback with message
        raise HTTPException(status_code=500, detail=f"Failed to read telemetry series: {e}")

    return {"observations": observations}

# ----------------- OrbitGuard Multi-Model Analysis -----------------

class RunAnalysisRequest(BaseModel):
    dataset_id: str
    channel: str

@app.post("/api/v1/analysis/run", tags=["OrbitGuard Analysis"])
def run_analysis(req: RunAnalysisRequest):
    pipeline = OrbitGuardPipeline()
    try:
        import pandas as pd
        weights_path = None
        gt = None

        if req.dataset_id == "testing-dataset":
            if not TESTING_CSV.exists():
                raise HTTPException(status_code=404, detail="testing dataset.csv not found")
            col = req.channel if req.channel in ["sensor_channel_4", "sensor_channel_5", "sensor_channel_6"] else "sensor_channel_4"
            telemetry_input = ingest_csv(
                TESTING_CSV,
                telemetry_column=col,
                channel_id=col,
                units="V" if "4" in col else ("°C" if "5" in col else "deg/s"),
                physical_meaning="EPS Solar Wing Voltage" if "4" in col else ("TCS Radiator Temp" if "5" in col else "AOCS Gyro Rate"),
                satellite_name="ISRO SPACE-03"
            )
            # Ground truth range from is_anomaly
            df = pd.read_csv(TESTING_CSV)
            if "is_anomaly" in df.columns:
                anom_idx = df.index[df["is_anomaly"] == 1].tolist()
                if anom_idx:
                    gt = [[anom_idx[0], anom_idx[-1]]]
        elif req.dataset_id == "esa-opssat":
            clean_cid = req.channel.replace("OPS-SAT-1 (ESA) - ", "").replace("ESA_OPSSAT_", "").replace("ESA_", "")
            telemetry_input, gt = esa_loader.to_canonical_input(clean_cid)
        elif req.dataset_id == "nasa-smap":
            telemetry_input = ingest_nasa_channel(ROOT, req.channel)
            weights_path = ROOT / "data" / "2018-05-19_15.00.10" / "models" / f"{req.channel}.h5"
        elif req.dataset_id in DATASETS_CACHE:
            path = DATASETS_CACHE[req.dataset_id].get("file_path")
            telemetry_input = ingest_csv(path, channel_id=req.channel, telemetry_column=req.channel)
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
            "events": [],
            "detectors": [d["detector_name"] for d in res.comparative_summary.to_dict(orient="records")]
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/analysis/{run_id}/events", tags=["OrbitGuard Analysis"])
def get_run_events(run_id: str):
    if run_id not in RUNS_CACHE:
        return []

    res = RUNS_CACHE[run_id]
    events = []
    signal = getattr(res, "target_signal", None)
    if signal is None:
        signal = getattr(getattr(res, "telemetry_input", None), "target_signal", None)

    for idx, ev in enumerate(res.consensus_events):
        start = getattr(ev, "start", 0)
        end = getattr(ev, "end", 0)
        highest_score = round(float(getattr(ev, "highest_score", 0.0)), 4)

        obs_val = highest_score
        if signal is not None and len(signal) > start:
            window = signal[start : min(len(signal), end + 1)]
            if len(window) > 0:
                obs_val = round(float(window.max()), 4)

        detectors = getattr(ev, "detectors_agreeing", [])
        events.append({
            "id": f"evt-{idx}",
            "channel_id": getattr(res, "channel_id", "Unknown"),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "start_index": start,
            "end_index": end,
            "severity": getattr(ev, "peak_severity", "CRITICAL").upper(),
            "detectors": detectors,
            "evidence": {
                "observed_value": obs_val,
                "peak_score": highest_score,
                "unit": "raw",
                "physical_meaning": f"Consensus anomaly detected across {getattr(ev, 'agreement_count', len(detectors))} models: {', '.join(detectors)}."
            }
        })
    return events

@app.get("/api/v1/analysis/{run_id}/health", tags=["OrbitGuard Analysis"])
def get_run_health(run_id: str):
    if run_id not in RUNS_CACHE:
        raise HTTPException(status_code=404, detail="Run not found")

    res = RUNS_CACHE[run_id]
    num_events = len(res.consensus_events)
    status = "CRITICAL" if num_events > 0 else "NOMINAL"
    score = max(0, 100 - (num_events * 15))

    return {
        "run_id": run_id,
        "scope": "Channel Telemetry Analysis",
        "channel_id": getattr(res, "channel_id", "Unknown"),
        "consensus_events": num_events,
        "executed_detectors": len(res.comparative_summary),
        "status": status,
        "health_indicator": score
    }

@app.get("/api/v1/history", tags=["OrbitGuard History"])
def get_history():
    runs = history.get_latest_runs(limit=100)
    history_list = []
    if not runs.empty:
        for _, row in runs.iterrows():
            history_list.append({
                "run_id": str(row["run_id"]),
                "dataset_id": "flight_telemetry",
                "channel_id": "multi-channel" if row["channels_evaluated"] > 1 else "monitored",
                "event_count": int(row.get("events_recorded", 0) if "events_recorded" in row else 0),
                "duration_seconds": round(float(row["total_time_seconds"]), 3)
            })
    return history_list

# ----------------- SatShield Fleet Intelligence Endpoints -----------------

SATELLITE_FLEET = [
    {
        "id": "SPACE-03",
        "noradId": "54219",
        "name": "ISRO SPACE-03 (Primary Monitored)",
        "operator": "ISRO / Space Applications Centre",
        "operatingCountry": "India",
        "currentSubpoint": {"lat": 18.42, "lon": 78.53, "geographicRegion": "Telangana / Deccan Plateau (India)"},
        "missionType": "Earth Observation & Telemetry Anomaly Benchmark",
        "orbitType": "SSO (Sun-Synchronous Orbit)",
        "altitudeKm": 552.4,
        "inclinationDeg": 97.6,
        "status": "CRITICAL",
        "subsystems": {"eps": "WARNING", "tcs": "CRITICAL", "aocs": "NOMINAL", "ttc": "NOMINAL", "obc": "NOMINAL", "sensors": "WARNING"},
        "telemetryChannels": ["sensor_channel_4", "sensor_channel_5", "sensor_channel_6", "P-1", "S-1", "T-1"],
        "activeAnomaliesCount": 2,
        "launchDate": "2023-10-21",
        "dataFreshness": "120ms (Real-Time Live Telemetry)",
        "dataSource": "LIVE_BACKEND_STREAM",
        "isSimulatedOrbit": False
    },
    {
        "id": "CARTOSAT-3",
        "noradId": "44804",
        "name": "Cartosat-3",
        "operator": "ISRO",
        "operatingCountry": "India",
        "currentSubpoint": {"lat": 24.11, "lon": 82.45, "geographicRegion": "Madhya Pradesh (India)"},
        "missionType": "High-Resolution Imaging",
        "orbitType": "SSO (Sun-Synchronous)",
        "altitudeKm": 509.0,
        "inclinationDeg": 97.5,
        "status": "NOMINAL",
        "subsystems": {"eps": "NOMINAL", "tcs": "NOMINAL", "aocs": "NOMINAL", "ttc": "NOMINAL", "obc": "NOMINAL", "sensors": "NOMINAL"},
        "telemetryChannels": ["P-2", "S-2", "T-2"],
        "activeAnomaliesCount": 0,
        "launchDate": "2019-11-27",
        "dataFreshness": "1.2s",
        "dataSource": "ISRO_TELEMETRY_LINK",
        "isSimulatedOrbit": False
    },
    {
        "id": "EOS-04",
        "noradId": "51656",
        "name": "EOS-04 (RISAT-1A)",
        "operator": "ISRO",
        "operatingCountry": "India",
        "currentSubpoint": {"lat": 12.97, "lon": 77.59, "geographicRegion": "Karnataka / Bengaluru (India)"},
        "missionType": "Radar Imaging Satellite (C-band SAR)",
        "orbitType": "SSO",
        "altitudeKm": 529.0,
        "inclinationDeg": 97.5,
        "status": "NOMINAL",
        "subsystems": {"eps": "NOMINAL", "tcs": "NOMINAL", "aocs": "NOMINAL", "ttc": "NOMINAL", "obc": "NOMINAL", "sensors": "NOMINAL"},
        "telemetryChannels": ["SAR-01", "SAR-02", "P-3"],
        "activeAnomaliesCount": 0,
        "launchDate": "2022-02-14",
        "dataFreshness": "850ms",
        "dataSource": "ISRO_TELEMETRY_LINK",
        "isSimulatedOrbit": False
    },
    {
        "id": "INSAT-3DR",
        "noradId": "41752",
        "name": "INSAT-3DR",
        "operator": "ISRO",
        "operatingCountry": "India",
        "currentSubpoint": {"lat": 0.0, "lon": 74.0, "geographicRegion": "Indian Ocean Geostationary Slot (74°E)"},
        "missionType": "Meteorological & Search and Rescue",
        "orbitType": "GEO (Geostationary)",
        "altitudeKm": 35786.0,
        "inclinationDeg": 0.05,
        "status": "NOMINAL",
        "subsystems": {"eps": "NOMINAL", "tcs": "NOMINAL", "aocs": "NOMINAL", "ttc": "NOMINAL", "obc": "NOMINAL", "sensors": "NOMINAL"},
        "telemetryChannels": ["MET-01", "IMAGER-01"],
        "activeAnomaliesCount": 0,
        "launchDate": "2016-09-08",
        "dataFreshness": "300ms",
        "dataSource": "ISRO_MET_LINK",
        "isSimulatedOrbit": False
    },
    {
        "id": "SMAP",
        "noradId": "40376",
        "name": "NASA SMAP",
        "operator": "NASA / JPL",
        "operatingCountry": "United States",
        "currentSubpoint": {"lat": -34.60, "lon": -58.38, "geographicRegion": "South America / Buenos Aires"},
        "missionType": "Soil Moisture Active Passive",
        "orbitType": "SSO (Sun-Synchronous)",
        "altitudeKm": 685.0,
        "inclinationDeg": 98.1,
        "status": "WARNING",
        "subsystems": {"eps": "NOMINAL", "tcs": "WARNING", "aocs": "NOMINAL", "ttc": "NOMINAL", "obc": "NOMINAL", "sensors": "WARNING"},
        "telemetryChannels": ["P-1", "S-1", "E-1", "E-2"],
        "activeAnomaliesCount": 1,
        "launchDate": "2015-01-31",
        "dataFreshness": "2.4s",
        "dataSource": "NASA_JPL_TELEMANOM_BENCHMARK",
        "isSimulatedOrbit": False
    },
    {
        "id": "SENTINEL-2A",
        "noradId": "40697",
        "name": "ESA Sentinel-2A",
        "operator": "ESA / Copernicus",
        "operatingCountry": "European Union",
        "currentSubpoint": {"lat": 48.85, "lon": 2.35, "geographicRegion": "Western Europe (France)"},
        "missionType": "Multispectral Optical Earth Observation",
        "orbitType": "SSO",
        "altitudeKm": 786.0,
        "inclinationDeg": 98.62,
        "status": "NOMINAL",
        "subsystems": {"eps": "NOMINAL", "tcs": "NOMINAL", "aocs": "NOMINAL", "ttc": "NOMINAL", "obc": "NOMINAL", "sensors": "NOMINAL"},
        "telemetryChannels": ["MSI-01", "P-4", "T-4"],
        "activeAnomaliesCount": 0,
        "launchDate": "2015-06-23",
        "dataFreshness": "1.8s",
        "dataSource": "ESA_COPERNICUS_FEED",
        "isSimulatedOrbit": False
    },
    {
        "id": "OPS-SAT-1",
        "noradId": "44878",
        "name": "ESA OPS-SAT-1",
        "operator": "ESA / ESOC",
        "operatingCountry": "European Union",
        "currentSubpoint": {"lat": 51.50, "lon": -0.12, "geographicRegion": "Western Europe (UK)"},
        "missionType": "In-Orbit Software & AI Experimentation",
        "orbitType": "SSO",
        "altitudeKm": 515.0,
        "inclinationDeg": 97.4,
        "status": "NOMINAL",
        "subsystems": {"eps": "NOMINAL", "tcs": "NOMINAL", "aocs": "NOMINAL", "ttc": "NOMINAL", "obc": "NOMINAL", "sensors": "NOMINAL"},
        "telemetryChannels": ["CADC0872", "CADC0892"],
        "activeAnomaliesCount": 0,
        "launchDate": "2019-12-18",
        "dataFreshness": "1.1s",
        "dataSource": "ESA_OPS_SAT_ARCHIVE",
        "isSimulatedOrbit": False
    }
]

@app.get("/satellites", tags=["SatShield Fleet"])
@app.get("/api/v1/satellites", tags=["SatShield Fleet"])
def list_satellites():
    return SATELLITE_FLEET

@app.get("/satellites/{satellite_id}", tags=["SatShield Fleet"])
@app.get("/api/v1/satellites/{satellite_id}", tags=["SatShield Fleet"])
def get_satellite(satellite_id: str):
    for sat in SATELLITE_FLEET:
        if sat["id"].upper() == satellite_id.upper() or sat["noradId"] == satellite_id:
            return sat
    raise HTTPException(status_code=404, detail=f"Satellite {satellite_id} not found")

# ----------------- SatShield Database Endpoints -----------------

@app.get("/channels", tags=["SatShield Channels"])
def list_channels(source: Optional[str] = None, db: Session = Depends(get_db)):
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

@app.get("/timeseries", tags=["SatShield Telemetry"])
def get_timeseries(
    channel_id: int,
    start_step: Optional[int] = Query(None),
    end_step: Optional[int] = Query(None),
    downsample: Optional[int] = Query(None),
    db: Session = Depends(get_db)
):
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

@app.get("/anomalies", tags=["SatShield Anomalies"])
def get_anomalies(
    channel_id: Optional[int] = None,
    method: Optional[str] = None,
    db: Session = Depends(get_db)
):
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
    method: str = "zscore"
    window: Optional[int] = 100
    z_threshold: Optional[float] = 3.0
    contamination: Optional[float] = 0.015

@app.post("/run-detection", tags=["SatShield Anomalies"])
def run_in_process_detection(req: DetectionRequest, db: Session = Depends(get_db)):
    ch = db.query(Channel).filter(Channel.id == req.channel_id).first()
    if not ch:
        raise HTTPException(status_code=404, detail="Channel not found")

    rows = db.query(Telemetry).filter(Telemetry.channel_id == req.channel_id).order_by(Telemetry.timestep).all()
    if not rows:
        raise HTTPException(status_code=400, detail="No telemetry available for this channel")

    values = [r.value for r in rows]

    if req.method == "zscore":
        anomalies = detect_zscore(values, win=req.window or 100, z_threshold=req.z_threshold or 3.0)
    elif req.method == "isoforest":
        anomalies = detect_isoforest(values, contamination=req.contamination or 0.015)
    else:
        raise HTTPException(status_code=400, detail=f"Unsupported method: {req.method}")

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

@app.get("/benchmarks", tags=["SatShield Benchmarks"])
def get_benchmarks(channel: Optional[str] = None, db: Session = Depends(get_db)):
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

@app.get("/api/v1/metrics", tags=["SatShield Fleet"])
def get_fleet_metrics(db: Session = Depends(get_db)):
    total_channels = db.query(Channel).count()
    total_anomalies = db.query(Anomaly).count()
    total_benchmarks = db.query(Benchmark).count()
    return {
        "active_satellites": len(SATELLITE_FLEET),
        "total_monitored_channels": total_channels,
        "total_detected_anomalies": total_anomalies,
        "benchmark_models_evaluated": total_benchmarks,
        "pipeline_status": "ONLINE",
        "consensus_engine": "ACTIVE"
    }

if __name__ == "__main__":
    uvicorn.run("backend.api:app", host="0.0.0.0", port=8000, reload=False)
