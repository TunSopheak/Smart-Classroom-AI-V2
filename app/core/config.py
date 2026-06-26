import os
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATABASE_URL = f"sqlite:///{BASE_DIR / 'smart_classroom_v2.db'}"
PROJECT_NAME = "Smart Classroom AI Monitoring V2"
FACE_DATASET_DIR = Path(
    os.getenv("SMART_CLASSROOM_FACE_DATASET_DIR", str(BASE_DIR / "models" / "face_dataset"))
)
FACE_MODEL_PATH = Path(
    os.getenv("SMART_CLASSROOM_FACE_MODEL_PATH", str(BASE_DIR / "models" / "face_lbph_model.yml"))
)
try:
    _face_confidence_threshold = float(
        os.getenv("SMART_CLASSROOM_FACE_CONFIDENCE_THRESHOLD", "70")
    )
except ValueError:
    _face_confidence_threshold = 70.0

FACE_CONFIDENCE_THRESHOLD = max(0.0, _face_confidence_threshold)
CAMERA_BACKEND = os.getenv("CAMERA_BACKEND", "opencv").strip().lower() or "opencv"
CAMERA_SOURCE = os.getenv("CAMERA_SOURCE", "0").strip() or "0"
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

EVENT_SNAPSHOTS_ENABLED = os.getenv(
    "SMART_CLASSROOM_EVENT_SNAPSHOTS_ENABLED",
    "0",
).strip().lower() in {"1", "true", "yes", "on"}


def env_int(name: str, default: int, minimum: int) -> int:
    try:
        value = int(os.getenv(name, str(default)))
    except ValueError:
        value = default
    return max(minimum, value)


EVENT_SNAPSHOT_RETENTION_DAYS = env_int(
    "SMART_CLASSROOM_EVENT_SNAPSHOT_RETENTION_DAYS",
    7,
    1,
)
EVENT_SNAPSHOT_MAX_FILES = env_int(
    "SMART_CLASSROOM_EVENT_SNAPSHOT_MAX_FILES",
    100,
    1,
)
EVENT_COOLDOWN_SECONDS = env_int(
    "SMART_CLASSROOM_EVENT_COOLDOWN_SECONDS",
    60,
    1,
)

try:
    _phone_event_confidence = float(
        os.getenv("SMART_CLASSROOM_PHONE_EVENT_CONFIDENCE", "0.60")
    )
except ValueError:
    _phone_event_confidence = 0.60

PHONE_EVENT_CONFIDENCE = min(1.0, max(0.0, _phone_event_confidence))

BEHAVIOR_ALERTS_ENABLED = os.getenv(
    "SMART_CLASSROOM_BEHAVIOR_ALERTS_ENABLED",
    "0",
).strip().lower() in {"1", "true", "yes", "on"}
BEHAVIOR_REQUIRED_SAMPLES = env_int(
    "SMART_CLASSROOM_BEHAVIOR_REQUIRED_SAMPLES",
    3,
    3,
)
HEAD_DOWN_EVENT_COOLDOWN_SECONDS = env_int(
    "SMART_CLASSROOM_HEAD_DOWN_EVENT_COOLDOWN_SECONDS",
    120,
    30,
)
