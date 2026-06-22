import os
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATABASE_URL = f"sqlite:///{BASE_DIR / 'smart_classroom_v2.db'}"
PROJECT_NAME = "Smart Classroom AI Monitoring V2"
PI_LIVE_STREAM_URL = os.getenv(
    "SMART_CLASSROOM_PI_STREAM_URL",
    "http://10.86.94.200:8081/stream.mjpg",
).strip() or "http://10.86.94.200:8081/stream.mjpg"

AI_FRAME_SAMPLING_MIN_INTERVAL_SECONDS = 5
AI_FRAME_SAMPLING_ENABLED = os.getenv(
    "SMART_CLASSROOM_AI_SAMPLING_ENABLED",
    "0",
).strip().lower() in {"1", "true", "yes", "on"}

try:
    _ai_sampling_interval = int(
        os.getenv("SMART_CLASSROOM_AI_SAMPLE_INTERVAL", "10")
    )
except ValueError:
    _ai_sampling_interval = 10

AI_FRAME_SAMPLING_INTERVAL_SECONDS = max(
    AI_FRAME_SAMPLING_MIN_INTERVAL_SECONDS,
    _ai_sampling_interval,
)
