# Smart Classroom Mobile MVP

Phase 31A creates a Flutter Android MVP that connects to the same FastAPI backend as the web dashboard.

## Important

This folder contains the MVP Dart code and pubspec. To create the Android native scaffold on Windows, run:

```powershell
flutter create --platforms=android --project-name smart_classroom_mobile mobile_app
```

If Flutter creates a default `lib/main.dart`, replace it with the version from this repository.

## Backend API

Start FastAPI on your laptop:

```powershell
python -m uvicorn main:app --host 0.0.0.0 --port 8000
```

Default mobile API URL:

```text
http://10.86.94.199:8000
```

Android devices cannot use `127.0.0.1` to reach your laptop backend. Use the laptop WiFi IP or an HTTPS tunnel URL.

## Mobile API endpoints

```text
GET /api/mobile/health
GET /api/mobile/summary
GET /api/mobile/students
GET /api/mobile/sessions/today
GET /api/mobile/iot/status
```

## Run on Android

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

APK output folder:

```text
mobile_app/build/app/outputs/flutter-apk/
```

## MVP screens

- Dashboard summary
- Students
- Today's sessions
- IoT / AI status
- Settings for backend API URL

## Not included yet

- Login/authentication
- Offline sync
- Push notification
- Full chart report system
- Live pose alerts
- Play Store release signing
