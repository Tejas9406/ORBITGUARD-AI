"""OrbitGuard AI: Satellite Telemetry Health Monitoring & Anomaly Detection Prototype.

Provides end-to-end multi-mission spacecraft telemetry health monitoring, hybrid anomaly
detection benchmarking (Rolling Robust Z-Score, Isolation Forest, and Pretrained Sequence LSTM),
and causal external CSV telemetry ingestion with automated engineering health reports.
"""

from __future__ import annotations

import ast
import json
from pathlib import Path
import sys
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.coordinator import ExecutionStatus, OrbitGuardPipeline
from backend.esa_telemetry import ESATelemetryLoader
from backend.events import group_events
from backend.features import build_features
from backend.health import (
    ChannelHealthSummary,
    SpacecraftFleetHealth,
    assess_channel_health,
    compute_spacecraft_health_overview,
)
from backend.ingestion import SourceType, ingest_nasa_channel
from backend.isolation_forest import run_isolation_forest_detection

DATA = ROOT / "data"
RUN_ID = "2018-05-19_15.00.10"


def parse_cell(value: object) -> list:
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return []
    text = str(value).strip()
    return ast.literal_eval(text) if text else []


def parse_class_cell(value: object) -> list[str]:
    text = str(value).strip().strip("[]")
    return [item.strip() for item in text.split(",") if item.strip()]


@st.cache_data(show_spinner=False)
def load_metadata() -> Tuple[pd.DataFrame, pd.DataFrame, Dict[str, SpacecraftFleetHealth]]:
    labels = pd.read_csv(ROOT / "labeled_anomalies.csv")
    results = pd.read_csv(ROOT / "results" / f"{RUN_ID}.csv")
    labels = labels.drop_duplicates(subset=["chan_id"]).copy()
    results = results.drop_duplicates(subset=["chan_id"]).copy()
    labels["ground_truth"] = labels["anomaly_sequences"].map(parse_cell)
    labels["anomaly_class"] = labels["class"].map(parse_class_cell)
    labels["category"] = "Unknown / unmapped (Anonymized channel)"
    results["predicted_events"] = results["tp_sequences"].map(parse_cell)
    results["false_alarm_events"] = results["fp_sequences"].map(parse_cell)

    joined = labels.merge(results, on=["chan_id", "spacecraft", "anomaly_sequences", "class"], how="inner")
    fleet_health = compute_spacecraft_health_overview(joined)

    # Reconcile ESA OPS-SAT-1 telemetry health from verified report
    esa_health_file = ROOT / "reports" / "esa_telemetry_health.json"
    if esa_health_file.exists():
        try:
            with open(esa_health_file, "r", encoding="utf-8") as f:
                esa_items = json.load(f)
            esa_summaries = [
                ChannelHealthSummary(
                    channel_id=item["channel_id"].replace("ESA_", ""),
                    spacecraft="OPS-SAT-1",
                    subsystem=item.get("subsystem", "ADCS (Attitude Determination & Control)"),
                    status=item.get("status", "Review"),
                    detected_events=int(item.get("detected_events", 0)),
                    reference_events=int(item.get("reference_events", 0)),
                    false_positives=int(item.get("false_positives", 0)),
                    false_negatives=int(item.get("false_negatives", 0)),
                    has_critical_events=bool(item.get("has_critical_events", False)),
                    explanation=item.get("explanation", "Operational ESA telemetry channel"),
                )
                for item in esa_items
            ]
            total_det = sum(c.detected_events for c in esa_summaries)
            total_ref = sum(c.reference_events for c in esa_summaries)
            total_fp = sum(c.false_positives for c in esa_summaries)
            total_fn = sum(c.false_negatives for c in esa_summaries)
            fleet_health["OPS-SAT-1 (ESA)"] = SpacecraftFleetHealth(
                spacecraft="OPS-SAT-1 (ESA)",
                channels_analyzed=len(esa_summaries),
                channels_with_anomalies=sum(1 for c in esa_summaries if c.detected_events > 0),
                channels_requiring_investigation=sum(1 for c in esa_summaries if c.status in ("Review", "High Priority")),
                total_detected_events=total_det,
                total_reference_events=total_ref,
                total_false_alarms=total_fp,
                total_missed_events=total_fn,
                persistent_events_count=sum(1 for c in esa_summaries if c.has_critical_events),
                overall_status="High Priority",
                status_justification=(
                    f"{len(esa_summaries)} channels monitored on live ESA OPS-SAT-1 telemetry stream; "
                    f"{total_det} consensus anomaly events flagged, requiring engineering review."
                ),
                channel_summaries=esa_summaries,
            )
        except Exception:
            pass

    return labels, results, fleet_health


def add_intervals(fig: go.Figure, intervals: list, timeline: list | np.ndarray, color: str, name: str, opacity: float = 0.25) -> None:
    for index, interval in enumerate(intervals):
        start_idx, end_idx = interval
        start_idx = max(0, start_idx)
        end_idx = min(len(timeline) - 1, end_idx)
        if start_idx <= end_idx:
            fig.add_vrect(
                x0=timeline[start_idx],
                x1=timeline[end_idx],
                fillcolor=color,
                opacity=opacity,
                line_width=1,
                line_color=color,
                annotation_text=name if index == 0 else None,
                annotation_position="top left",
            )


def build_mission_timeline_chart(
    telemetry_input,
    result,
    start: int,
    end: int,
    gt_ranges: list,
) -> go.Figure:
    fig = go.Figure()

    signal = telemetry_input.target_signal
    timestamps = telemetry_input.metadata.get("timestamps")

    slice_idx = np.arange(start, end + 1)
    x_vals = [timestamps[i] for i in slice_idx] if timestamps else slice_idx
    y_vals = signal[start : end + 1]

    fig.add_trace(go.Scatter(x=x_vals, y=y_vals, name="Observed telemetry", line=dict(color="#36c5f0")))

    full_timeline = timestamps if timestamps else np.arange(len(signal))

    # Known reference anomalies
    visible_gt = [(max(s, start), min(e, end)) for s, e in gt_ranges if max(s, start) <= min(e, end)]
    add_intervals(fig, visible_gt, full_timeline, "#ef476f", "Known Anomaly")

    # Consensus alerts
    consensus_ranges = [(c.start, c.end) for c in result.consensus_events if max(c.start, start) <= min(c.end, end)]
    add_intervals(fig, consensus_ranges, full_timeline, "#06d6a0", "Consensus Alert")

    x_title = "ISO-8601 Timestamp" if timestamps else "Test-set time step"
    fig.update_layout(height=410, margin=dict(l=10, r=10, t=35, b=15), xaxis_title=x_title, yaxis_title="Telemetry Value")
    return fig


def build_mission_score_chart(
    telemetry_input,
    result,
    start: int,
    end: int,
) -> go.Figure:
    fig = go.Figure()
    timestamps = telemetry_input.metadata.get("timestamps")
    slice_idx = np.arange(start, end + 1)
    x_vals = [timestamps[i] for i in slice_idx] if timestamps else slice_idx

    colors = {
        "Statistical Baseline": "#f8961e",
        "Isolation Forest": "#43aa8b",
        "Pretrained Telemanom LSTM": "#9b5de5",
        "Sequence LSTM": "#9b5de5",
        "ESA-Trained Sequence LSTM": "#9b5de5",
    }

    for det_name, res in result.detector_results.items():
        if res.execution_status == ExecutionStatus.EXECUTED and len(res.scores) > 0:
            c = colors.get(det_name, "#9b5de5")
            s = res.scores[start : end + 1]
            fig.add_trace(go.Scatter(x=x_vals, y=s, name=det_name, line=dict(color=c)))
            fig.add_hline(y=res.threshold_used, line_dash="dot", line_color=c, annotation_text=f"{det_name} Threshold")

    x_title = "ISO-8601 Timestamp" if timestamps else "Test-set time step"
    fig.update_layout(height=300, margin=dict(l=10, r=10, t=35, b=15), xaxis_title=x_title, yaxis_title="Anomaly Score")
    return fig


def build_upload_signal_chart(
    timeline: np.ndarray | pd.Series,
    values: np.ndarray,
    start: int,
    end: int,
    events_df: pd.DataFrame,
    col_name: str,
) -> go.Figure:
    fig = go.Figure()
    sliced_timeline = timeline.iloc[start : end + 1] if isinstance(timeline, pd.Series) else timeline[start : end + 1]
    sliced_values = values[start : end + 1]
    fig.add_trace(
        go.Scatter(
            x=sliced_timeline,
            y=sliced_values,
            name=f"Observed ({col_name})",
            line=dict(color="#36c5f0"),
        )
    )

    if not events_df.empty:
        for idx, row in events_df.iterrows():
            ev_start = int(row["start"])
            ev_end = int(row["end"])
            if ev_end < start or ev_start > end:
                continue
            v_start = max(start, ev_start)
            v_end = min(end, ev_end)
            x0 = timeline.iloc[v_start] if isinstance(timeline, pd.Series) else timeline[v_start]
            x1 = timeline.iloc[v_end] if isinstance(timeline, pd.Series) else timeline[v_end]
            sev = str(row["severity"]).lower()
            color = "#ef476f" if sev == "critical" else "#f77f00" if sev == "high" else "#ffd166"
            fig.add_vrect(
                x0=x0,
                x1=x1,
                fillcolor=color,
                opacity=0.25,
                line_width=1,
                line_color=color,
                annotation_text=f"{str(row['severity']).capitalize()} alert" if idx == 0 else None,
                annotation_position="top left",
            )

    fig.update_layout(
        height=410,
        margin=dict(l=10, r=10, t=35, b=15),
        xaxis_title="Time / Observation Step",
        yaxis_title=f"Telemetry Value ({col_name})",
    )
    return fig


def build_upload_score_chart(
    timeline: np.ndarray | pd.Series,
    zscores: np.ndarray,
    iso_scores: Optional[np.ndarray],
    start: int,
    end: int,
    threshold: float,
) -> go.Figure:
    fig = go.Figure()
    sliced_timeline = timeline.iloc[start : end + 1] if isinstance(timeline, pd.Series) else timeline[start : end + 1]
    sliced_scores = zscores[start : end + 1]
    fig.add_trace(
        go.Scatter(
            x=sliced_timeline,
            y=sliced_scores,
            name="Statistical Robust Z-score",
            line=dict(color="#f8961e"),
        )
    )
    if iso_scores is not None and len(iso_scores) == len(zscores):
        sliced_iso = iso_scores[start : end + 1]
        fig.add_trace(
            go.Scatter(
                x=sliced_timeline,
                y=sliced_iso,
                name="Isolation Forest Score",
                line=dict(color="#43aa8b", dash="dot"),
            )
        )

    fig.add_hline(
        y=threshold,
        line_dash="dot",
        line_color="#f94144",
        annotation_text=f"Alert threshold ({threshold})",
    )
    fig.update_layout(
        height=300,
        margin=dict(l=10, r=10, t=35, b=15),
        xaxis_title="Time / Observation Step",
        yaxis_title="Anomaly Score",
    )
    return fig


# Streamlit Page Configuration
st.set_page_config(
    page_title="OrbitGuard AI — Satellite Telemetry Sentinel",
    page_icon="🛰️",
    layout="wide",
)

labels, results, fleet_health = load_metadata()
joined = labels.merge(results, on=["chan_id", "spacecraft", "anomaly_sequences", "class"], how="inner")

with st.sidebar:
    st.title("🛰️ OrbitGuard AI")
    st.caption("SPACE-03 Satellite Health Sentinel")
    st.divider()
    nav_mode = st.radio(
        "Navigation",
        [
            "🛰️ Mission Fleet Health Overview",
            "🔍 Mission Channel Deep Dive & Multi-Detector Benchmark",
            "📁 Custom Telemetry CSV Ingestion & Hybrid Detection",
        ],
        index=0,
    )
    st.divider()
    st.caption(f"**Fleet Overview:** {len(fleet_health)} Spacecraft Missions Monitored")
    st.caption("• NASA SMAP & MSL Reference Data")
    st.caption("• ESA OPS-SAT-1 Real Telemetry Stream")
    st.caption("• External Ingestion & Health Engine")


# =========================================================================
# VIEW 1: Mission Fleet Health Overview
# =========================================================================
if nav_mode == "🛰️ Mission Fleet Health Overview":
    st.title("🛰️ Spacecraft Fleet Telemetry Health Overview")
    st.caption("Decision-support monitoring overview aggregated across all active spacecraft telemetry streams.")

    with st.expander("📊 Dataset Integrity & Channel Reconciliation Audit", expanded=True):
        col_rec1, col_rec2, col_rec3, col_rec4 = st.columns(4)
        col_rec1.metric(
            "Telemetry Datasets",
            "NASA + ESA",
            help="82 NASA SMAP/MSL .npy channels + Real ESA OPS-SAT-1 UHF telemetry stream.",
        )
        col_rec2.metric(
            "Monitored Missions",
            f"{len(fleet_health)} Spacecraft",
            help="NASA SMAP, NASA MSL, and ESA OPS-SAT-1.",
        )
        col_rec3.metric(
            "Unlabelled Raw Channels",
            "1 (T-10)",
            help="T-10 is present on disk but omitted from labeled_anomalies.csv.",
        )
        col_rec4.metric(
            "Reconciled Duplicates",
            "1 (P-2)",
            help="P-2 had 2 duplicate rows in labeled_anomalies.csv; cleanly deduplicated.",
        )

    col_sc1, col_sc2 = st.columns([1, 3])
    with col_sc1:
        mission_keys = sorted(fleet_health.keys())
        selected_mission = st.selectbox("Select Mission", ["All Missions"] + mission_keys)

    missions_to_show = fleet_health.values() if selected_mission == "All Missions" else [fleet_health[selected_mission]]

    for mission_data in missions_to_show:
        st.subheader(f"Mission: {mission_data.spacecraft}")
        status_color = "red" if mission_data.overall_status == "High Priority" else "orange" if mission_data.overall_status == "Review" else "green"
        st.markdown(
            f"**Operational Telemetry Status:** <span style='font-size:18px; font-weight:bold; color:{status_color};'>{mission_data.overall_status}</span> — {mission_data.status_justification}",
            unsafe_allow_html=True,
        )
        m1, m2, m3, m4, m5, m6 = st.columns(6)
        m1.metric("Channels Monitored", mission_data.channels_analyzed)
        m2.metric("Channels with Alerts", mission_data.channels_with_anomalies)
        m3.metric("Requires Investigation", mission_data.channels_requiring_investigation)
        m4.metric("Total Events Flagged", mission_data.total_detected_events)
        m5.metric("Reference Ground Truth", mission_data.total_reference_events)
        m6.metric("False Alarms / Missed", f"{mission_data.total_false_alarms} / {mission_data.total_missed_events}")

        channel_rows = [c.to_dict() for c in mission_data.channel_summaries]
        ch_df = pd.DataFrame(channel_rows)
        ch_df_display = ch_df[["channel_id", "subsystem", "status", "detected_events", "reference_events", "false_positives", "false_negatives", "explanation"]].copy()
        st.dataframe(ch_df_display, width="stretch")
        st.divider()


# =========================================================================
# VIEW 2: Mission Channel Deep Dive & Multi-Detector Benchmark
# =========================================================================
elif nav_mode == "🔍 Mission Channel Deep Dive & Multi-Detector Benchmark":
    st.title("🔍 Mission Channel Deep Dive & Multi-Detector Benchmark")
    st.caption("Inspect telemetry channels and compare hybrid anomaly detectors over identical evaluation intervals.")

    esa_loader = ESATelemetryLoader()
    try:
        esa_channels = esa_loader.list_channels()
    except Exception:
        esa_channels = []

    nasa_missions = sorted(joined["spacecraft"].unique().tolist())
    all_missions = ["OPS-SAT-1 (ESA)"] + nasa_missions if esa_channels else nasa_missions

    with st.sidebar:
        st.header("Channel Selection")
        mission_choice = st.selectbox("Mission", all_missions)

        if mission_choice == "OPS-SAT-1 (ESA)":
            channel_id = st.selectbox("Channel", esa_channels)
        else:
            eligible = joined[joined["spacecraft"] == mission_choice].sort_values("chan_id")
            channel_id = st.selectbox("Channel", eligible["chan_id"].tolist())
        st.divider()

    @st.cache_data(show_spinner=False)
    def load_and_run(chan_id, mission):
        pipeline = OrbitGuardPipeline()
        if mission == "OPS-SAT-1 (ESA)":
            loader = ESATelemetryLoader()
            telemetry_input, gt_ranges = loader.to_canonical_input(chan_id)
            weights_path = None
        else:
            telemetry_input = ingest_nasa_channel(ROOT, chan_id)
            record = joined[joined["chan_id"] == chan_id].iloc[0]
            gt_ranges = record["ground_truth"]
            weights_path = ROOT / "data" / RUN_ID / "models" / f"{chan_id}.h5"

        result = pipeline.run(
            telemetry_input=telemetry_input,
            ground_truth_ranges=gt_ranges,
            model_weights_path=weights_path,
            record_history=False,
        )
        return telemetry_input, gt_ranges, result

    with st.spinner(f"Loading {channel_id} telemetry and running pipeline..."):
        telemetry_input, gt_ranges, pipeline_result = load_and_run(channel_id, mission_choice)

    st.subheader(f"Channel {channel_id} · {mission_choice}")
    st.markdown(f"**Description:** {telemetry_input.metadata.get('description', 'NASA Telemanom Anonymized Channel')}")
    st.markdown(f"**Provenance:** {telemetry_input.metadata.get('provenance', 'NASA SMAP/MSL Benchmark Dataset')}")

    total_len = len(telemetry_input.target_signal)
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Test Observations", f"{total_len:,}")
    c2.metric("Known Anomaly Events", len(gt_ranges))
    c3.metric("Feature Dimension", telemetry_input.feature_dim)
    c4.metric("Consensus Events Detected", len(pipeline_result.consensus_events))

    default_start = max(0, min((s for s, e in gt_ranges), default=0) - 300)
    default_end = min(total_len - 1, max((e for s, e in gt_ranges), default=total_len - 1) + 300)

    start, end = st.slider("Inspection window", 0, total_len - 1, (default_start, default_end), step=1, key="deep_dive_slider")

    st.plotly_chart(
        build_mission_timeline_chart(telemetry_input, pipeline_result, start, end, gt_ranges),
        width="stretch",
    )
    st.plotly_chart(
        build_mission_score_chart(telemetry_input, pipeline_result, start, end),
        width="stretch",
    )

    st.subheader("⚖️ Multi-Detector Pipeline Consensus & Status")

    status_cols = st.columns(len(pipeline_result.detector_results))
    for i, (name, res) in enumerate(pipeline_result.detector_results.items()):
        with status_cols[i]:
            if res.execution_status == ExecutionStatus.EXECUTED:
                st.success(f"**{name}**\n\nEXECUTED\n\nFound {len(res.events)} events.")
            elif res.execution_status == ExecutionStatus.SKIPPED:
                st.warning(f"**{name}**\n\nSKIPPED\n\n{res.status_reason}")
            else:
                st.error(f"**{name}**\n\nFAILED\n\n{res.status_reason}")

    st.dataframe(pipeline_result.comparative_summary, width="stretch")

    st.subheader("🚨 Consensus Alert List")
    if pipeline_result.consensus_events:
        consensus_df = pd.DataFrame([ast.literal_eval(repr(c.__dict__)) for c in pipeline_result.consensus_events])
        if telemetry_input.metadata.get("timestamps"):
            timestamps = telemetry_input.metadata["timestamps"]
            consensus_df["start_time"] = consensus_df["start"].apply(lambda idx: timestamps[min(idx, len(timestamps) - 1)])
            consensus_df["end_time"] = consensus_df["end"].apply(lambda idx: timestamps[min(idx, len(timestamps) - 1)])
        st.dataframe(consensus_df, width="stretch")
    else:
        st.info("No consensus multi-detector alerts in this channel.")


# =========================================================================
# VIEW 3: Custom Telemetry CSV Ingestion & Hybrid Detection
# =========================================================================
else:
    st.title("📁 Custom Telemetry CSV Ingestion & Hybrid Detection")
    st.caption("Upload and evaluate external satellite or sensor telemetry streams using causal statistical and ML detectors.")

    with st.sidebar:
        st.header("Detector Parameters")
        threshold = st.number_input(
            "Anomaly Threshold",
            min_value=1.0,
            max_value=20.0,
            value=3.5,
            step=0.5,
            help="Z-score threshold for flagging anomaly candidates.",
        )
        window_size = st.number_input(
            "Rolling Window Size",
            min_value=20,
            max_value=2000,
            value=100,
            step=10,
            help="Causal historical window size for rolling median & MAD.",
        )
        run_iso = st.checkbox("Enable Isolation Forest ML Detector", value=True)
        st.divider()
        st.markdown("**Sample Telemetry Options:**")
        sample_choice = st.selectbox(
            "Quick Demo Options",
            ["Upload my own CSV", "Sample Satellite EPS (Solar Panel Voltage)", "Sample Battery System (Battery Temp)", "Sample Attitude Control (Gyro Z)"],
        )
        st.divider()

    df: Optional[pd.DataFrame] = None
    source_name = "Uploaded File"

    if sample_choice == "Upload my own CSV":
        uploaded_file = st.file_uploader(
            "Upload Telemetry CSV",
            type=["csv"],
            help="Upload a CSV file containing numerical telemetry readings.",
        )
        if uploaded_file is not None:
            try:
                df = pd.read_csv(uploaded_file)
                source_name = uploaded_file.name
            except Exception as exc:
                st.error(f"Error parsing uploaded CSV file: {exc}")
                st.stop()
    else:
        sample_path = ROOT / "data" / "uploads" / "upload-98b2a7a86d1c.csv"
        if sample_path.exists():
            df = pd.read_csv(sample_path)
            source_name = sample_choice
        else:
            st.error("Sample dataset file not found on disk.")

    if df is None:
        st.info("👆 Please upload a telemetry CSV file or select a Quick Demo sample above to begin anomaly detection.")
        st.markdown(
            """
            ### Expected CSV Format:
            - **Telemetry column:** Numeric time-series values (e.g. voltage, temperature, vibration, current).
            - **Timestamp column (optional):** ISO-8601 strings, timestamps, or integers.
            - **Minimum length:** At least **20 valid numeric observations** are required.
            """
        )
    else:
        if df.empty:
            st.error("The selected CSV file is empty.")
            st.stop()

        all_cols = list(df.columns)
        numeric_candidates = [
            c for c in all_cols
            if pd.to_numeric(df[c], errors="coerce").notna().sum() >= 20
        ]

        st.subheader("Telemetry Channel & Timestamp Selection")
        col_sel1, col_sel2 = st.columns(2)
        with col_sel1:
            # Default selection based on sample choice
            default_col_idx = 0
            if "Solar" in sample_choice and "solar_panel_voltage" in numeric_candidates:
                default_col_idx = numeric_candidates.index("solar_panel_voltage")
            elif "Battery" in sample_choice and "battery_temp" in numeric_candidates:
                default_col_idx = numeric_candidates.index("battery_temp")
            elif "Gyro" in sample_choice and "gyro_z" in numeric_candidates:
                default_col_idx = numeric_candidates.index("gyro_z")

            telemetry_col = st.selectbox(
                "Telemetry Signal Column (Numeric)*",
                options=numeric_candidates if numeric_candidates else all_cols,
                index=default_col_idx if numeric_candidates else 0,
            )
        with col_sel2:
            timestamp_options = ["None (Use sequential step index)"] + [c for c in all_cols if c != telemetry_col]
            default_ts_idx = 0
            if "timestamp" in timestamp_options:
                default_ts_idx = timestamp_options.index("timestamp")

            timestamp_col = st.selectbox(
                "Timestamp Column (Optional)",
                options=timestamp_options,
                index=default_ts_idx,
            )

        # Validate selected telemetry column
        raw_series = pd.to_numeric(df[telemetry_col], errors="coerce")
        total_rows = len(df)
        invalid_mask = raw_series.isna() | np.isinf(raw_series)
        invalid_count = int(invalid_mask.sum())
        valid_mask = ~invalid_mask
        valid_count = int(valid_mask.sum())

        if invalid_count > 0:
            st.warning(
                f"⚠️ **Data Quality Notice:** Found {invalid_count} missing or non-numeric observation(s) "
                f"out of {total_rows} total rows ({invalid_count / total_rows:.1%}). "
                "These invalid rows were excluded transparently before baseline analysis."
            )

        if valid_count < 20:
            st.error(
                f"❌ **Validation Error:** At least 20 valid numeric observations are required "
                f"for rolling baseline analysis. Found only {valid_count} valid value(s)."
            )
            st.stop()

        clean_values = raw_series[valid_mask].to_numpy(dtype=np.float64)

        if timestamp_col != "None (Use sequential step index)":
            raw_timestamps = df.loc[valid_mask, timestamp_col].reset_index(drop=True)
            timeline = raw_timestamps
        else:
            raw_timestamps = None
            timeline = np.arange(len(clean_values))

        effective_window = max(20, min(int(window_size), len(clean_values)))

        # 1. Statistical Baseline
        features_df = build_features(clean_values, window=effective_window)
        zscores = features_df["robust_zscore"].to_numpy()
        events_df = group_events(zscores, threshold=float(threshold))

        # 2. Isolation Forest (if enabled)
        iso_scores = None
        if run_iso and len(clean_values) >= 30:
            try:
                split_idx = max(20, len(clean_values) // 2)
                train_part = clean_values[:split_idx]
                test_part = clean_values
                iso_scores, _ = run_isolation_forest_detection(train_part, test_part, threshold=float(threshold))
            except Exception as e:
                st.caption(f"Isolation Forest notice: {e}")

        st.subheader("Telemetry Analysis Overview")
        col_m1, col_m2, col_m3, col_m4 = st.columns(4)
        col_m1.metric("Valid Observations", f"{len(clean_values):,}")
        flagged_points_count = int((zscores >= float(threshold)).sum())
        col_m2.metric("Flagged Points (Statistical)", flagged_points_count)
        col_m3.metric("Detected Anomaly Events", len(events_df))
        peak_score = float(np.max(zscores)) if len(zscores) > 0 else 0.0
        col_m4.metric("Peak Anomaly Score", f"{peak_score:.2f}")

        # Inspection window slider
        start, end = st.slider(
            "Inspection window",
            0,
            len(clean_values) - 1,
            (0, len(clean_values) - 1),
            step=1,
            key="upload_slider",
        )

        st.plotly_chart(
            build_upload_signal_chart(timeline, clean_values, start, end, events_df, telemetry_col),
            width="stretch",
        )
        st.plotly_chart(
            build_upload_score_chart(timeline, zscores, iso_scores, start, end, float(threshold)),
            width="stretch",
        )

        st.subheader("Detected Anomaly Incidents")
        if events_df.empty:
            st.success(
                f"✅ No anomaly events detected exceeding score threshold {threshold}. "
                "The telemetry stream appears consistent with its rolling baseline."
            )
        else:
            display_events = events_df.copy()
            display_events["duration"] = display_events["end"] - display_events["start"] + 1
            if raw_timestamps is not None:
                display_events["start_timestamp"] = display_events["start"].apply(lambda i: str(raw_timestamps.iloc[i]))
                display_events["end_timestamp"] = display_events["end"].apply(lambda i: str(raw_timestamps.iloc[i]))
                cols_order = ["start", "end", "start_timestamp", "end_timestamp", "duration", "flagged_points", "peak_score", "severity"]
            else:
                cols_order = ["start", "end", "duration", "flagged_points", "peak_score", "severity"]

            display_events = display_events[[c for c in cols_order if c in display_events.columns]]
            st.dataframe(display_events, width="stretch")

        # =====================================================================
        # EXECUTIVE SATELLITE HEALTH REVIEW & HEALTH REPORT (Step 1155, 1181, 1239)
        # =====================================================================
        st.subheader("📋 Executive Satellite Health Review & Diagnostic Assessment")

        critical_count = sum(1 for _, row in events_df.iterrows() if str(row.get("severity", "")).lower() == "critical")
        num_events = len(events_df)
        stream_stability_pct = max(0.0, 100.0 * (1.0 - (flagged_points_count / max(1, len(clean_values)))))

        if critical_count > 0 or num_events >= 3:
            health_status = "High Priority"
            health_badge_color = "red"
            health_narrative = (
                f"Critical operational deviations flagged: {num_events} distinct anomaly sequence(s) detected, "
                f"including {critical_count} critical incident(s) with peak Z-score {peak_score:.2f}. "
                "Immediate telemetry monitoring and subsystem engineering evaluation are required."
            )
        elif num_events > 0:
            health_status = "Review"
            health_badge_color = "orange"
            health_narrative = (
                f"Minor telemetry anomalies detected: {num_events} transient anomaly sequence(s) flagged "
                f"(Peak anomaly Z-score: {peak_score:.2f}). Subsystem parameters should be checked during the next orbital pass."
            )
        else:
            health_status = "Normal"
            health_badge_color = "green"
            health_narrative = (
                "Telemetry stream operates fully within nominal bounds. Zero deviations exceed the operational baseline threshold."
            )

        st.markdown(
            f"**Operational Telemetry Status:** <span style='font-size:18px; font-weight:bold; color:{health_badge_color};'>{health_status}</span> — {health_narrative}",
            unsafe_allow_html=True,
        )

        with st.container():
            h_col1, h_col2, h_col3, h_col4 = st.columns(4)
            h_col1.metric("Subsystem Channel", telemetry_col)
            h_col2.metric("Telemetry Stability", f"{stream_stability_pct:.1f}%")
            h_col3.metric("Critical Incidents", critical_count)
            h_col4.metric("Operational Status", health_status)

        # Engineering Root-Cause & Actionable Findings
        with st.expander("🔬 Subsystem Engineering Diagnostics & Remediation", expanded=True):
            st.markdown(f"**Source Stream:** `{source_name}` · **Channel:** `{telemetry_col}`")
            if num_events == 0:
                st.markdown(
                    "• **Nominal Telemetry Baseline:** Signal dynamics are stable without unexpected variance shifts or statistical drift.\n"
                    "• **Action:** Routine mission operations. Continue standard telemetry downlink."
                )
            else:
                findings = []
                if peak_score > 6.0:
                    findings.append("• **High-Magnitude Excursion:** Extreme peak deviation indicates possible sensor saturation, transient power surge, or actuator step change.")
                max_duration = int(events_df["duration"].max()) if not events_df.empty else 0
                if max_duration > 20:
                    findings.append(f"• **Persistent Deviation:** Long-duration anomaly sequence ({max_duration} time steps) suggests sustained subsystem thermal drift or impedance variation.")
                else:
                    findings.append("• **Transient Jitter:** Short-duration anomaly sequence consistent with bus noise, telemetry frame loss, or switching transients.")

                findings.append("• **Operator Recommendation:** Correlate detected timestamps with ground commanding log, orbital eclipse schedule, and attitude maneuver timeline.")
                findings.append("• **Flight Controller Action:** If anomalous behavior persists, initiate secondary sensor telemetry review and prepare ground command for redundant sensor cross-strapping.")
                st.markdown("\n".join(findings))

        # Downloadable Health Report Artifacts
        col_dl1, col_dl2 = st.columns(2)
        report_dict = {
            "source_stream": source_name,
            "telemetry_column": telemetry_col,
            "operational_status": health_status,
            "status_justification": health_narrative,
            "stability_index_percent": round(stream_stability_pct, 2),
            "valid_observations": len(clean_values),
            "flagged_points": flagged_points_count,
            "anomaly_events_count": num_events,
            "critical_events_count": critical_count,
            "peak_score": round(peak_score, 4),
            "threshold_used": float(threshold),
            "rolling_window_used": int(window_size),
            "events": events_df.to_dict(orient="records"),
        }

        with col_dl1:
            st.download_button(
                label="📥 Download Health Review Report (JSON)",
                data=json.dumps(report_dict, indent=2),
                file_name=f"satellite_health_report_{telemetry_col}.json",
                mime="application/json",
            )

        with col_dl2:
            md_summary = (
                f"# Satellite Telemetry Health Audit Report\n\n"
                f"**Source:** {source_name}\n"
                f"**Channel:** {telemetry_col}\n"
                f"**Status:** {health_status}\n\n"
                f"## Executive Summary\n{health_narrative}\n\n"
                f"## Key Metrics\n"
                f"- **Observations Analyzed:** {len(clean_values):,}\n"
                f"- **Stream Stability Index:** {stream_stability_pct:.1f}%\n"
                f"- **Anomaly Events Flagged:** {num_events}\n"
                f"- **Critical Severity Incidents:** {critical_count}\n"
                f"- **Peak Anomaly Score:** {peak_score:.2f}\n"
            )
            st.download_button(
                label="📄 Download Executive Summary (Markdown)",
                data=md_summary,
                file_name=f"satellite_health_summary_{telemetry_col}.md",
                mime="text/markdown",
            )

        st.subheader("Model Evaluation & Limitations")
        st.info(
            "ℹ️ **Evaluation Note:** Ground-truth anomaly labels are not supplied for this external dataset. "
            "Supervised performance metrics (**Precision**, **Recall**, **F1 Score**, and **False Alarm Rates**) "
            "cannot be computed without verified expert reference labels."
        )
        st.caption(
            "**Architecture Note:** For arbitrary single-column CSV uploads, Statistical Baseline and Isolation Forest detectors "
            "are deployed. The pretrained Telemanom LSTM is not applied because it strictly requires 25-dimensional (SMAP) or "
            "55-dimensional (MSL) multivariate telemetry inputs."
        )
