"""Convert point-level anomaly scores into operator-friendly event windows."""

from __future__ import annotations

import numpy as np
import pandas as pd


def _record(points: list[int], scores: np.ndarray, min_points: int) -> dict | None:
    if len(points) < min_points:
        return None
    peak = float(np.max(np.asarray(scores)[points]))
    severity = "critical" if peak >= 8 or len(points) >= 25 else "high" if peak >= 5 else "medium"
    return {"start": points[0], "end": points[-1], "flagged_points": len(points), "peak_score": round(peak, 4), "severity": severity}


def group_events(scores: np.ndarray, threshold: float = 3.5, max_gap: int = 5, min_points: int = 3) -> pd.DataFrame:
    """Group nearby anomalous steps and remove isolated one-point alert noise."""
    flagged = np.flatnonzero(np.asarray(scores) >= threshold)
    if len(flagged) == 0:
        return pd.DataFrame(columns=["start", "end", "flagged_points", "peak_score", "severity"])
    groups, current = [], [int(flagged[0])]
    for point in flagged[1:]:
        if int(point) - current[-1] <= max_gap + 1:
            current.append(int(point))
        else:
            groups.append(current)
            current = [int(point)]
    groups.append(current)
    return pd.DataFrame([record for group in groups if (record := _record(group, scores, min_points)) is not None])
