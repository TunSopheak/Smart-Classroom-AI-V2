"""Safe model-adapter interfaces for future behavior recognition layers."""

from app.services.model_adapters.face_emotion_adapter import FaceEmotionAdapter
from app.services.model_adapters.head_orientation_adapter import (
    HeadOrientationAdapter,
)
from app.services.model_adapters.pose_adapter import PoseAdapter


def default_model_adapters():
    """Return fresh placeholder adapters without loading optional models."""

    return [PoseAdapter(), HeadOrientationAdapter(), FaceEmotionAdapter()]


__all__ = [
    "FaceEmotionAdapter",
    "HeadOrientationAdapter",
    "PoseAdapter",
    "default_model_adapters",
]
