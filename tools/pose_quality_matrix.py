"""Phase 30E pose quality testing matrix.

Run the Phase 30D posture-candidate sandbox across many saved images and export
a small JSON/CSV matrix. This remains a research-only tool: it does not update
the dashboard, database, reports, attendance, evidence, or Raspberry Pi service.

Usage examples:
    python tools/pose_quality_matrix.py --dir app/static/uploads/iot_snapshots --model models/pose_landmarker_full.task --pretty
    python tools/pose_quality_matrix.py --image D:\\test_pose.jpg --model models\\pose_landmarker_full.task --csv reports\\pose_quality_matrix.csv
"""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any

from tools.posture_candidate_sandbox import run_posture_candidate_sandbox

SUPPORTED_IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png"}
GOOD_VISIBILITY_THRESHOLD = 0.50
WEAK_VISIBILITY_THRESHOLD = 0.30


def discover_images(
    directories: list[str] | None = None,
    image_paths: list[str] | None = None,
    limit: int | None = None,
) -> list[Path]:
    """Return unique image paths from explicit files and folders."""

    found: list[Path] = []
    seen: set[str] = set()

    for raw_path in image_paths or []:
        path = Path(raw_path)
        if path.is_file() and path.suffix.lower() in SUPPORTED_IMAGE_SUFFIXES:
            resolved = str(path.resolve())
            if resolved not in seen:
                seen.add(resolved)
                found.append(path)

    for raw_directory in directories or []:
        directory = Path(raw_directory)
        if not directory.exists() or not directory.is_dir():
            continue
        for path in sorted(directory.rglob("*"), key=lambda item: item.stat().st_mtime, reverse=True):
            if path.is_file() and path.suffix.lower() in SUPPORTED_IMAGE_SUFFIXES:
                resolved = str(path.resolve())
                if resolved not in seen:
                    seen.add(resolved)
                    found.append(path)
                    if limit is not None and len(found) >= limit:
                        return found

    return found[:limit] if limit is not None else found


def quality_label(pose_count: int, average_visibility: float | None) -> str:
    if pose_count <= 0:
        return "not_detected"
    if average_visibility is None:
        return "unknown_visibility"
    if average_visibility >= GOOD_VISIBILITY_THRESHOLD:
        return "good"
    if average_visibility >= WEAK_VISIBILITY_THRESHOLD:
        return "weak"
    return "poor"


def first_posture_candidate(result: dict[str, Any]) -> dict[str, Any]:
    candidate_result = result.get("candidate_result")
    if not isinstance(candidate_result, dict):
        return {}
    candidates = candidate_result.get("posture_candidates")
    if isinstance(candidates, list) and candidates:
        candidate = candidates[0]
        return candidate if isinstance(candidate, dict) else {}
    return {}


def summarize_matrix_result(image_path: str | Path, result: dict[str, Any]) -> dict[str, Any]:
    candidate = first_posture_candidate(result)
    pose_count = int(result.get("pose_count") or 0)

    average_visibility = None
    pose_summaries = result.get("pose_summaries")
    if isinstance(pose_summaries, list) and pose_summaries:
        first_summary = pose_summaries[0]
        if isinstance(first_summary, dict):
            try:
                average_visibility = float(first_summary.get("average_visibility"))
            except (TypeError, ValueError):
                average_visibility = None

    # Phase 30D result intentionally hides full pose summaries, so prefer candidate
    # readiness when average visibility is not exposed.
    candidate_label = str(candidate.get("label") or "none")
    candidate_confidence = candidate.get("confidence")
    candidate_delta = candidate.get("nose_to_shoulder_delta")

    return {
        "image_path": str(image_path),
        "ok": bool(result.get("ok")),
        "phase": "30E",
        "pose_status": result.get("pose_status"),
        "pose_count": pose_count,
        "quality_label": quality_label(pose_count, average_visibility),
        "average_visibility": average_visibility,
        "candidate_label": candidate_label,
        "candidate_confidence": candidate_confidence,
        "nose_to_shoulder_delta": candidate_delta,
        "safe_mode": True,
        "generated_behavior_labels": [],
    }


def run_pose_quality_matrix(image_paths: list[Path], model_path: str | Path) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    for image_path in image_paths:
        sandbox_result = run_posture_candidate_sandbox(image_path, model_path)
        row = summarize_matrix_result(image_path, sandbox_result)
        rows.append(row)

    total = len(rows)
    detected = sum(1 for row in rows if int(row.get("pose_count") or 0) > 0)
    good = sum(1 for row in rows if row.get("quality_label") == "good")
    weak = sum(1 for row in rows if row.get("quality_label") == "weak")
    not_detected = sum(1 for row in rows if row.get("quality_label") == "not_detected")

    return {
        "ok": True,
        "phase": "30E",
        "safe_mode": True,
        "total_images": total,
        "pose_detected_images": detected,
        "good_quality_images": good,
        "weak_quality_images": weak,
        "not_detected_images": not_detected,
        "generated_behavior_labels": [],
        "rows": rows,
        "message": "Pose quality matrix completed in sandbox mode only. No dashboard alerts were created.",
    }


def write_csv(rows: list[dict[str, Any]], output_path: str | Path) -> None:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "image_path",
        "ok",
        "phase",
        "pose_status",
        "pose_count",
        "quality_label",
        "average_visibility",
        "candidate_label",
        "candidate_confidence",
        "nose_to_shoulder_delta",
        "safe_mode",
    ]
    with path.open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key) for key in fieldnames})


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run a safe pose-quality testing matrix across multiple images."
    )
    parser.add_argument("--dir", action="append", dest="directories", help="Image folder to scan. Can be used multiple times.")
    parser.add_argument("--image", action="append", dest="image_paths", help="Single image path. Can be used multiple times.")
    parser.add_argument("--model", default="models/pose_landmarker_full.task", help="MediaPipe Pose Landmarker .task model path.")
    parser.add_argument("--limit", type=int, default=10, help="Maximum images to evaluate. Default: 10.")
    parser.add_argument("--csv", dest="csv_path", help="Optional CSV output path.")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON output.")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    images = discover_images(
        directories=args.directories,
        image_paths=args.image_paths,
        limit=args.limit,
    )
    if not images:
        print(
            json.dumps(
                {
                    "ok": False,
                    "phase": "30E",
                    "status": "no_images_found",
                    "safe_mode": True,
                    "message": "No jpg/jpeg/png images were found. Provide --image or --dir.",
                    "generated_behavior_labels": [],
                },
                indent=2 if args.pretty else None,
                ensure_ascii=False,
            )
        )
        return 1

    result = run_pose_quality_matrix(images, args.model)
    if args.csv_path:
        write_csv(result["rows"], args.csv_path)
        result["csv_path"] = args.csv_path
    print(json.dumps(result, indent=2 if args.pretty else None, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
