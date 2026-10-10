import pytest
from fastapi.testclient import TestClient
from backend.main import app
from backend.ingest import ingest_all

@pytest.fixture(scope="session", autouse=True)
def setup_database():
    ingest_all()

client = TestClient(app)

def test_healthz():
    res = client.get("/healthz")
    assert res.status_code == 200
    assert res.json()["status"] == "ok"

def test_channels_list():
    res = client.get("/channels")
    assert res.status_code == 200
    channels = res.json()
    assert len(channels) >= 8  # 7 NASA channels + 1 Demo channel
    
    # Verify NASA channels have strictly unknown subsystems and normalized units
    smap_p1 = next(c for c in channels if c["channel_key"] == "P-1")
    assert smap_p1["subsystem"] == "Unknown / Unspecified"
    assert "Normalized" in smap_p1["units"]
    assert smap_p1["point_count"] > 0

def test_timeseries_with_downsampling():
    channels = client.get("/channels").json()
    first_ch = channels[0]["id"]
    
    # Request without downsampling
    res_full = client.get(f"/timeseries?channel_id={first_ch}")
    assert res_full.status_code == 200
    full_data = res_full.json()
    assert full_data["total_points"] > 0
    
    # Request with downsampling to 100 points
    res_down = client.get(f"/timeseries?channel_id={first_ch}&downsample=100")
    assert res_down.status_code == 200
    down_data = res_down.json()
    assert down_data["returned_points"] <= 150
    assert len(down_data["points"]) <= 150

def test_anomalies_schema():
    res = client.get("/anomalies")
    assert res.status_code == 200
    anomalies = res.json()
    assert len(anomalies) > 0
    
    first = anomalies[0]
    assert "score" in first
    assert "method" in first
    assert "evidence" in first

def test_benchmarks():
    res = client.get("/benchmarks")
    assert res.status_code == 200
    benchmarks = res.json()
    assert len(benchmarks) >= 20
    assert any(b["method"] == "Z-score" for b in benchmarks)
    assert any(b["method"] == "Isolation Forest" for b in benchmarks)

def test_run_detection_on_demand():
    channels = client.get("/channels").json()
    first_ch = channels[0]["id"]
    
    payload = {
        "channel_id": first_ch,
        "method": "zscore",
        "window": 50,
        "z_threshold": 3.0
    }
    res = client.post("/run-detection", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    assert "new_anomalies_detected" in data
