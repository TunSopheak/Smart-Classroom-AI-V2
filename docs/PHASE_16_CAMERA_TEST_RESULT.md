# Phase 16: Raspberry Pi Camera Test Result

Smart Classroom AI Monitoring - Production Roadmap Before Flutter

## Test Date

2026-06-19

## Goal

Confirm that the Raspberry Pi camera module can be detected and can capture a real image before continuing to backend snapshot upload and real AI detection.

## Camera Detection Test

Command used on Raspberry Pi:

```bash
rpicam-hello --list-cameras
```

Result:

```text
Available cameras
-----------------
0 : ov5647 [2592x1944 10-bit GBRG] (/base/axi/pcie@1000120000/rp1/i2c@88000/ov5647@36)
```

Detected camera sensor:

```text
ov5647
```

Supported modes shown during test:

```text
640x480
1296x972
1920x1080
2592x1944
```

## Image Capture Test

Command used on Raspberry Pi:

```bash
rpicam-still --output test.jpg --timeout 2000 --nopreview
```

Reason for `--nopreview`:

The Raspberry Pi was accessed through SSH/headless mode without a monitor, so preview window was disabled.

## Image File Check

Command used:

```bash
ls -lh test.jpg
```

Result:

```text
-rw-rw-r-- 1 sopheak sopheak 582K Jun 19 16:17 test.jpg
```

## Test Result

```text
Camera detected: PASSED
Image capture: PASSED
Image file saved: PASSED
Phase 16 status: COMPLETED
```

## Important Notes

- Camera cable and camera module are working.
- Raspberry Pi OS camera stack detected the camera successfully.
- The captured test image was saved as `/home/sopheak/test.jpg`.
- The image should be copied to the laptop for visual confirmation and backup.

## Copy Image to Laptop

From Windows PowerShell on the laptop, use:

```powershell
scp sopheak@10.86.94.200:/home/sopheak/test.jpg "$env:USERPROFILE\Desktop\Smart_Classroom_Demo_Backup\phase16_camera_test.jpg"
```

If the backup folder does not exist yet, create it first:

```powershell
mkdir "$env:USERPROFILE\Desktop\Smart_Classroom_Demo_Backup"
```

## Next Phase

Next production step:

```text
Phase 17: Camera Snapshot Upload to Backend
```

Goal:

```text
Raspberry Pi captures a real camera image and uploads it to the FastAPI backend so the dashboard can display the latest classroom snapshot.
```
