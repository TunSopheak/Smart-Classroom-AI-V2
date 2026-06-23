"""Saved-snapshot pose sandbox for Phase 30B.

This tool is intentionally isolated from the FastAPI dashboard, database, and
Raspberry Pi services. It lets the team test a real pose model on saved images
before connecting any posture/head-down logic to the live monitoring system.

Usage examples:

    python tools/pose_sandbox.py --image app/static/uploads/iot_snapshots/latest.jpg
    python tools/pose_sandbox.py --image sample.jpg --model models/pose_landmarker.task
    python tools/pose_sandbox.py --image sample.jpg --model models/pose_landmarker.task --pretty

Notes:
- MediaPipe is optional. If it is not installed, the script returns a safe JSON
  status instead of failing the project.
- A Pose Landmarker .task model is required for real inference.
- The script does not generate sleeping/emotion labels. It only reports pose
  landmarks and model-readiness information.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class ImageInputStatus:
    path: str
    exists: bool
    size_bytes: int | None = None
    suffix: str | None = None


def build_image_status(image_path: str | Path) -> ImageInputStatus:
    path = Path(image_path)
    if not path.exists() or not path.is_file():
        return ImageInputStatus(path=str(path), exists=False)
    return ImageInputStatus(
        path=str(path),
        exists=True,
        size_bytes=path.stat().st_size,
        suffix=path.suffix.lower(),
    )


def safe_import_mediapipe() -> tuple[Any | None, str | None]:
    try:
        import mediapipe as mp  # type: ignore
    except Exception as exc:  # pragma: no cover - depends on optional package
        return None, str(exc)
    return mp, None


def safe_import_cv2() -> tuple[Any | None, str | None]:
    try:
        import cv2  # type: ignore
    except Exception as exc:  # pragma: no cover - depends on optional package
        return None, str(exc)
    return cv2, None


def image_metadata(image_path: str | Path) -> dict[str, Any]:
    cv2, error = safe_import_cv2()
    if cv2 is None:
        return {
            "available": False,
            "reason": "opencv_unavailable",
            "message": error or "OpenCV is required to read image metadata.",
        }

    image = cv2.imread(str(image_path))
    if image is None:
        return {
            "available": False,
            "reason": "image_read_failed",
            "message": "OpenCV could not read the image file.",
        }

    height, width = image.shape[:2]
    channels = image.shape[2] if len(image.shape) >= 3 else 1
    return {
        "available": True,
        "width": width,
        "height": height,
        "channels": channels,
    }


def summarize_pose_landmarks(pose_landmarks: list[Any]) -> list[dict[str, Any]]:
    summaries: list[dict[str, Any]] = []
    for pose_index, landmarks in enumerate(pose_landmarks):
        points = list(landmarks)
        visibility_values = [
            float(getattr(point, "visibility", 0.0))
            for point in points
            if getattr(point, "visibility", None) is not None
        ]
        average_visibility = (
            sum(visibility_values) / len(visibility_values) if visibility_values else None
        )
        summaries.append(
            {
                "pose_index": pose_index,
                "landmark_count": len(points),
                "average_visibility": round(average_visibility, 4)
                if average_visibility is not None
                else None,
                "note": "Pose landmarks found. Behavior labels are not generated in Phase 30B.",
            }
        )
    return summaries


def run_pose_landmarker(image_path: str | Path, model_path: str | Path) -> dict[str, Any]:
    """Run MediaPipe Pose Landmarker only when optional inputs are available."""

    image_status = build_image_status(image_path)
    if not image_status.exists:
        return {
            "ok": False,
            "phase": "30B",
            "status": "image_not_found",
            "image": image_status.__dict__,
            "message": "Saved snapshot image was not found.",
        }

    model_file = Path(model_path)
    if not model_file.exists() or not model_file.is_file():
        return {
            "ok": True,
            "phase": "30B",
            "status": "model_required",
            "safe_mode": True,
            "image": image_status.__dict__,
            "image_metadata": image_metadata(image_path),
            "model_path": str(model_file),
            "message": "Pose sandbox is ready, but a MediaPipe Pose Landmarker .task model is required for inference.",
            "generated_behavior_labels": [],
        }

    mp, mp_error = safe_import_mediapipe()
    if mp is None:
        return {
            "ok": True,
            "phase": "30B",
            "status": "dependency_required",
            "safe_mode": True,
            "image": image_status.__dict__,
            "image_metadata": image_metadata(image_path),
            "model_path": str(model_file),
            "message": "MediaPipe is not installed. Install it only in the laptop sandbox environment before running real pose inference.",
            "dependency_error": mp_error,
            "generated_behavior_labels": [],
        }

    cv2, cv2_error = safe_import_cv2()
    if cv2 is None:
        return {
            "ok": True,
            "phase": "30B",
            "status": "dependency_required",
            "safe_mode": True,
            "image": image_status.__dict__,
            "model_path": str(model_file),
            "message": "OpenCV is required to decode the saved snapshot image.",
            "dependency_error": cv2_error,
            "generated_behavior_labels": [],
        }

    try:  # pragma: no cover - requires optional dependency and model file
        image_bgr = cv2.imread(str(image_path))
        if image_bgr is None:
            raise ValueError("OpenCV could not read the image file.")
        image_rgb = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)

        base_options = mp.tasks.BaseOptions(model_asset_path=str(model_file))
        options = mp.tasks.vision.PoseLandmarkerOptions(
            base_options=base_options,
            running_mode=mp.tasks.vision.RunningMode.IMAGE,
            num_poses=4,
        )

        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=image_rgb)
        with mp.tasks.vision.PoseLandmarker.create_from_options(options) as landmarker:
            result = landmarker.detect(mp_image)

        pose_summaries = summarize_pose_landmarks(result.pose_landmarks or [])
        height, width = image_rgb.shape[:2]
        return {
            "ok": True,
            "phase": "30B",
            "status": "completed",
            "safe_mode": True,
            "image": image_status.__dict__,
            "image_metadata": {"available": True, "width": width, "height": height, "channels": 3},
            "model_path": str(model_file),
            "pose_count": len(pose_summaries),
            "pose_summaries": pose_summaries,
            "generated_behavior_labels": [],
            "message": "Pose inference completed on a saved snapshot. No sleeping/emotion labels were generated.",
        }
    except Exception as exc:  # pragma: no cover - defensive optional dependency path
        return {
            "ok": False,
            "phase": "30B",
            "status": "pose_inference_failed",
            "safe_mode": True,
            "image": image_status.__dict__,
            "image_metadata": image_metadata(image_path),
            "model_path": str(model_file),
            "message": "Pose inference failed in sandbox mode. The dashboard and live monitoring are unaffected.",
            "error": str(exc),
            "generated_behavior_labels": [],
        }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run a safe MediaPipe Pose sandbox test on one saved snapshot image."
    )
    parser.add_argument("--image", required=True, help="Path to a saved snapshot image.")
    parser.add_argument(
        "--model",
        default="models/pose_landmarker.task",
        help="Path to a MediaPipe Pose Landmarker .task model file.",
    )
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON output.")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    result = run_pose_landmarker(args.image, args.model)
    print(json.dumps(result, indent=2 if args.pretty else None, ensure_ascii=False))
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
