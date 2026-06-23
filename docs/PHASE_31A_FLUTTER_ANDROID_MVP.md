# Phase 31A: Flutter Android MVP Connected to FastAPI

## Purpose

Phase 31A adds a minimal Android mobile app that reads data from the same FastAPI backend used by the web dashboard.

Architecture:

```text
Web Dashboard      -> FastAPI Backend + SQLite DB
Flutter Android    -> FastAPI Backend + SQLite DB
Raspberry Pi       -> FastAPI Backend + Snapshot/IoT APIs
```

## What was added

```text
app/routers/mobile_api.py
mobile_app/pubspec.yaml
mobile_app/lib/main.dart
mobile_app/README.md
tests/test_mobile_api_router.py
```

`main.py` now includes the mobile API router.

## Mobile API endpoints

```text
GET /api/mobile/health
GET /api/mobile/summary
GET /api/mobile/students
GET /api/mobile/sessions/today
GET /api/mobile/iot/status
```

## Web/backend setup for phone access

Run backend on all network interfaces:

```powershell
python -m uvicorn main:app --host 0.0.0.0 --port 8000
```

Phone browser or Flutter app should use the laptop WiFi IP:

```text
http://10.86.94.199:8000
```

Do not use `127.0.0.1` from Android phone, because that points to the phone itself, not the laptop.

## Android scaffold setup

If `mobile_app/android` does not exist locally, generate it with Flutter:

```powershell
flutter create --platforms=android --project-name smart_classroom_mobile mobile_app
```

Then keep/restore the repository versions of:

```text
mobile_app/pubspec.yaml
mobile_app/lib/main.dart
```

## Cleartext HTTP note

For local WiFi demo with `http://10.86.94.199:8000`, Android may need cleartext HTTP allowed in the debug/demo Android manifest.

If the app cannot connect but browser can, add this to the `<application>` tag in:

```text
mobile_app/android/app/src/main/AndroidManifest.xml
```

```xml
android:usesCleartextTraffic="true"
```

Production should use HTTPS.

## Run app

```powershell
cd mobile_app
flutter pub get
flutter run
```

## Build APK

```powershell
cd mobile_app
flutter build apk --split-per-abi
```

APK output:

```text
mobile_app/build/app/outputs/flutter-apk/
```

## MVP screens

- Dashboard summary
- Student list
- Today's sessions
- IoT status
- API URL settings

## Safety limitation

This MVP is for demo. It has no login/authentication yet. Do not expose private data publicly without security hardening.

## Recommended next phase

```text
Phase 31B: Flutter APK Build + Android Device Test
```
