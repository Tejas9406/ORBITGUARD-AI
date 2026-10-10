"""Evaluation History and Run Tracking for OrbitGuard AI.

Provides SQLite-backed persistent storage for:
- Per-run evaluation results with timestamps and parameters.
- Historical trend analysis across evaluation runs.
- Run comparison and performance regression detection.
"""

from __future__ import annotations

import json
import sqlite3
import time
from contextlib import contextmanager
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd


DEFAULT_DB_PATH = Path(__file__).resolve().parent.parent / "data" / "evaluation_history.sqlite"


@dataclass
class EvaluationRun:
    """Single evaluation run record."""
    run_id: str
    timestamp: str
    channel_id: str
    spacecraft: str
    detector_name: str
    detector_type: str
    evaluation_scope: str
    total_observations: int
    detected_events: int
    ground_truth_events: int
    true_positives: int
    false_positives: int
    false_negatives: int
    precision: Optional[float]
    recall: Optional[float]
    f1_score: Optional[float]
    execution_time_seconds: float
    parameters: Dict[str, Any]
    status: str


class EvaluationHistory:
    """SQLite-backed evaluation history tracker."""

    def __init__(self, db_path: Optional[str | Path] = None):
        self.db_path = Path(db_path) if db_path else DEFAULT_DB_PATH
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    @contextmanager
    def _connect(self):
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def _init_db(self):
        with self._connect() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS evaluation_runs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    run_id TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    channel_id TEXT NOT NULL,
                    spacecraft TEXT DEFAULT 'unknown',
                    detector_name TEXT NOT NULL,
                    detector_type TEXT NOT NULL,
                    evaluation_scope TEXT DEFAULT 'Full Channel',
                    total_observations INTEGER DEFAULT 0,
                    detected_events INTEGER DEFAULT 0,
                    ground_truth_events INTEGER DEFAULT 0,
                    true_positives INTEGER DEFAULT 0,
                    false_positives INTEGER DEFAULT 0,
                    false_negatives INTEGER DEFAULT 0,
                    precision REAL,
                    recall REAL,
                    f1_score REAL,
                    execution_time_seconds REAL DEFAULT 0.0,
                    parameters_json TEXT DEFAULT '{}',
                    status TEXT DEFAULT 'Completed'
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_runs_channel
                ON evaluation_runs(channel_id, detector_name)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_runs_timestamp
                ON evaluation_runs(timestamp)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_runs_run_id
                ON evaluation_runs(run_id)
            """)

    def generate_run_id(self) -> str:
        """Generate a unique run ID based on timestamp."""
        return datetime.now(timezone.utc).strftime("run_%Y%m%d_%H%M%S_") + f"{int(time.time() * 1000) % 10000:04d}"

    def record_run(self, run: EvaluationRun) -> int:
        """Record a single evaluation run. Returns the row ID."""
        with self._connect() as conn:
            cursor = conn.execute("""
                INSERT INTO evaluation_runs (
                    run_id, timestamp, channel_id, spacecraft,
                    detector_name, detector_type, evaluation_scope,
                    total_observations, detected_events, ground_truth_events,
                    true_positives, false_positives, false_negatives,
                    precision, recall, f1_score,
                    execution_time_seconds, parameters_json, status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                run.run_id, run.timestamp, run.channel_id, run.spacecraft,
                run.detector_name, run.detector_type, run.evaluation_scope,
                run.total_observations, run.detected_events, run.ground_truth_events,
                run.true_positives, run.false_positives, run.false_negatives,
                run.precision, run.recall, run.f1_score,
                run.execution_time_seconds,
                json.dumps(run.parameters),
                run.status,
            ))
            return cursor.lastrowid

    def record_batch(self, runs: List[EvaluationRun]) -> int:
        """Record multiple evaluation runs. Returns count inserted."""
        count = 0
        for run in runs:
            self.record_run(run)
            count += 1
        return count

    def get_channel_history(
        self,
        channel_id: str,
        detector_name: Optional[str] = None,
        limit: int = 100,
    ) -> pd.DataFrame:
        """Get evaluation history for a specific channel."""
        with self._connect() as conn:
            if detector_name:
                rows = conn.execute("""
                    SELECT * FROM evaluation_runs
                    WHERE channel_id = ? AND detector_name = ?
                    ORDER BY timestamp DESC LIMIT ?
                """, (channel_id, detector_name, limit)).fetchall()
            else:
                rows = conn.execute("""
                    SELECT * FROM evaluation_runs
                    WHERE channel_id = ?
                    ORDER BY timestamp DESC LIMIT ?
                """, (channel_id, limit)).fetchall()

        if not rows:
            return pd.DataFrame()
        return pd.DataFrame([dict(r) for r in rows])

    def get_run_summary(self, run_id: str) -> pd.DataFrame:
        """Get all results for a specific run."""
        with self._connect() as conn:
            rows = conn.execute("""
                SELECT * FROM evaluation_runs WHERE run_id = ?
                ORDER BY channel_id, detector_name
            """, (run_id,)).fetchall()
        if not rows:
            return pd.DataFrame()
        return pd.DataFrame([dict(r) for r in rows])

    def get_latest_runs(self, limit: int = 10) -> pd.DataFrame:
        """Get the most recent unique run IDs with summary counts."""
        with self._connect() as conn:
            rows = conn.execute("""
                SELECT run_id,
                       MIN(timestamp) as started_at,
                       COUNT(*) as total_evaluations,
                       COUNT(DISTINCT channel_id) as channels_evaluated,
                       COUNT(DISTINCT detector_name) as detectors_used,
                       AVG(CASE WHEN f1_score IS NOT NULL THEN f1_score END) as avg_f1,
                       SUM(execution_time_seconds) as total_time_seconds
                FROM evaluation_runs
                GROUP BY run_id
                ORDER BY started_at DESC
                LIMIT ?
            """, (limit,)).fetchall()
        if not rows:
            return pd.DataFrame()
        return pd.DataFrame([dict(r) for r in rows])

    def compare_runs(self, run_id_a: str, run_id_b: str) -> pd.DataFrame:
        """Compare metrics between two runs."""
        a = self.get_run_summary(run_id_a)
        b = self.get_run_summary(run_id_b)

        if a.empty or b.empty:
            return pd.DataFrame()

        merged = a.merge(
            b,
            on=["channel_id", "detector_name"],
            suffixes=("_run_a", "_run_b"),
            how="outer",
        )

        for metric in ["precision", "recall", "f1_score"]:
            col_a = f"{metric}_run_a"
            col_b = f"{metric}_run_b"
            if col_a in merged.columns and col_b in merged.columns:
                merged[f"{metric}_delta"] = merged[col_b] - merged[col_a]

        return merged

    def get_performance_trends(
        self,
        channel_id: Optional[str] = None,
        detector_name: Optional[str] = None,
    ) -> pd.DataFrame:
        """Get performance trends over time for drift monitoring."""
        with self._connect() as conn:
            conditions = []
            params = []
            if channel_id:
                conditions.append("channel_id = ?")
                params.append(channel_id)
            if detector_name:
                conditions.append("detector_name = ?")
                params.append(detector_name)

            where = f" WHERE {' AND '.join(conditions)}" if conditions else ""
            rows = conn.execute(f"""
                SELECT run_id, timestamp, channel_id, detector_name,
                       detected_events, ground_truth_events,
                       true_positives, false_positives, false_negatives,
                       precision, recall, f1_score, execution_time_seconds
                FROM evaluation_runs
                {where}
                ORDER BY timestamp
            """, params).fetchall()

        if not rows:
            return pd.DataFrame()
        return pd.DataFrame([dict(r) for r in rows])

    def export_csv(self, output_path: str | Path) -> int:
        """Export full history to CSV."""
        with self._connect() as conn:
            rows = conn.execute("SELECT * FROM evaluation_runs ORDER BY timestamp").fetchall()

        if not rows:
            return 0

        df = pd.DataFrame([dict(r) for r in rows])
        df.to_csv(output_path, index=False)
        return len(df)

    def export_json(self, output_path: str | Path) -> int:
        """Export full history to JSON."""
        with self._connect() as conn:
            rows = conn.execute("SELECT * FROM evaluation_runs ORDER BY timestamp").fetchall()

        if not rows:
            return 0

        records = [dict(r) for r in rows]
        Path(output_path).write_text(json.dumps(records, indent=2, default=str), encoding="utf-8")
        return len(records)

    @property
    def total_runs(self) -> int:
        with self._connect() as conn:
            return conn.execute("SELECT COUNT(*) FROM evaluation_runs").fetchone()[0]
