import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from typing import List, Dict, Any

def detect_isoforest(
    values: List[float] | np.ndarray,
    contamination: float = 0.02,
    n_estimators: int = 100,
    roll_win: int = 40,
    gap_tol: int = 2
) -> List[Dict[str, Any]]:
    """
    Multivariate feature Isolation Forest anomaly detector.
    
    Features constructed:
    1. Raw value
    2. Delta (first difference - rate of change)
    3. Rolling mean (local trend)
    4. Rolling std (local volatility)
    """
    arr = np.asarray(values, dtype=float)
    n = len(arr)
    if n < 10:
        return []

    s = pd.Series(arr)
    delta = s.diff().bfill().fillna(0.0)
    roll_mean = s.rolling(roll_win, min_periods=3).mean().bfill().fillna(0.0)
    roll_std = s.rolling(roll_win, min_periods=3).std().bfill().fillna(0.0)

    X = np.column_stack([arr, delta.to_numpy(), roll_mean.to_numpy(), roll_std.to_numpy()])

    # Train Isolation Forest
    model = IsolationForest(
        contamination=contamination,
        n_estimators=n_estimators,
        random_state=42
    )
    model.fit(X)

    # decision_function returns negative for outliers (more negative = more anomalous)
    scores = -model.decision_function(X) # higher = more anomalous
    preds = model.predict(X) == -1       # True for anomalies

    windows = []
    in_run = False
    start_idx = 0
    end_idx = 0
    max_score = 0.0
    gap_count = 0

    for i in range(n):
        if preds[i]:
            if not in_run:
                in_run = True
                start_idx = i
                end_idx = i
                max_score = float(scores[i])
                gap_count = 0
            else:
                end_idx = i
                max_score = max(max_score, float(scores[i]))
                gap_count = 0
        else:
            if in_run:
                gap_count += 1
                if gap_count > gap_tol:
                    # Finalize window
                    peak_val = float(np.max(arr[start_idx : end_idx + 1]))
                    windows.append({
                        "start_step": start_idx,
                        "end_step": end_idx,
                        "score": round(max_score, 3),
                        "method": "isoforest",
                        "severity": "critical" if max_score >= 0.25 else "warning",
                        "evidence": {
                            "observed_peak": round(peak_val, 4),
                            "anomaly_score": round(max_score, 4),
                            "contamination_rate": contamination,
                            "trees": n_estimators,
                            "operational_guidance": "Multivariate isolation path deviation detected. Indicates unexpected variance/rate-of-change pattern."
                        }
                    })
                    in_run = False
                    gap_count = 0

    if in_run:
        peak_val = float(np.max(arr[start_idx : end_idx + 1]))
        windows.append({
            "start_step": start_idx,
            "end_step": end_idx,
            "score": round(max_score, 3),
            "method": "isoforest",
            "severity": "critical" if max_score >= 0.25 else "warning",
            "evidence": {
                "observed_peak": round(peak_val, 4),
                "anomaly_score": round(max_score, 4),
                "contamination_rate": contamination,
                "trees": n_estimators,
                "operational_guidance": "Multivariate isolation path deviation detected. Indicates unexpected variance/rate-of-change pattern."
            }
        })

    return windows
