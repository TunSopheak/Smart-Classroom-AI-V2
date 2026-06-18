from fastapi import APIRouter, Request

from app.services import iot_service


router = APIRouter(prefix="/iot", tags=["iot"])


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


@router.get("/health")
async def iot_health():
    return {
        "ok": True,
        "message": "IoT API is running.",
    }