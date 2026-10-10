else:
    st.title("ðŸ“ Custom Telemetry CSV Ingestion & Hybrid Detection")
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

    uploaded_file = st.file_uploader(
        "Upload Telemetry CSV",
        type=["csv"],
        help="Upload a CSV file containing numerical telemetry readings.",
    )

    if uploaded_file is None:
        st.info("ðŸ‘† Please upload a telemetry CSV file to begin anomaly detection.")
        st.markdown(
            """
            ### Expected CSV Format:
            - **Telemetry column:** Numeric time-series values (e.g. voltage, temperature, vibration, current).
            - **Timestamp column (optional):** ISO-8601 strings, timestamps, or integers.
            - **Minimum length:** At least **20 valid numeric observations** are required.
            """
        )
    else:
        try:
            df = pd.read_csv(uploaded_file)
        except Exception as exc:
            st.error(f"Error parsing uploaded CSV file: {exc}")
            st.stop()

        if df.empty:
            st.error("The uploaded CSV file is empty.")
            st.stop()

        all_cols = list(df.columns)
        numeric_candidates = [
            c for c in all_cols
            if pd.to_numeric(df[c], errors="coerce").notna().sum() >= 20
        ]

        st.subheader("Telemetry Channel & Timestamp Selection")
        col_sel1, col_sel2 = st.columns(2)
        with col_sel1:
            telemetry_col = st.selectbox(
                "Telemetry Signal Column (Numeric)*",
                options=numeric_candidates if numeric_candidates else all_cols,
            )
        with col_sel2:
            timestamp_options = ["None (Use sequential step index)"] + [c for c in all_cols if c != telemetry_col]
            timestamp_col = st.selectbox(
                "Timestamp Column (Optional)",
                options=timestamp_options,
                index=0,
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
                f"âš ï¸ **Data Quality Notice:** Found {invalid_count} missing or non-numeric observation(s) "
                f"out of {total_rows} total rows ({invalid_count / total_rows:.1%}). "
                "These invalid rows were excluded transparently before baseline analysis."
            )

        if valid_count < 20:
            st.error(
                f"âŒ **Validation Error:** At least 20 valid numeric observations are required "
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
                # Use first 50% as nominal training baseline
                split_idx = max(20, len(clean_values) // 2)
                train_part = clean_values[:split_idx]
                test_part = clean_values
                iso_scores, _ = run_isolation_forest_detection(train_part, test_part, threshold=float(threshold))
            except Exception as e:
                st.caption(f"Isolation Forest notice: {e}")

        st.subheader("Telemetry Analysis Overview")
        col_m1, col_m2, col_m3, col_m4 = st.columns(4)
        col_m1.metric("Valid Observations", f"{len(clean_values):,}")
        col_m2.metric("Flagged Points (Statistical)", int((zscores >= float(threshold)).sum()))
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
            use_container_width=True,
        )
        st.plotly_chart(
            build_upload_score_chart(timeline, zscores, iso_scores, start, end, float(threshold)),
            use_container_width=True,
        )

        st.subheader("Detected Anomaly Incidents")
        if events_df.empty:
            st.success(
                f"âœ… No anomaly events detected exceeding score threshold {threshold}. "
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
            st.dataframe(display_events, use_container_width=True)

        st.subheader("Model Evaluation & Limitations")
        st.info(
            "â„¹ï¸ **Evaluation Note:** Ground-truth anomaly labels are not supplied for this uploaded dataset. "
            "Supervised performance metrics (**Precision**, **Recall**, **F1 Score**, and **False Alarm Rates**) "
            "cannot be computed without verified expert reference labels."
        )
        st.caption(
            "**Architecture Note:** For arbitrary single-column CSV uploads, Statistical Baseline and Isolation Forest detectors "
            "are deployed. The pretrained Telemanom LSTM is not applied because it strictly requires 25-dimensional (SMAP) or "
            "55-dimensional (MSL) multivariate telemetry inputs."
        )
