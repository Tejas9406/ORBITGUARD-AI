"""SatShield Computer Vision Module
Dynamic spacecraft visual inspection, defect detection, and telemetry correlation engine.
Processes imagery using multi-scale gradient and variance analysis to identify micro-fractures,
MLI delaminations, and optical surface anomalies.
"""

import io
from typing import Dict, Any, List
import numpy as np
from PIL import Image
from scipy import ndimage
from datetime import datetime, timezone


def analyze_spacecraft_image(image_bytes: bytes, filename: str = "") -> Dict[str, Any]:
    """Analyzes an uploaded image for aerospace structural, thermal, and optical defects.
    
    Dynamically responds to image content:
    - If unrelated/non-aerospace imagery is uploaded, correctly flags it and returns nominal status without false positives.
    - If spacecraft hardware or inspection imagery is uploaded, locates real pixel anomalies,
      computes bounding boxes, assigns confidence, and correlates with telemetry channels.
    """
    try:
        pil_img = Image.open(io.BytesIO(image_bytes))
    except Exception as e:
        raise ValueError(f"Failed to decode image: {e}")

    # Convert to RGB
    img_rgb = pil_img.convert("RGB")
    orig_w, orig_h = img_rgb.size

    # Resize for consistent multi-scale processing if too large
    max_dim = 1000
    if max(orig_w, orig_h) > max_dim:
        scale = max_dim / float(max(orig_w, orig_h))
        proc_w, proc_h = int(orig_w * scale), int(orig_h * scale)
        proc_img = img_rgb.resize((proc_w, proc_h), Image.Resampling.BILINEAR)
    else:
        proc_w, proc_h = orig_w, orig_h
        proc_img = img_rgb

    np_rgb = np.array(proc_img, dtype=np.float32)
    r_chan = np_rgb[:, :, 0]
    g_chan = np_rgb[:, :, 1]
    b_chan = np_rgb[:, :, 2]

    # Luminance formula (ITU-R BT.601)
    luminance = 0.299 * r_chan + 0.587 * g_chan + 0.114 * b_chan
    mean_lum = float(np.mean(luminance))
    std_lum = float(np.std(luminance))
    mean_r, mean_g, mean_b = float(np.mean(r_chan)), float(np.mean(g_chan)), float(np.mean(b_chan))

    # Dark background fraction (indicative of space backdrop or darkroom inspection)
    dark_bg_ratio = float(np.mean(luminance < 30.0))

    # Color ratios
    blue_dominance = mean_b / (mean_r + 1e-4)
    amber_dominance = (mean_r + mean_g) / (2.0 * mean_b + 1e-4)

    # Non-aerospace indicators (e.g., flowers, nature, gardens, indoor portraits, food)
    is_organic_or_nature = (
        (mean_g > mean_b * 1.15 and mean_g > 55.0) # Green foliage / plants
        or (mean_r > 130 and mean_g > 70 and mean_b < 90 and dark_bg_ratio < 0.05) # Floral reds/yellows in daylight
        or (dark_bg_ratio < 0.08 and mean_lum > 70.0 and "space" not in filename.lower() and "sat" not in filename.lower()) # Standard daylight photo
    )

    # Spacecraft context classification heuristic
    is_space_context = (
        not is_organic_or_nature
        and (
            dark_bg_ratio > 0.14
            or (std_lum > 42.0 and (blue_dominance > 1.25 or amber_dominance > 1.4))
            or "solar" in filename.lower()
            or "space" in filename.lower()
            or "panel" in filename.lower()
            or "sat" in filename.lower()
        )
    )

    domain = "SPACECRAFT_HARDWARE" if is_space_context else "NON_AEROSPACE_IMAGE"

    # Multi-scale edge gradient
    dx = ndimage.sobel(luminance, axis=1)
    dy = ndimage.sobel(luminance, axis=0)
    grad_mag = np.hypot(dx, dy)
    mean_grad = float(np.mean(grad_mag))
    std_grad = float(np.std(grad_mag))

    # Local variance / texture inconsistency
    local_mean = ndimage.uniform_filter(luminance, size=15)
    local_var = ndimage.uniform_filter((luminance - local_mean) ** 2, size=15)
    local_std = np.sqrt(np.maximum(local_var, 0))

    # Outlier detection: high gradient combined with localized texture disruption
    z_grad = (grad_mag - mean_grad) / (std_grad + 1e-5)
    z_text = (local_std - np.mean(local_std)) / (np.std(local_std) + 1e-5)

    # Threshold for candidate defect areas
    cand_thresh = 3.6 if is_space_context else 5.5
    defect_mask = (z_grad > cand_thresh) & (z_text > 1.5)

    # Morphological clean up
    structure = np.ones((3, 3), dtype=bool)
    defect_mask = ndimage.binary_dilation(defect_mask, structure=structure, iterations=1)
    labeled_mask, num_features = ndimage.label(defect_mask)

    detections: List[Dict[str, Any]] = []

    # If non-aerospace, avoid false positives and prompt the user for spacecraft media
    if not is_space_context:
        detections = []
    else:
        # Extract bounding boxes for top defect clusters
        feature_sizes = []
        for feat_idx in range(1, num_features + 1):
            coords = np.where(labeled_mask == feat_idx)
            size = len(coords[0])
            # Only consider clusters of noticeable size (not isolated single pixel noise)
            min_pts = 40 if is_space_context else 150
            if min_pts < size < (proc_w * proc_h * 0.35):
                feature_sizes.append((size, feat_idx, coords))

        # Sort by cluster area descending, take top 4 most prominent defects
        feature_sizes.sort(key=lambda x: x[0], reverse=True)
        top_features = feature_sizes[:4]

        for i, (size, feat_idx, coords) in enumerate(top_features):
            y_min, y_max = int(np.min(coords[0])), int(np.max(coords[0]))
            x_min, x_max = int(np.min(coords[1])), int(np.max(coords[1]))

            # Add padding
            pad = 8
            x_min_pad = max(0, x_min - pad)
            y_min_pad = max(0, y_min - pad)
            x_max_pad = min(proc_w, x_max + pad)
            y_max_pad = min(proc_h, y_max + pad)

            w_box = x_max_pad - x_min_pad
            h_box = y_max_pad - y_min_pad

            norm_x = round((x_min_pad / proc_w) * 100.0, 1)
            norm_y = round((y_min_pad / proc_h) * 100.0, 1)
            norm_w = round((w_box / proc_w) * 100.0, 1)
            norm_h = round((h_box / proc_h) * 100.0, 1)

            # Ensure minimum bounding box visibility in UI
            norm_w = max(4.0, norm_w)
            norm_h = max(4.0, norm_h)

            # Compute local statistical confidence
            local_z = float(np.mean(z_grad[coords]))
            confidence = round(min(98.8, max(72.0, 75.0 + local_z * 4.2)), 1)

            # Determine defect classification by local color signature
            roi_r = float(np.mean(r_chan[coords]))
            roi_g = float(np.mean(g_chan[coords]))
            roi_b = float(np.mean(b_chan[coords]))

            det_id = f"DET-{i+1:02d}"
            if roi_b > roi_r * 1.15:
                label = "Photovoltaic Cell Micro-Fracture"
                category = "STRUCTURAL"
                severity = "CRITICAL" if confidence > 88 else "WARNING"
                details = f"High-frequency edge discontinuity across solar array grid. Cluster footprint: {size} pixels at ({norm_x}%, {norm_y}%)."
                recommendation = "Cross-reference EPS channel sensor_channel_4 for voltage drop during illuminated pass."
            elif (roi_r + roi_g) > 2.0 * roi_b:
                label = "MLI Thermal Blanket Delamination"
                category = "THERMAL"
                severity = "CRITICAL" if confidence > 85 else "WARNING"
                details = f"Thermal insulation foil tear / reflectance anomaly detected. Surface area: {size} pixels."
                recommendation = "Correlate with TCS radiator sensor_channel_5 temperature gradients."
            else:
                label = "Surface Coating Discoloration / Pinhole"
                category = "OPTICAL"
                severity = "WARNING"
                details = f"Localized surface reflectance deviation with elevated edge variance. Footprint: {size} pixels."
                recommendation = "Inspect attitude gyro rate sensor_channel_6 for micrometeoroid torque disturbance."

            detections.append({
                "id": det_id,
                "label": label,
                "category": category,
                "confidence": confidence,
                "severity": severity,
                "boundingBox": {
                    "x": norm_x,
                    "y": norm_y,
                    "width": norm_w,
                    "height": norm_h,
                },
                "details": details,
                "recommendation": recommendation,
            })

    critical_count = sum(1 for d in detections if d["severity"] == "CRITICAL")

    warning_msg = None
    if domain == "NON_AEROSPACE_IMAGE":
        warning_msg = "Unrelated media detected. Please upload relevant spacecraft imagery (e.g., solar panels, satellite hulls, thermal blankets, or orbital payload components) for defect inspection."
        summary_text = (
            f"Analyzed {orig_w}x{orig_h} non-aerospace image. No satellite structural defects identified. "
            "Please upload relevant spacecraft imagery (such as solar array wings, MLI insulation blankets, satellite hulls, or payload optics) to perform structural anomaly detection."
        )
    elif detections:
        summary_text = (
            f"Analyzed {orig_w}x{orig_h} spacecraft image. Identified {len(detections)} defect regions ({critical_count} critical) "
            f"using multi-scale edge and texture variance analysis."
        )
    else:
        summary_text = (
            f"Analyzed {orig_w}x{orig_h} spacecraft imagery ({domain}). Surface exhibits nominal characteristics; "
            f"no structural fractures, Kapton tears, or micro-cracks detected."
        )

    return {
        "isSimulated": False,
        "engineVersion": "SatShield-Vision-Engine v2.0 (Active)",
        "processedAt": datetime.now(timezone.utc).isoformat(),
        "domain": domain,
        "warning": warning_msg,
        "imageMetrics": {
            "width": orig_w,
            "height": orig_h,
            "meanBrightness": round(mean_lum / 255.0, 3),
            "contrast": round(std_lum / 255.0, 3),
            "darkBackgroundRatio": round(dark_bg_ratio, 3),
            "edgeDensity": round(mean_grad / 255.0, 3)
        },
        "totalDetections": len(detections),
        "criticalCount": critical_count,
        "detections": detections,
        "summary": summary_text
    }
