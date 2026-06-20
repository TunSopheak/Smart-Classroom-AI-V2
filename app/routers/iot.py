import asyncio
from contextlib import suppress
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, Request, UploadFile
from fastapi.responses import JSONResponse, StreamingResponse
from sqlalchemy.orm import Session as DatabaseSession

from app.ai.yolo_detector import get_yolo_detector
from app.core.config import (
    AI_FRAME_SAMPLING_ENABLED,
    AI_FRAME_SAMPLING_INTERVAL_SECONDS,
    AI_FRAME_SAMPLING_MIN_INTERVAL_SECONDS,
)
from app.core.database import SessionLocal, get_db
from app.services import ai_service, iot_service


router = APIRouter(prefix="/iot", tags=["iot"])
LIVE_STREAM_FRAME_DELAY_SECONDS = 0.75
_camera_analysis_lock = asyncio.Lock()
_sampler_task: asyncio.Task | None = None
_sampler_state: dict = {
    "running": False,
    "last_sampled_file": None,
    "last_sampled_at": None,
    "last_error": None,
    "skipped_reason": "AI frame sampling is disabled.",
}


def sampler_time_label(value: datetime | None) -> str | None:
    if value is None:
        return None
    return value.strftime("%Y-%m-%d %H:%M:%S")


def ai_frame_sampler_status() -> dict:
    return {
        "enabled": AI_FRAME_SAMPLING_ENABLED,
        "running": bool(_sampler_state.get("running")),
        "interval_seconds": AI_FRAME_SAMPLING_INTERVAL_SECONDS,
        "min_interval_seconds": AI_FRAME_SAMPLING_MIN_INTERVAL_SECONDS,
        "last_sampled_file": _sampler_state.get("last_sampled_file"),
        "last_sampled_at": sampler_time_label(
            _sampler_state.get("last_sampled_at")
        ),
        "last_error": _sampler_state.get("last_error"),
        "skipped_reason": _sampler_state.get("skipped_reason"),
    }


def mark_sampler_file_processed(filename: str | None, reason: str) -> None:
    if not AI_FRAME_SAMPLING_ENABLED or not filename:
        return
    _sampler_state.update(
        {
            "last_sampled_file": filename,
            "last_sampled_at": datetime.utcnow(),
            "last_error": None,
            "skipped_reason": reason,
        }
    )


async def camera_live_stream():
    while True:
        snapshot = iot_service.snapshot_status()
        snapshot_url = snapshot.get("url")

        if snapshot.get("available") and snapshot_url:
            snapshot_path = Path("app") / str(snapshot_url).lstrip("/")
            try:
                image_bytes = snapshot_path.read_bytes()
            except OSError:
                image_bytes = b""

            if image_bytes:
                content_type = (
                    "image/png"
                    if snapshot_path.suffix.lower() == ".png"
                    else "image/jpeg"
                )
                yield (
                    b"--frame\r\n"
                    + f"Content-Type: {content_type}\r\n".encode("ascii")
                    + f"Content-Length: {len(image_bytes)}\r\n\r\n".encode("ascii")
                    + image_bytes
                    + b"\r\n"
                )

        await asyncio.sleep(LIVE_STREAM_FRAME_DELAY_SECONDS)


async def read_request_data(request: Request) -> dict:
    content_type = request.headers.get("content-type", "").lower()

    if "application/json" in content_type:
        try:
            data = await request.json()
            return data if isinstance(data, dict) else {}
        except Exception:
            return {}

    if (
        "application/x-www-form-urlencoded" in content_type
        or "multipart/form-data" in content_type
    ):
        try:
            form = await request.form()
            return dict(form)
        except Exception:
            return {}

    return {}


def is_truthy(value) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes", "on"}


def run_camera_analysis(
    image_bytes: bytes,
    db: DatabaseSession,
    session_id: str | int | None = None,
) -> tuple[dict, dict | None, bool, str | None, dict]:
    analysis = get_yolo_detector().analyze(image_bytes)

    occupancy = None
    occupancy_error = None
    occupancy_synced = False

    if analysis.get("available") and session_id:
        occupancy, occupancy_error = ai_service.update_detected_count(
            db,
            session_id,
            int(analysis.get("person_count") or 0),
        )
        occupancy_synced = occupancy is not None and occupancy_error is None
    elif analysis.get("available"):
        occupancy_error = "No active session selected, so occupancy was not updated."

    light = iot_service.light_status()
    iot_service.save_camera_analysis(
        analysis=analysis,
        occupancy=occupancy,
        occupancy_synced=occupancy_synced,
        occupancy_error=occupancy_error,
        light=light,
    )

    return analysis, occupancy, occupancy_synced, occupancy_error, light


async def run_camera_analysis_guarded(
    image_bytes: bytes,
    db: DatabaseSession,
    session_id: str | int | None = None,
) -> tuple[dict, dict | None, bool, str | None, dict]:
    async with _camera_analysis_lock:
        return run_camera_analysis(image_bytes, db, session_id)


def run_sampled_camera_analysis(
    image_bytes: bytes,
    session_id: str | int | None,
) -> tuple[dict, dict | None, bool, str | None, dict]:
    db = SessionLocal()
    try:
        return run_camera_analysis(image_bytes, db, session_id)
    finally:
        db.close()


async def sample_latest_camera_snapshot() -> None:
    snapshot = iot_service.snapshot_status()
    filename = snapshot.get("filename")
    snapshot_url = snapshot.get("url")

    if not snapshot.get("available") or not filename or not snapshot_url:
        _sampler_state["skipped_reason"] = "No camera snapshot is available."
        return

    if filename == _sampler_state.get("last_sampled_file"):
        _sampler_state["skipped_reason"] = "Latest snapshot was already analyzed."
        return

    if _camera_analysis_lock.locked():
        _sampler_state["skipped_reason"] = "AI analysis is already running."
        return

    snapshot_path = Path("app") / str(snapshot_url).lstrip("/")
    try:
        image_bytes = snapshot_path.read_bytes()
    except OSError as error:
        _sampler_state.update(
            {
                "last_error": str(error),
                "skipped_reason": "Latest snapshot file could not be read.",
            }
        )
        return

    async with _camera_analysis_lock:
        if filename == _sampler_state.get("last_sampled_file"):
            _sampler_state["skipped_reason"] = (
                "Latest snapshot was already analyzed."
            )
            return

        _sampler_state.update(
            {
                "last_sampled_file": filename,
                "last_sampled_at": datetime.utcnow(),
                "last_error": None,
                "skipped_reason": None,
            }
        )
        try:
            await asyncio.to_thread(
                run_sampled_camera_analysis,
                image_bytes,
                snapshot.get("session_id"),
            )
        except Exception as error:
            _sampler_state.update(
                {
                    "last_error": str(error),
                    "skipped_reason": "AI analysis failed for the sampled snapshot.",
                }
            )


async def ai_frame_sampling_loop() -> None:
    _sampler_state.update(
        {
            "running": True,
            "last_error": None,
            "skipped_reason": "Waiting for the next sampling interval.",
        }
    )
    try:
        while True:
            await asyncio.sleep(AI_FRAME_SAMPLING_INTERVAL_SECONDS)
            await sample_latest_camera_snapshot()
    finally:
        _sampler_state["running"] = False


def start_ai_frame_sampler() -> None:
    global _sampler_task

    if not AI_FRAME_SAMPLING_ENABLED:
        _sampler_state.update(
            {
                "running": False,
                "skipped_reason": "AI frame sampling is disabled.",
            }
        )
        return

    if _sampler_task and not _sampler_task.done():
        return

    _sampler_task = asyncio.create_task(ai_frame_sampling_loop())


async def stop_ai_frame_sampler() -> None:
    global _sampler_task

    if not _sampler_task:
        return

    _sampler_task.cancel()
    with suppress(asyncio.CancelledError):
        await _sampler_task
    _sampler_task = None


@router.post("/device/heartbeat")
async def device_heartbeat(request: Request):
    data = await read_request_data(request)

    device_name = data.get("device_name") or data.get("name")
    ip_address = request.client.host if request.client else None

    status = iot_service.record_heartbeat(
        device_name=device_name,
        ip_address=ip_address,
    )

    return {
        "ok": True,
        "message": "Device heartbeat received.",
        "device": status,
    }


@router.get("/device/status")
async def device_status():
    return {
        "ok": True,
        "device": iot_service.device_status(),
    }


@router.post("/device/reset")
async def reset_device_status():
    return {
        "ok": True,
        "message": "Device status reset.",
        "device": iot_service.reset_device_state(),
    }


@router.get("/light/status")
async def light_status():
    return {
        "ok": True,
        "light": iot_service.light_status(),
    }


@router.post("/light/control")
async def light_control(request: Request):
    data = await read_request_data(request)

    light_1 = data.get("light_1")
    light_2 = data.get("light_2")

    # Optional simple format:
    # {"light": "light_1", "state": "on"}
    selected_light = (data.get("light") or "").strip()
    selected_state = data.get("state")

    if selected_light == "light_1":
        light_1 = selected_state
    elif selected_light == "light_2":
        light_2 = selected_state

    updated_light = iot_service.update_light_state(
        light_1=light_1,
        light_2=light_2,
    )

    return {
        "ok": True,
        "message": "Light state updated.",
        "light": updated_light,
    }


@router.post("/light/reset")
async def reset_light_status():
    return {
        "ok": True,
        "message": "Light state reset.",
        "light": iot_service.reset_light_state(),
    }


@router.post("/camera/snapshot")
async def upload_camera_snapshot(
    request: Request,
    snapshot: UploadFile = File(...),
    device_name: str = Form("Raspberry Pi 5"),
    auto_analyze: str = Form("false"),
    session_id: str = Form(""),
    db: DatabaseSession = Depends(get_db),
):
    if not snapshot.content_type or not snapshot.content_type.startswith("image/"):
        return JSONResponse(
            {"ok": False, "message": "Snapshot must be an image file."},
            status_code=400,
        )

    image_bytes = await snapshot.read()
    if not image_bytes:
        return JSONResponse(
            {"ok": False, "message": "Snapshot image is empty."},
            status_code=400,
        )

    ip_address = request.client.host if request.client else None
    latest_snapshot = iot_service.save_camera_snapshot(
        image_bytes=image_bytes,
        original_filename=snapshot.filename,
        device_name=device_name,
        ip_address=ip_address,
        session_id=session_id,
    )

    response_payload = {
        "ok": True,
        "message": "Camera snapshot uploaded.",
        "snapshot": latest_snapshot,
        "analysis_state": iot_service.analysis_status(),
    }

    if is_truthy(auto_analyze):
        (
            analysis,
            occupancy,
            occupancy_synced,
            occupancy_error,
            light,
        ) = await run_camera_analysis_guarded(
            image_bytes=image_bytes, db=db, session_id=session_id
        )
        mark_sampler_file_processed(
            latest_snapshot.get("filename"),
            "Latest snapshot was analyzed by upload auto_analyze.",
        )
        response_payload.update(
            {
                "message": "Camera snapshot uploaded and analyzed.",
                "analysis": analysis,
                "occupancy": occupancy,
                "occupancy_synced": occupancy_synced,
                "occupancy_error": occupancy_error,
                "light": light,
                "analysis_state": iot_service.analysis_status(),
            }
        )

    return response_payload


@router.get("/camera/latest")
async def latest_camera_snapshot():
    return {
        "ok": True,
        "snapshot": iot_service.snapshot_status(),
        "analysis_state": iot_service.analysis_status(),
    }


@router.get("/camera/live.mjpg")
async def live_camera_preview():
    return StreamingResponse(
        camera_live_stream(),
        media_type="multipart/x-mixed-replace; boundary=frame",
        headers={
            "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
            "Pragma": "no-cache",
        },
    )


@router.get("/camera/sampler/status")
async def camera_sampler_status():
    return {
        "ok": True,
        "sampler": ai_frame_sampler_status(),
    }


@router.post("/camera/analyze-latest")
async def analyze_latest_camera_snapshot(
    request: Request,
    db: DatabaseSession = Depends(get_db),
):
    snapshot = iot_service.snapshot_status()
    snapshot_url = snapshot.get("url")

    if not snapshot.get("available") or not snapshot_url:
        return JSONResponse(
            {"ok": False, "message": "No Raspberry Pi camera snapshot is available yet."},
            status_code=404,
        )

    snapshot_path = Path("app") / str(snapshot_url).lstrip("/")
    if not snapshot_path.exists():
        return JSONResponse(
            {"ok": False, "message": "Latest snapshot file was not found on the backend."},
            status_code=404,
        )

    request_data = await read_request_data(request)
    session_id = request_data.get("session_id")
    (
        analysis,
        occupancy,
        occupancy_synced,
        occupancy_error,
        light,
    ) = await run_camera_analysis_guarded(
        image_bytes=snapshot_path.read_bytes(), db=db, session_id=session_id
    )
    mark_sampler_file_processed(
        snapshot.get("filename"),
        "Latest snapshot was analyzed manually.",
    )

    return {
        "ok": True,
        "message": "Latest camera snapshot analyzed.",
        "snapshot": snapshot,
        "analysis": analysis,
        "occupancy": occupancy,
        "occupancy_synced": occupancy_synced,
        "occupancy_error": occupancy_error,
        "light": light,
        "analysis_state": iot_service.analysis_status(),
    }


@router.post("/camera/reset")
async def reset_camera_snapshot():
    return {
        "ok": True,
        "message": "Camera snapshot state reset.",
        "snapshot": iot_service.reset_camera_snapshot(),
        "analysis_state": iot_service.analysis_status(),
    }


@router.get("/health")
async def iot_health():
    return {
        "ok": True,
        "message": "IoT API is running.",
    }
