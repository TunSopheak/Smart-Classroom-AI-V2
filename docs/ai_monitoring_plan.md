# AI Monitoring Plan

AI monitoring is planned for later phases and is not implemented in the initial foundation.

## Future Modules

- `camera.py`: camera stream setup and frame capture.
- `face_detection.py`: face detection and classroom presence signals.
- `attention_detection.py`: attention-related signals.
- `phone_detection.py`: phone usage detection.
- `event_logger.py`: conversion of detection output into session-linked AI events.

## Event Strategy

AI detections should create normalized `AIEvent` records linked to a `Session`.

Examples of future event types:

- `face_missing`
- `low_attention`
- `phone_detected`
- `camera_offline`

## Design Rule

AI code should stay isolated from FastAPI routers. Routers call services, services coordinate AI modules, and model files remain database-only.
