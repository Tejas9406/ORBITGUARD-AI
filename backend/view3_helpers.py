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

