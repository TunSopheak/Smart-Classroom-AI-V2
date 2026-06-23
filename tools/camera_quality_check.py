"""Phase 30G camera quality check CLI.

Analyze saved snapshots for simple camera-quality signals before repeating pose
quality testing. This remains a sandbox tool and does not affect live services.

Examples:
    python tools/camera_quality_check.py --dir app/static/uploads/iot_snapshots --limit 10 --pretty
    python tools/camera_quality_check.py --dir app/static/uploads/iot_snapshots --csv reports/camera_quality_matrix.csv --pretty
"""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any

from app.services.camera_quality_service import analyze_image_quality, summarize_camera_quality

SUPPORTED_IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png"}


def discover_images(
    directories: list[str] | None = None,
    image_paths: list[str] | None = None,
    limit: int | None = None,
) -> list[Path]:
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
        images = [
            path
            for path in directory.rglob("*")
            if path.is_file() and path.suffix.lower() in SUPPORTED_IMAGE_SUFFIXES
        ]
        for path in sorted(images, key=lambda item: item.stat().st_mtime, reverse=True):
            resolved = str(path.resolve())
            if resolved not in seen:
                seen.add(resolved)
                found.append(path)
                if limit is not None and len(found) >= limit:
                    return found

    return found[:limit] if limit is not None else found


def flatten_row(row: dict[str, Any]) -> dict[str, Any]:
    metrics = row.get("metrics") if isinstance(row.get("metrics"), dict) else {}
    return {
        "image_path": row.get("image_path"),
        "status": row.get("status"),
        "quality_label": row.get("quality_label"),
        "width": metrics.get("width"),
        "height": metrics.get("height"),
        "brightness_mean": metrics.get("brightness_mean"),
        "contrast_std": metrics.get("contrast_std"),
        "sharpness_laplacian_var": metrics.get("sharpness_laplacian_var"),
        "issues": ";".join(row.get("issues") or []),
        "recommendations": ";".join(row.get("recommendations") or []),
    }


def write_csv(rows: list[dict[str, Any]], output_path: str | Path) -> None:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "image_path",
        "status",
        "quality_label",
        "width",
        "height",
        "brightness_mean",
        "contrast_std",
        "sharpness_laplacian_var",
        "issues",
        "recommendations",
    ]
    with path.open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(flatten_row(row))


def run_camera_quality_check(image_paths: list[Path]) -> dict[str, Any]:
    rows = [analyze_image_quality(path) for path in image_paths]
    summary = summarize_camera_quality(rows)
    summary["rows"] = rows
    return summary


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Analyze camera angle/lighting quality for saved classroom snapshots."
    )
    parser.add_argument("--dir", action="append", dest="directories", help="Image folder to scan. Can be used multiple times.")
    parser.add_argument("--image", action="append", dest="image_paths", help="Single image path. Can be used multiple times.")
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
                    "phase": "30G",
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

    result = run_camera_quality_check(images)
    if args.csv_path:
        write_csv(result["rows"], args.csv_path)
        result["csv_path"] = args.csv_path
    print(json.dumps(result, indent=2 if args.pretty else None, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
