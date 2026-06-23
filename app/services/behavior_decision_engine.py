"""Combine active object results with safe optional-model adapter outputs."""

from __future__ import annotations

from copy import deepcopy

from app.services import multibehavior_model_service
from app.services.model_adapters import default_model_adapters


OBJECT_BASED_BEHAVIORS = {
    "normal_monitoring",
    "possible_phone_usage",
    "phone_object",
    "object_detected",
}


def analyze_with_model_adapters(
    image_bytes: bytes,
    object_analysis: dict | None,
    adapters=None,
) -> dict:
    """Attach adapter decisions without replacing active object-based results."""

    enriched = (
        deepcopy(object_analysis) if isinstance(object_analysis, dict) else {}
    )
    detections = enriched.get("detections")
    detections = detections if isinstance(detections, list) else []
    selected_adapters = (
        list(adapters) if adapters is not None else default_model_adapters()
    )

    adapter_results = [
        adapter.analyze(image_bytes, detections) for adapter in selected_adapters
    ]
    generated_labels = [
        label
        for result in adapter_results
        for label in result.get("generated_behavior_labels", [])
    ]
    object_behaviors = sorted(
        {
            str(detection.get("behavior"))
            for detection in detections
            if isinstance(detection, dict)
            and detection.get("behavior") in OBJECT_BASED_BEHAVIORS
        }
    )
    capabilities = multibehavior_model_service.model_capability_status()

    enriched["detections"] = detections
    enriched["model_capabilities"] = capabilities
    enriched["adapter_results"] = adapter_results
    enriched["behavior_decision"] = {
        "schema_version": "behavior-decision-v1",
        "status": "object_detector_active_optional_models_required",
        "safe_mode": True,
        "object_based_behaviors_preserved": object_behaviors,
        "adapter_generated_behavior_labels": generated_labels,
        "model_required": [
            status["capability"]
            for status in capabilities["adapter_status"]
            if not status["available"]
        ],
        "temporal_smoothing_active": capabilities[
            "temporal_smoothing_active"
        ],
        "message": (
            "Object-based person and phone behavior remains active. Optional pose, "
            "head-orientation, and emotion adapters did not generate behavior labels."
        ),
    }
    return enriched
