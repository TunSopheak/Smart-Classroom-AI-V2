"""Phase 30D posture-candidate sandbox.

This command runs the existing pose sandbox first, then evaluates only cautious
single-image posture candidates. It does not connect to the dashboard, database,
reports, evidence saving, or Raspberry Pi services.

Usage:
    python tools/posture_candidate_sandbox.py --image D:\\test_pose.jpg --model models\\pose_landmarker_full.task --pretty
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from app.services.posture_candidate_service import evaluate_pose_result
from tools.pose_sandbox import run_pose_landmarker


def run_posture_candidate_sandbox(image_path: str | Path, model_path: str | Path) -> dict[str, Any]:
    pose_result = run_pose_landmarker(image_path=image_path, model_path=model_path)
    candidate_result = evaluate_pose_result(pose_result)
    return {
        "ok": bool(candidate_result.get("ok")),
        "phase": "30D",
        "safe_mode": True,
        "pose_status": pose_result.get("status"),
        "pose_count": pose_result.get("pose_count", 0),
        "pose_result_summary": {
            "ok": pose_result.get("ok"),
            "phase": pose_result.get("phase"),
            "status": pose_result.get("status"),
            "image": pose_result.get("image"),
            "image_metadata": pose_result.get("image_metadata"),
            "model_path": pose_result.get("model_path"),
        },
        "candidate_result": candidate_result,
        "generated_behavior_labels": [],
        "message": "Phase 30D sandbox completed. Candidate labels are not dashboard alerts.",
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run a safe posture-candidate sandbox test on one saved snapshot image."
    )
    parser.add_argument("--image", required=True, help="Path to a saved snapshot image.")
    parser.add_argument(
        "--model",
        default="models/pose_landmarker_full.task",
        help="Path to a MediaPipe Pose Landmarker .task model file.",
    )
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON output.")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    result = run_posture_candidate_sandbox(args.image, args.model)
    print(json.dumps(result, indent=2 if args.pretty else None, ensure_ascii=False))
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
