"""Placeholder adapter for a future face/head-orientation model."""

from app.services.model_adapters.base import BaseModelAdapter


class HeadOrientationAdapter(BaseModelAdapter):
    adapter_name = "head_orientation_adapter"
    capability_key = "head_orientation_model"
    display_name = "Head Orientation Model"
    required_dependency = (
        "Requires validated face/head landmarks and yaw, pitch, and roll estimation "
        "with temporal confirmation."
    )
    planned_outputs = (
        "looking_around_candidate",
        "possible_inattentive_candidate",
        "head_orientation",
    )
