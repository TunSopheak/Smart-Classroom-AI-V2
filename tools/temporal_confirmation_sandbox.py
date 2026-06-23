"""Phase 30F temporal confirmation sandbox.

Use this CLI to test repeated posture candidates without connecting to live
alerts, reports, the database, or Raspberry Pi services.

Examples:
    python tools/temporal_confirmation_sandbox.py --demo --pretty
    python tools/temporal_confirmation_sandbox.py --label possible_head_low_candidate --label possible_head_low_candidate --label possible_head_low_candidate --pretty
"""

from __future__ import annotations

import argparse
import json
from typing import Any

from app.services.temporal_confirmation_service import evaluate_temporal_confirmation


def build_frame(label: str, confidence: float) -> dict[str, Any]:
    return {
        "candidate_result": {
            "posture_candidates": [
                {
                    "label": label,
                    "confidence": confidence,
                    "safe_mode": True,
                    "generated_behavior_labels": [],
                }
            ]
        }
    }


def demo_frames() -> list[dict[str, Any]]:
    return [
        build_frame("possible_head_low_candidate", 0.55),
        build_frame("possible_head_low_candidate", 0.58),
        build_frame("normal_upright_candidate", 0.60),
        build_frame("possible_head_low_candidate", 0.57),
        build_frame("possible_head_low_candidate", 0.56),
    ]


def frames_from_labels(labels: list[str], confidence: float) -> list[dict[str, Any]]:
    return [build_frame(label, confidence) for label in labels]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run Phase 30F temporal confirmation on sandbox candidate labels."
    )
    parser.add_argument("--demo", action="store_true", help="Run a built-in demo sequence.")
    parser.add_argument("--label", action="append", dest="labels", help="Candidate label for one frame. Can be repeated.")
    parser.add_argument("--target", default="possible_head_low_candidate", help="Target candidate label to confirm.")
    parser.add_argument("--window-size", type=int, default=5, help="Recent frame window size.")
    parser.add_argument("--min-matches", type=int, default=3, help="Minimum target matches required.")
    parser.add_argument("--confidence", type=float, default=0.55, help="Confidence applied to --label frames.")
    parser.add_argument("--min-confidence", type=float, default=0.50, help="Minimum confidence for a match.")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON output.")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    if args.demo:
        frames = demo_frames()
    else:
        frames = frames_from_labels(args.labels or [], args.confidence)

    result = evaluate_temporal_confirmation(
        frames,
        target_label=args.target,
        window_size=args.window_size,
        min_matches=args.min_matches,
        min_confidence=args.min_confidence,
    )
    print(json.dumps(result, indent=2 if args.pretty else None, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
