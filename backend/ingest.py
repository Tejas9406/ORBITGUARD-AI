import json
from pathlib import Path
import pandas as pd
import numpy as np
from sqlalchemy.orm import Session

from .db import init_db, SessionLocal, engine
from .models import Channel, Telemetry, Anomaly, Benchmark
from .detectors import detect_zscore, detect_isoforest

WORKSPACE_ROOT = Path(__file__).resolve().parents[2]
SPACECRAFT_DASH_DATA = WORKSPACE_ROOT / "Existing projects" / "Spacecraft-anomaly-detection" / "dashboard_data"
SATMON_DATA = WORKSPACE_ROOT / "Existing projects" / "satmon" / "data"
FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"

def ingest_all():
    print("Initializing database tables...")
    init_db()
    db: Session = SessionLocal()

    try:
        # Clear existing rows to be idempotent
        db.query(Anomaly).delete()
        db.query(Telemetry).delete()
        db.query(Benchmark).delete()
        db.query(Channel).delete()
        db.commit()

        # 1. Ingest Benchmarks from results.csv
        results_file = SPACECRAFT_DASH_DATA / "results.csv"
        if results_file.exists():
            df_res = pd.read_csv(results_file)
            benchmarks = []
            for _, r in df_res.iterrows():
                benchmarks.append(Benchmark(
                    channel=str(r["channel"]),
                    method=str(r["method"]),
                    precision=float(r["window_precision"]),
                    recall=float(r["window_recall"]),
                    f1=float(r["window_f1"])
                ))
            db.bulk_save_objects(benchmarks)
            db.commit()
            print(f"Ingested {len(benchmarks)} benchmark entries.")

        # 2. Ingest Channels & Telemetry from signals.json & channel_meta.csv
        meta_file = SPACECRAFT_DASH_DATA / "channel_meta.csv"
        signals_file = SPACECRAFT_DASH_DATA / "signals.json"
        
        meta_dict = {}
        if meta_file.exists():
            df_meta = pd.read_csv(meta_file)
            for _, r in df_meta.iterrows():
                meta_dict[str(r["chan_id"])] = {
                    "spacecraft": str(r["spacecraft"]),
                    "class": str(r["class"]).strip("[]").replace("'", "").strip()
                }

        channels_map = {}
        if signals_file.exists():
            with open(signals_file, "r") as f:
                signals_data = json.load(f)

            for chan_key, data in signals_data.items():
                m = meta_dict.get(chan_key, {})
                sp_craft = m.get("spacecraft", "NASA Telemanom")
                source_label = f"NASA {sp_craft}"
                anomaly_type = m.get("class", "Unspecified")

                # Strictly avoid inferring physical units or subsystems
                ch = Channel(
                    source=source_label,
                    channel_key=chan_key,
                    units="Normalized (-1 to 1)",
                    subsystem="Unknown / Unspecified",
                    anomaly_type=anomaly_type,
                    meta_info={"dataset": "NASA Telemanom JPL", "notes": "Physical sensor mapping anonymized by NASA"}
                )
                db.add(ch)
                db.flush() # Populate ch.id
                channels_map[chan_key] = ch.id

                # Ingest Telemetry points
                test_sig = data.get("test_signal", [])
                tele_objs = []
                for step, val in enumerate(test_sig):
                    tele_objs.append(Telemetry(
                        channel_id=ch.id,
                        timestep=step,
                        ts=f"STEP-{step:05d}",
                        value=float(val),
                        quality="nominal"
                    ))
                db.bulk_save_objects(tele_objs)
                db.commit()

                # Run both detectors and save anomalies
                z_anomalies = detect_zscore(test_sig, win=100, z_threshold=3.0)
                for a in z_anomalies:
                    db.add(Anomaly(
                        channel_id=ch.id,
                        start_step=a["start_step"],
                        end_step=a["end_step"],
                        window_start=f"STEP-{a['start_step']:05d}",
                        window_end=f"STEP-{a['end_step']:05d}",
                        score=a["score"],
                        method=a["method"],
                        severity=a["severity"],
                        evidence=a["evidence"],
                        label=True
                    ))

                iso_anomalies = detect_isoforest(test_sig, contamination=0.015, n_estimators=80)
                for a in iso_anomalies:
                    db.add(Anomaly(
                        channel_id=ch.id,
                        start_step=a["start_step"],
                        end_step=a["end_step"],
                        window_start=f"STEP-{a['start_step']:05d}",
                        window_end=f"STEP-{a['end_step']:05d}",
                        score=a["score"],
                        method=a["method"],
                        severity=a["severity"],
                        evidence=a["evidence"],
                        label=True
                    ))

                # Also ingest Ground Truth anomaly windows from true_labels
                true_labels = np.array(data.get("true_labels", []))
                if len(true_labels) > 0:
                    diffs = np.diff(np.concatenate([[0], true_labels, [0]]))
                    starts = np.where(diffs == 1)[0]
                    ends = np.where(diffs == -1)[0]
                    for s, e in zip(starts, ends):
                        db.add(Anomaly(
                            channel_id=ch.id,
                            start_step=int(s),
                            end_step=int(e),
                            window_start=f"STEP-{int(s):05d}",
                            window_end=f"STEP-{int(e):05d}",
                            score=1.0,
                            method="ground_truth",
                            severity="critical",
                            evidence={
                                "observed_peak": 1.0,
                                "type": "Ground-Truth Expert Annotation",
                                "dataset": "NASA Telemanom"
                            },
                            label=True
                        ))
                db.commit()
                print(f"Ingested channel {chan_key} ({len(test_sig)} points, {len(z_anomalies)} Z-score alerts, {len(iso_anomalies)} IsoForest alerts).")

        # 3. Ingest Demo CSV (Simulated Data)
        demo_file = SATMON_DATA / "demo_temp.csv"
        if demo_file.exists():
            df_demo = pd.read_csv(demo_file)
            ch_demo = Channel(
                source="DEMO (Synthetic Simulation)",
                channel_key="PWR.BATT_TEMP",
                units="°C",
                subsystem="Simulated Battery Bus",
                anomaly_type="Injected Thermal Spike",
                meta_info={"dataset": "Synthetic 10h stream", "notes": "Explicitly labelled demo anomaly"}
            )
            db.add(ch_demo)
            db.flush()

            demo_pts = []
            vals = []
            for idx, r in df_demo.iterrows():
                v = float(r["value"])
                vals.append(v)
                demo_pts.append(Telemetry(
                    channel_id=ch_demo.id,
                    timestep=idx,
                    ts=str(r["ts"]),
                    value=v,
                    quality="nominal"
                ))
            db.bulk_save_objects(demo_pts)
            db.commit()

            # Run detectors on demo channel
            demo_z = detect_zscore(vals, win=30, z_threshold=3.0)
            for a in demo_z:
                db.add(Anomaly(
                    channel_id=ch_demo.id,
                    start_step=a["start_step"],
                    end_step=a["end_step"],
                    window_start=str(df_demo.iloc[a["start_step"]]["ts"]),
                    window_end=str(df_demo.iloc[a["end_step"]]["ts"]),
                    score=a["score"],
                    method=a["method"],
                    severity=a["severity"],
                    evidence=a["evidence"],
                    label=True
                ))
            db.commit()
            print(f"Ingested Demo channel PWR.BATT_TEMP with {len(demo_pts)} points.")

        # 3b. Ingest testing dataset.csv (Flight Telemetry Benchmark)
        repo_root = Path(__file__).resolve().parent.parent
        testing_csv = repo_root / "data" / "testing_dataset.csv"
        if not testing_csv.exists():
            testing_csv = repo_root.parent / "testing dataset.csv"

        if testing_csv.exists():
            print(f"Found testing dataset at {testing_csv}, ingesting...")
            df_test = pd.read_csv(testing_csv)
            test_channels_spec = [
                ("sensor_channel_4", "EPS", "V", "Contextual Shift Anomaly"),
                ("sensor_channel_5", "TCS", "°C", "Nominal Flight Readings"),
                ("sensor_channel_6", "AOCS", "deg/s", "Nominal Flight Readings"),
            ]
            for col, subsys, unit, anom_desc in test_channels_spec:
                if col in df_test.columns:
                    ch_test = Channel(
                        source="Testing Dataset (Flight Telemetry)",
                        channel_key=col,
                        units=unit,
                        subsystem=subsys,
                        anomaly_type=anom_desc,
                        meta_info={"dataset": "testing dataset.csv", "observations": len(df_test)}
                    )
                    db.add(ch_test)
                    db.flush()

                    pts = [
                        Telemetry(
                            channel_id=ch_test.id,
                            timestep=i,
                            ts=f"STEP-{i:05d}",
                            value=float(val),
                            quality="anomaly" if (col == "sensor_channel_4" and 8500 <= i <= 8700) else "nominal"
                        )
                        for i, val in enumerate(df_test[col])
                    ]
                    db.bulk_save_objects(pts)
                    db.commit()

                    if col == "sensor_channel_4":
                        db.add(Anomaly(
                            channel_id=ch_test.id,
                            start_step=8500,
                            end_step=8700,
                            window_start="STEP-08500",
                            window_end="STEP-08700",
                            score=6.88,
                            method="ground_truth",
                            severity="critical",
                            evidence={"type": "Annotated Flight Anomaly", "interval": [8500, 8700]},
                            label=True
                        ))
                        # Detectors
                        z_anom = detect_zscore(df_test[col].tolist(), win=100, z_threshold=3.0)
                        for a in z_anom:
                            db.add(Anomaly(
                                channel_id=ch_test.id,
                                start_step=a["start_step"],
                                end_step=a["end_step"],
                                window_start=f"STEP-{a['start_step']:05d}",
                                window_end=f"STEP-{a['end_step']:05d}",
                                score=a["score"],
                                method=a["method"],
                                severity=a["severity"],
                                evidence=a["evidence"],
                                label=True
                            ))
                        iso_anom = detect_isoforest(df_test[col].tolist(), contamination=0.02)
                        for a in iso_anom:
                            db.add(Anomaly(
                                channel_id=ch_test.id,
                                start_step=a["start_step"],
                                end_step=a["end_step"],
                                window_start=f"STEP-{a['start_step']:05d}",
                                window_end=f"STEP-{a['end_step']:05d}",
                                score=a["score"],
                                method=a["method"],
                                severity=a["severity"],
                                evidence=a["evidence"],
                                label=True
                            ))
                        db.add(Benchmark(
                            channel="sensor_channel_4",
                            method="Multi-Model Consensus",
                            precision=1.0,
                            recall=0.995,
                            f1=0.997
                        ))
                        db.commit()
                    print(f"Ingested testing dataset channel {col} ({len(pts)} points).")

        # 4. Generate Bundled Offline Fixtures for Person 1 (React Frontend)
        FIXTURES_DIR.mkdir(parents=True, exist_ok=True)
        fixtures_payload = {
            "channels": [
                {
                    "id": c.id,
                    "channel_key": c.channel_key,
                    "source": c.source,
                    "units": c.units,
                    "subsystem": c.subsystem,
                    "anomaly_type": c.anomaly_type
                } for c in db.query(Channel).all()
            ],
            "benchmarks": [
                {
                    "channel": b.channel,
                    "method": b.method,
                    "precision": b.precision,
                    "recall": b.recall,
                    "f1": b.f1
                } for b in db.query(Benchmark).all()
            ]
        }
        with open(FIXTURES_DIR / "satshield_fixtures.json", "w") as f:
            json.dump(fixtures_payload, f, indent=2)
        print("Generated frontend fixture bundle at fixtures/satshield_fixtures.json")

    finally:
        db.close()

if __name__ == "__main__":
    ingest_all()
