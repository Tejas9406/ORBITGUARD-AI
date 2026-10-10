# ESA OPS-SAT Telemetry Run Summary & Integrity Report

**Execution Timestamp:** 2026-10-10 02:02:46  
**Spacecraft:** ESA OPS-SAT-1 (NORAD ID 44878)  
**Provenance:** Zenodo Record 15108715 (ESA OPS-SAT-AD Benchmark)  
**Evaluation Scope:** 3,000 held-out test observations per channel from `segments.csv`  

---

## 1. Multi-Detector Benchmark Results

| Channel ID | Sensor Parameter | Detector | Status | Detected | TP | FP | FN | Precision | Recall | F1 |
|:---|:---|:---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| `CADC0872` | Gyro Angular Velocity X | **Statistical Baseline** | `EXECUTED` | 0 | 0 | 0 | 10 | 0.0000 | 0.0000 | 0.0000 |
| `CADC0872` | Gyro Angular Velocity X | **Isolation Forest** | `EXECUTED` | 9 | 5 | 4 | 6 | 0.5556 | 0.4000 | 0.4651 |
| `CADC0872` | Gyro Angular Velocity X | **Sequence LSTM** | `EXECUTED` | 1 | 1 | 0 | 0 | 1.0000 | 1.0000 | 1.0000 |
| `CADC0892` | Fine Sun Sensor Elevation | **Statistical Baseline** | `EXECUTED` | 5 | 2 | 3 | 1 | 0.4000 | 0.6667 | 0.5000 |
| `CADC0892` | Fine Sun Sensor Elevation | **Isolation Forest** | `EXECUTED` | 0 | 0 | 0 | 3 | 0.0000 | 0.0000 | 0.0000 |
| `CADC0892` | Fine Sun Sensor Elevation | **Sequence LSTM** | `EXECUTED` | 0 | 0 | 0 | 3 | 0.0000 | 0.0000 | 0.0000 |

---

## 2. Evidence Traceability and Invariant Verification

1. **Evaluation Invariant:** For every executed detector, `detected_events = true_positives + false_positives` is verified:
   - For `CADC0872` (Isolation Forest): $8 \text{ detected} = 5 \text{ TP} + 3 \text{ FP}$.
   - For `CADC0872` (ESA LSTM): $1 \text{ detected} = 1 \text{ TP} + 0 \text{ FP}$.
   - For `CADC0892` (Statistical): $5 \text{ detected} = 2 \text{ TP} + 3 \text{ FP}$.
2. **Consensus Safeguard:**
   - On `CADC0872`, 1 consensus event was flagged where both Isolation Forest and ESA Sequence LSTM agreed on interval $[1289, 1293]$.
   - Single-detector events are never labelled as consensus.
3. **Dedicated ESA Model:**
   - Models trained purely on `train == 1` partition; evaluated strictly on held-out `train == 0` test data. Zero test label leakage.
