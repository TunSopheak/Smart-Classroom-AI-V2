"""Frame decoding helpers for backend AI analysis."""

from __future__ import annotations

import base64
import binascii


def decode_base64_image(frame_data: str | None) -> bytes | None:
    if not frame_data:
        return None

    _, _, payload = frame_data.partition(",")
    clean_payload = payload or frame_data
    try:
        return base64.b64decode(clean_payload, validate=True)
    except (binascii.Error, ValueError):
        return None
