import numpy as np
import pandas as pd
from typing import List, Dict, Any

def detect_zscore(
    values: List[float] | np.ndarray,
    win: int = 100,
    z_threshold: float = 3.0,
    min_pts: int = 20,
    eps: float = 1e-6
) -> List[Dict[str, Any]]:
    """
    Rolling Z-Score anomaly detector for 1D time-series.
    
    Guarantees:
    - Pure trailing rolling baseline (no temporal lookahead leakage).
    - Constant signal & zero-variance protected (eps guard).
    - Groups contiguous outlier points into cohesive alert windows.
    - Returns structured statistical evidence.
    """
    arr = np.asarray(values, dtype=float)
    n = len(arr)
    if n == 0:
        return []

    s = pd.Series(arr)
    safe_min_pts = max(1, min(min_pts, win, n))
    mu = s.rolling(win, min_periods=safe_min_pts).mean()
    sigma = s.rolling(win, min_periods=safe_min_pts).std()
    # Fallback to series-wide stats if rolling window is empty
    if sigma.isna().all() and n > 1:
        sigma = pd.Series([float(np.std(arr))] * n)
        mu = pd.Series([float(np.mean(arr))] * n)

    # Protect against zero division when signal is constant
    sigma_safe = np.where(sigma.isna() | (sigma < eps), np.nan, sigma)
    z_scores = np.abs((s - mu) / sigma_safe).fillna(0.0).to_numpy()

    is_outlier = z_scores >= z_threshold

    windows = []
    in_run = False
    start_idx = 0
    max_z = 0.0

    for i in range(n):
        if is_outlier[i]:
            if not in_run:
                in_run = True
                start_idx = i
                max_z = float(z_scores[i])
            else:
                max_z = max(max_z, float(z_scores[i]))
        else:
            if in_run:
                end_idx = i - 1
                peak_val = float(np.max(arr[start_idx : end_idx + 1]))
                b_mu = float(mu.iloc[start_idx]) if not np.isnan(mu.iloc[start_idx]) else 0.0
                b_sig = float(sigma.iloc[start_idx]) if not np.isnan(sigma.iloc[start_idx]) else 0.0
                
                windows.append({
                    "start_step": start_idx,
                    "end_step": end_idx,
                    "score": round(max_z, 3),
                    "method": "zscore",
                    "severity": "critical" if max_z >= 4.0 else "warning",
                    "evidence": {
                        "observed_peak": round(peak_val, 4),
                        "baseline_mean": round(b_mu, 4),
                        "baseline_std": round(b_sig, 4),
                        "deviation_sigma": f"+{round(max_z, 2)}σ",
                        "threshold": z_threshold,
                        "window_size": win,
                        "operational_guidance": f"Telemetry exceeded +{round(max_z, 2)}σ beyond {win}-step trailing baseline. Inspect channel trend and correlate with adjacent telemetry."
                    }
                })
                in_run = False

    if in_run:
        end_idx = n - 1
        peak_val = float(np.max(arr[start_idx : end_idx + 1]))
        b_mu = float(mu.iloc[start_idx]) if not np.isnan(mu.iloc[start_idx]) else 0.0
        b_sig = float(sigma.iloc[start_idx]) if not np.isnan(sigma.iloc[start_idx]) else 0.0
        windows.append({
            "start_step": start_idx,
            "end_step": end_idx,
            "score": round(max_z, 3),
            "method": "zscore",
            "severity": "critical" if max_z >= 4.0 else "warning",
            "evidence": {
                "observed_peak": round(peak_val, 4),
                "baseline_mean": round(b_mu, 4),
                "baseline_std": round(b_sig, 4),
                "deviation_sigma": f"+{round(max_z, 2)}σ",
                "threshold": z_threshold,
                "window_size": win,
                "operational_guidance": f"Telemetry exceeded +{round(max_z, 2)}σ beyond {win}-step trailing baseline. Inspect channel trend and correlate with adjacent telemetry."
            }
        })

    return windows
