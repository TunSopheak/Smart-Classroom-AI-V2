"""Phase 30G camera angle and lighting quality helpers.

These helpers estimate whether saved classroom snapshots are likely good enough
for pose-landmark research. They do not run live services, write to the database,
or create dashboard alerts.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

MIN_WIDTH = 640
MIN_HEIGHT = 480
MIN_BRIGHTNESS = 60.0
MAX_BRIGHTNESS = 190.0
MIN_CONTRAST = 25.0
MIN_SHARPNESS = 50.0
LOW_QUALITY_WARNING = "Low-quality frame: AI result is less reliable."


def _safe_float(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def classify_camera_quality(metrics: dict[str, Any]) -> dict[str, Any]:
    """Classify snapshot quality using simple image-quality thresholds."""

    width = _safe_float(metrics.get("width"))
    height = _safe_float(metrics.get("height"))
    brightness = _safe_float(metrics.get("brightness_mean"))
    contrast = _safe_float(metrics.get("contrast_std"))
    sharpness = _safe_float(metrics.get("sharpness_laplacian_var"))

    issues: list[str] = []
    recommendations: list[str] = []

    if width is None or height is None or width < MIN_WIDTH or height < MIN_HEIGHT:
        issues.append("low_resolution")
        recommendations.append("Use at least 640x480 snapshots for pose research.")

    if brightness is None:
        issues.append("brightness_unknown")
        recommendations.append("Recheck the image file because brightness could not be measured.")
    elif brightness < MIN_BRIGHTNESS:
        issues.append("too_dark")
        recommendations.append("Add front/side lighting or move the camera away from backlight.")
    elif brightness > MAX_BRIGHTNESS:
        issues.append("too_bright")
        recommendations.append("Reduce direct light glare and avoid pointing the camera at bright windows.")

    if contrast is None or contrast < MIN_CONTRAST:
        issues.append("low_contrast")
        recommendations.append("Improve subject/background separation and avoid flat dark scenes.")

    if sharpness is None or sharpness < MIN_SHARPNESS:
        issues.append("blurry_or_soft")
        recommendations.append("Stabilize the camera, clean the lens, and avoid motion blur.")

    quality_label = "good" if not issues else "needs_improvement"
    return {
        "quality_label": quality_label,
        "issues": issues,
        "recommendations": recommendations,
        "safe_mode": True,
    }


def classify_live_frame_quality(
    brightness_score: Any,
    blur_score: Any,
) -> dict[str, Any]:
    """Return dashboard-safe quality labels for a sampled browser frame."""

    brightness = _safe_float(brightness_score)
    blur = _safe_float(blur_score)
    low_light = brightness is not None and brightness < MIN_BRIGHTNESS
    blurry = blur is not None and blur < MIN_SHARPNESS

    if brightness is None or blur is None:
        label = "low_quality_frame"
        reason = "Frame quality could not be measured completely."
    elif low_light and blurry:
        label = "low_quality_frame"
        reason = "The sampled frame is dark and blurry."
    elif low_light:
        label = "low_light"
        reason = "The sampled frame is too dark for reliable AI review."
    elif blurry:
        label = "blurry"
        reason = "The sampled frame appears blurry or soft."
    else:
        label = "good"
        reason = "Brightness and sharpness are suitable for sampled analysis."

    is_low_quality = label != "good"
    return {
        "frame_quality_label": label,
        "frame_quality_reason": reason,
        "brightness_score": round(brightness, 3) if brightness is not None else None,
        "blur_score": round(blur, 3) if blur is not None else None,
        "frame_quality_warning": LOW_QUALITY_WARNING if is_low_quality else "",
    }


def evaluate_live_frame_quality(image_bytes: bytes) -> dict[str, Any]:
    """Estimate brightness and Laplacian blur for one sampled camera frame."""

    try:
        import cv2  # type: ignore
        import numpy as np  # type: ignore
    except Exception:  # pragma: no cover - optional dependency path
        return classify_live_frame_quality(None, None)

    image_array = np.frombuffer(image_bytes, dtype=np.uint8)
    frame = cv2.imdecode(image_array, cv2.IMREAD_COLOR)
    if frame is None:
        result = classify_live_frame_quality(None, None)
        result["frame_quality_reason"] = "The sampled frame could not be decoded for quality review."
        return result

    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    return classify_live_frame_quality(
        float(gray.mean()),
        float(cv2.Laplacian(gray, cv2.CV_64F).var()),
    )


def analyze_image_quality(image_path: str | Path) -> dict[str, Any]:
    """Analyze one image file with OpenCV when available."""

    path = Path(image_path)
    if not path.exists() or not path.is_file():
        return {
            "ok": False,
            "phase": "30G",
            "status": "image_not_found",
            "image_path": str(path),
            "safe_mode": True,
        }

    try:
        import cv2  # type: ignore
    except Exception as exc:  # pragma: no cover - optional dependency failure path
        return {
            "ok": False,
            "phase": "30G",
            "status": "opencv_unavailable",
            "image_path": str(path),
            "safe_mode": True,
            "message": str(exc),
        }

    image = cv2.imread(str(path))
    if image is None:
        return {
            "ok": False,
            "phase": "30G",
            "status": "image_read_failed",
            "image_path": str(path),
            "safe_mode": True,
        }

    height, width = image.shape[:2]
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    brightness_mean = float(gray.mean())
    contrast_std = float(gray.std())
    sharpness_laplacian_var = float(cv2.Laplacian(gray, cv2.CV_64F).var())

    metrics = {
        "width": int(width),
        "height": int(height),
        "brightness_mean": round(brightness_mean, 4),
        "contrast_std": round(contrast_std, 4),
        "sharpness_laplacian_var": round(sharpness_laplacian_var, 4),
    }
    classification = classify_camera_quality(metrics)
    return {
        "ok": True,
        "phase": "30G",
        "status": "completed",
        "image_path": str(path),
        "metrics": metrics,
        **classification,
        "generated_behavior_labels": [],
    }


def summarize_camera_quality(rows: list[dict[str, Any]]) -> dict[str, Any]:
    total = len(rows)
    completed = sum(1 for row in rows if row.get("status") == "completed")
    good = sum(1 for row in rows if row.get("quality_label") == "good")
    needs_improvement = sum(1 for row in rows if row.get("quality_label") == "needs_improvement")
    issue_counts: dict[str, int] = {}
    for row in rows:
        for issue in row.get("issues") or []:
            issue_counts[str(issue)] = issue_counts.get(str(issue), 0) + 1

    return {
        "ok": True,
        "phase": "30G",
        "safe_mode": True,
        "total_images": total,
        "completed_images": completed,
        "good_quality_images": good,
        "needs_improvement_images": needs_improvement,
        "issue_counts": issue_counts,
        "generated_behavior_labels": [],
        "message": "Camera quality summary completed in sandbox mode only.",
    }
