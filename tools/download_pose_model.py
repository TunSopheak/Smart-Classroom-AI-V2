"""Download helper for Phase 30C MediaPipe Pose Landmarker models.

This script downloads an official MediaPipe Pose Landmarker `.task` model into a
local `models/` folder. Model files are intentionally ignored by Git and should
not be committed.

Usage:
    python tools/download_pose_model.py --variant lite
    python tools/download_pose_model.py --variant full
    python tools/download_pose_model.py --variant heavy
"""

from __future__ import annotations

import argparse
import json
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

POSE_MODEL_URLS: dict[str, str] = {
    "lite": "https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_lite/float16/latest/pose_landmarker_lite.task",
    "full": "https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_full/float16/latest/pose_landmarker_full.task",
    "heavy": "https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_heavy/float16/latest/pose_landmarker_heavy.task",
}

POSE_MODEL_FILENAMES: dict[str, str] = {
    "lite": "pose_landmarker_lite.task",
    "full": "pose_landmarker_full.task",
    "heavy": "pose_landmarker_heavy.task",
}


def model_destination(variant: str, output_dir: str | Path = "models") -> Path:
    safe_variant = variant.lower().strip()
    if safe_variant not in POSE_MODEL_FILENAMES:
        raise ValueError(f"Unsupported pose model variant: {variant}")
    return Path(output_dir) / POSE_MODEL_FILENAMES[safe_variant]


def download_pose_model(
    variant: str = "lite",
    output_dir: str | Path = "models",
    overwrite: bool = False,
) -> dict[str, Any]:
    """Download a MediaPipe Pose Landmarker model and return JSON-safe status."""

    safe_variant = variant.lower().strip()
    if safe_variant not in POSE_MODEL_URLS:
        return {
            "ok": False,
            "status": "unsupported_variant",
            "variant": variant,
            "supported_variants": sorted(POSE_MODEL_URLS),
        }

    destination = model_destination(safe_variant, output_dir)
    destination.parent.mkdir(parents=True, exist_ok=True)

    if destination.exists() and not overwrite:
        return {
            "ok": True,
            "status": "already_exists",
            "variant": safe_variant,
            "path": str(destination),
            "size_bytes": destination.stat().st_size,
            "message": "Model already exists locally. Use --overwrite to download again.",
        }

    url = POSE_MODEL_URLS[safe_variant]
    try:
        with urllib.request.urlopen(url, timeout=60) as response:  # nosec B310 - official model URL list above
            data = response.read()
        destination.write_bytes(data)
    except urllib.error.URLError as exc:
        return {
            "ok": False,
            "status": "download_failed",
            "variant": safe_variant,
            "url": url,
            "path": str(destination),
            "message": "Failed to download the MediaPipe Pose Landmarker model.",
            "error": str(exc),
        }

    return {
        "ok": True,
        "status": "downloaded",
        "variant": safe_variant,
        "url": url,
        "path": str(destination),
        "size_bytes": destination.stat().st_size,
        "message": "Model downloaded locally. Do not commit .task model files.",
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Download a local MediaPipe Pose Landmarker model for sandbox testing."
    )
    parser.add_argument(
        "--variant",
        choices=sorted(POSE_MODEL_URLS),
        default="lite",
        help="Pose model variant to download. Start with lite for laptop testing.",
    )
    parser.add_argument(
        "--output-dir",
        default="models",
        help="Local output folder. The default `models/` folder is ignored by Git.",
    )
    parser.add_argument("--overwrite", action="store_true", help="Redownload even if the file exists.")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON output.")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    result = download_pose_model(
        variant=args.variant,
        output_dir=args.output_dir,
        overwrite=args.overwrite,
    )
    print(json.dumps(result, indent=2 if args.pretty else None, ensure_ascii=False))
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
