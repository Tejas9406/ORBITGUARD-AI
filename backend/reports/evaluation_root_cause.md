# Evaluation Root Cause Analysis

## Defect Identified
The evaluation function `evaluate_event_detection` in `backend/evaluation.py` previously contained a critical event-matching defect that broke the mathematical invariants `predicted = TP + FP` and `eligible_ground_truth = TP + FN`.

Specifically, the function independently calculated:
- `gt_caught`: A count of distinct reference events that overlapped with ANY predicted event.
- `det_valid`: A count of predicted events that overlapped with ANY reference event.

It then derived false negatives via `FN = total_gt - gt_caught` and false positives via `FP = total_predicted - det_valid`. It incorrectly set `TP = det_valid`.

This disjointed counting approach led to mathematically impossible states. For example, if a detector produced exactly 1 prediction that happened to overlap 1 reference event in a dataset of 23 anomalies, the script would record `TP = 1`, `FN = 0` (erroneously assigning a 100% recall), and `FP = 0`. The true false negative count was completely decoupled from the reported TP.

## Repair Implemented
A strict chronological one-to-one matching algorithm was implemented in `evaluate_event_detection`. 
The algorithm sorts the ground-truth reference ranges and iterates over each detected event, assigning it to the earliest overlapping unmatched reference event. 
- True Positives (`TP`) strictly count the number of these successfully matched 1:1 pairs.
- False Positives (`FP`) strictly count predictions that failed to match.
- False Negatives (`FN`) strictly equal `total_gt - TP`.

This definitively enforces the invariants `predicted = TP + FP` and `eligible_gt = TP + FN` and accurately reflects a detector's actual recall performance. The `validate_compatibility.py` script and `test_compatibility_regressions.py` tests have also been updated to aggressively enforce these invariants on every evaluation payload, guaranteeing this logic cannot silently regress.
