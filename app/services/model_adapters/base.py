"""Base contract for optional behavior-recognition model adapters."""

from __future__ import annotations


class BaseModelAdapter:
    adapter_name = "base_adapter"
    capability_key = "future_model"
    display_name = "Future Model Adapter"
    required_dependency = "A validated optional model implementation."
    planned_outputs: tuple[str, ...] = ()

    def is_available(self) -> bool:
        """Return whether a real validated model is loaded for this adapter."""

        return False

    def analyze(self, image_bytes: bytes, detections: list[dict]) -> dict:
        """Return a safe empty result when the optional model is unavailable."""

        safe_detections = detections if isinstance(detections, list) else []
        return {
            "adapter": self.adapter_name,
            "capability": self.capability_key,
            "available": False,
            "status": "model_required",
            "predictions": [],
            "generated_behavior_labels": [],
            "detections_evaluated": len(safe_detections),
            "image_input_available": bool(image_bytes),
            "message": self.required_dependency,
        }

    def capability_status(self) -> dict:
        """Describe current availability without importing optional dependencies."""

        available = self.is_available()
        return {
            "adapter": self.adapter_name,
            "capability": self.capability_key,
            "display_name": self.display_name,
            "available": available,
            "active": available,
            "status": "active" if available else "model_required",
            "planned_outputs": list(self.planned_outputs),
            "required_dependency": self.required_dependency,
            "safe_mode": not available,
        }
