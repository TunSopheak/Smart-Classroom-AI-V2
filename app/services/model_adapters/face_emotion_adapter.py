"""Placeholder adapter for a future validated face-emotion model."""

from app.services.model_adapters.base import BaseModelAdapter


class FaceEmotionAdapter(BaseModelAdapter):
    adapter_name = "face_emotion_adapter"
    capability_key = "face_emotion_model"
    display_name = "Face Emotion Model"
    required_dependency = (
        "Requires reliable face crops and a validated, bias-reviewed emotion model; "
        "small or occluded faces must be rejected."
    )
    planned_outputs = (
        "happy_smile_candidate",
        "laughing_candidate",
        "sad_tired_candidate",
    )
