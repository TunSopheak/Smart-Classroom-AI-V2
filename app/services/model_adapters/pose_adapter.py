"""Placeholder adapter for a future pose/head-landmark model."""

from app.services.model_adapters.base import BaseModelAdapter


class PoseAdapter(BaseModelAdapter):
    adapter_name = "pose_adapter"
    capability_key = "pose_model"
    display_name = "Pose / Head Landmark Model"
    required_dependency = (
        "Requires a validated pose or head-landmark model and classroom-specific "
        "confidence thresholds."
    )
    planned_outputs = (
        "possible_head_down",
        "sleepy_drowsy_candidate",
        "pose_landmarks",
    )
