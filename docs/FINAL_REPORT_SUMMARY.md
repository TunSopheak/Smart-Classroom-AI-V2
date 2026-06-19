# Final Report Summary for Teacher

Project: Smart Classroom AI Monitoring  
Course: IoT / Computer Network Project  
Team: Smart Classroom Project Team  

## 1. Project Overview

Smart Classroom AI Monitoring is a classroom monitoring system that combines web technology, backend API, AI monitoring features, and Raspberry Pi IoT device connection.

The purpose of this project is to help teachers monitor classroom activity, check device status, review AI monitoring events, and support smart light control from one dashboard.

The system focuses on two important ideas:

- Reliable: the system should show useful classroom and device information clearly.
- Sustainable: the system should support energy saving through smart light control logic.

## 2. Problem Statement

In a normal classroom, teachers may find it difficult to monitor everything at the same time. For example, teachers may need to check student attention, classroom activity, device status, and light usage.

Sometimes classroom lights may stay on even when there are no students in the room. Also, classroom events are difficult to review later if there is no monitoring record.

Because of these problems, our team developed this Smart Classroom AI Monitoring system to support better classroom management.

## 3. Project Objectives

The main objectives of this project are:

1. To build a web dashboard for smart classroom monitoring.
2. To develop backend APIs for AI monitoring, IoT device status, and light control.
3. To integrate Raspberry Pi as a real IoT client device.
4. To display Raspberry Pi Online/Offline status on the dashboard.
5. To support software light control from the web dashboard.
6. To prepare the system for future real hardware integration such as relay modules and Raspberry Pi camera detection.
7. To support AI event records and reporting for teacher review.

## 4. System Architecture

The system has three main parts:

```text
Laptop Backend + Web Dashboard
        |
        | Same Wi-Fi / Hotspot Network
        |
Raspberry Pi IoT Client
```

### Laptop / Backend

The laptop runs the FastAPI backend server, web dashboard, AI monitoring pages, and SQLite database.

### Raspberry Pi

The Raspberry Pi works as an IoT client device. It sends heartbeat data to the backend and reads light control state from the backend.

### Network

The laptop and Raspberry Pi must be connected to the same Wi-Fi or phone hotspot so they can communicate with each other.

## 5. Technology Used

- Python
- FastAPI
- SQLite
- SQLAlchemy
- Jinja2 Templates
- HTML, CSS, JavaScript
- OpenCV-related AI monitoring logic
- Raspberry Pi 5
- Raspberry Pi OS Lite
- Git and GitHub

## 6. Completed Features

### Web Dashboard

The project includes a web dashboard for monitoring the classroom system.

Completed items:

- Dashboard page
- AI Monitoring page
- AI Events / Reports page
- Navigation links for monitoring features
- Modern UI layout for demo

### AI Monitoring Features

The AI monitoring module supports classroom monitoring events and report preparation.

Completed items:

- AI event structure
- AI event snapshots
- Report links
- AI reports list page
- Monitoring UI preparation

### Raspberry Pi Device Status Integration

The system can show the Raspberry Pi device status on the dashboard.

Completed items:

- Raspberry Pi heartbeat API
- Raspberry Pi Online/Offline display
- Device name display
- Last seen time display
- Seconds since last seen display
- Raspberry Pi IP address display

### Software Light Control Demo

The system includes a safe software-based light control demo.

Completed items:

- Light 1 ON/OFF control
- Light 2 ON/OFF control
- Backend light state API
- Dashboard light control buttons
- Raspberry Pi client reads light state from backend
- Raspberry Pi terminal prints updated light state

### Occupancy Auto Light Sync

The project supports automatic light state synchronization based on occupancy logic.

Completed items:

- Auto light logic preparation
- Sync between occupancy state and IoT light state
- Energy-saving concept demonstration

### Raspberry Pi Real Device Connection

The team successfully connected a real Raspberry Pi device to the backend system.

Completed items:

- Raspberry Pi OS setup
- SSH access
- Internet access on Raspberry Pi
- Git clone on Raspberry Pi
- Python requests installation
- Raspberry Pi client run successfully
- Dashboard showed Raspberry Pi Online
- Dashboard showed real Raspberry Pi IP address
- Safe shutdown tested

### Documentation and Demo Preparation

The project includes documentation files for final demo preparation.

Completed items:

- Raspberry Pi Demo Guide
- Auto-start service example
- Final Demo Checklist
- Final Presentation Script
- Final Report Summary

## 7. Important API Endpoints

The backend includes IoT-related endpoints:

```text
POST /iot/device/heartbeat
GET  /iot/device/status
POST /iot/device/reset
GET  /iot/light/status
POST /iot/light/control
POST /iot/light/reset
GET  /iot/health
```

These endpoints support Raspberry Pi heartbeat, device status checking, and light control.

## 8. Raspberry Pi Client Summary

The Raspberry Pi client script is located at:

```text
raspberry_pi/pi_client.py
```

The client performs these tasks:

- Reads backend URL from `SMART_CLASSROOM_BACKEND_URL` environment variable.
- Sends heartbeat to backend every 5 seconds.
- Fetches Light 1 and Light 2 status from backend.
- Prints updated light state when the value changes.
- Works as a safe software-only IoT demo.

Example command:

```bash
export SMART_CLASSROOM_BACKEND_URL="http://<LAPTOP_IP>:8000"
python3 raspberry_pi/pi_client.py
```

## 9. Final Demo Flow

During the final demo, the team can show this flow:

1. Start FastAPI backend server on laptop.
2. Open the web dashboard.
3. Open AI Monitoring page.
4. Power on Raspberry Pi.
5. SSH into Raspberry Pi.
6. Run Raspberry Pi client.
7. Show Raspberry Pi Online on dashboard.
8. Click Light 1 and Light 2 buttons.
9. Show Raspberry Pi terminal receiving light state updates.
10. Explain AI events, reports, and future improvements.

## 10. Current Limitations

At the current stage, the project still has some limitations:

- The light control is still a software demo, not connected to real electrical lights.
- Real relay module integration is not yet implemented.
- Raspberry Pi camera-based AI detection is not fully integrated yet.
- The Flutter mobile app is planned but not fully integrated into the final demo.
- More real classroom testing data is needed.

## 11. Future Improvements

Future improvements include:

1. Connect a relay module for real physical light control.
2. Improve Raspberry Pi camera integration.
3. Improve AI attention detection accuracy.
4. Add more classroom test data.
5. Integrate Flutter mobile application.
6. Add user authentication for teacher/admin access.
7. Improve report export features.
8. Deploy backend to a more stable server environment.

## 12. Conclusion

In conclusion, the Smart Classroom AI Monitoring project has successfully implemented the main demo features, including web-based monitoring, AI event/report preparation, Raspberry Pi IoT device connection, device online status, software light control, and occupancy auto light sync.

This project demonstrates how AI and IoT can work together to support a more reliable and sustainable classroom environment.

Although some hardware integrations are still planned for the future, the current system already shows the core concept and working communication between the web dashboard, backend API, and Raspberry Pi device.

## 13. Short Summary for Teacher

```text
Our Smart Classroom AI Monitoring project is designed to help teachers monitor classroom activity, device status, and smart light control through a web dashboard.

We completed the web dashboard, AI monitoring page, AI events/reports, Raspberry Pi device status integration, real Raspberry Pi connection, heartbeat system, software light control demo, and occupancy auto light sync.

The Raspberry Pi successfully connected to the backend and appeared Online on the dashboard with its real IP address. The dashboard can control Light 1 and Light 2 status, and the Raspberry Pi client can read and display the updated light state.

The current limitation is that the light control is still a software demo. In the future, we plan to connect real relay hardware, improve Raspberry Pi camera AI detection, and integrate the Flutter mobile app.

Overall, this project shows how AI and IoT can support a more reliable and sustainable smart classroom system.
```
