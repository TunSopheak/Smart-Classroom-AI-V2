# Final Presentation Script

Smart Classroom AI Monitoring - Demo Presentation Script

## Presentation Style

Use simple English. Speak slowly and clearly. Show the system while explaining each part.

Recommended speaking time: 5-8 minutes.

## 1. Greeting and Introduction

```text
Good morning/afternoon teacher and everyone.

Today, our team would like to present our project called Smart Classroom AI Monitoring.

This project is designed to help teachers monitor classroom activity, check device status, and support smart light control using a web dashboard, backend API, AI monitoring logic, and Raspberry Pi IoT device connection.
```

Khmer note:

```text
ចាប់ផ្តើមដោយសុភាព។ និយាយឱ្យច្បាស់ថា project យើងមាន Web Dashboard + AI Monitoring + Raspberry Pi IoT។
```

## 2. Problem Statement

```text
In a normal classroom, teachers may find it difficult to monitor everything at the same time, such as student attention, classroom activity, device status, and light usage.

Sometimes lights may stay on even when there are no students in the room. Also, it is difficult to review classroom events later without a monitoring record.

Because of these problems, we created this Smart Classroom system to make classroom monitoring more reliable and more sustainable.
```

## 3. Project Objectives

```text
The main objectives of our project are:

First, to create a web dashboard for classroom monitoring.
Second, to integrate AI monitoring features for classroom events.
Third, to connect a real Raspberry Pi device to the backend.
Fourth, to control classroom light status from the dashboard.
Fifth, to prepare the system for future real hardware integration, such as relay modules and Raspberry Pi camera detection.
```

## 4. System Architecture Overview

```text
Our system has three main parts.

The first part is the laptop, which runs the FastAPI backend server and web dashboard.

The second part is the Raspberry Pi, which works as an IoT client device. It sends heartbeat data to the backend and reads light control commands from the backend.

The third part is the network. In our demo, the laptop and Raspberry Pi are connected through the same Wi-Fi or phone hotspot.
```

Show this while speaking:

```text
Laptop Backend + Web Dashboard
        |
        | Same Wi-Fi / Hotspot
        |
Raspberry Pi IoT Client
```

## 5. Technology Used

```text
For the backend, we use FastAPI with Python.

For the database, we use SQLite.

For the web dashboard, we use HTML, CSS, JavaScript, and Jinja2 templates.

For AI monitoring, we use Python and OpenCV-related processing.

For the IoT device, we use Raspberry Pi 5 running a Python client script.
```

## 6. Live Demo Part 1 - Start Dashboard

Action:

Open the dashboard in browser.

```text
http://127.0.0.1:8000/dashboard
```

Say:

```text
Now, this is our web dashboard. It is the main interface for the teacher or admin.

From here, the user can access classroom monitoring, AI monitoring, sessions, reports, and IoT device status.
```

## 7. Live Demo Part 2 - AI Monitoring Page

Action:

Open:

```text
http://127.0.0.1:8000/ai-monitoring
```

Say:

```text
This is the AI Monitoring page.

On this page, we can see classroom monitoring information, Raspberry Pi device status, and smart light control.

The purpose of this page is to help the teacher understand the current classroom condition from one place.
```

## 8. Live Demo Part 3 - Raspberry Pi Online Status

Action:

Show the Raspberry Pi Device Status card.

Say:

```text
Here, we can see the Raspberry Pi device status.

The Raspberry Pi sends a heartbeat to the backend every few seconds.

When the backend receives the heartbeat, the dashboard shows the device as Online.

We can also see the device name, IP address, last seen time, and how many seconds ago the Raspberry Pi connected.
```

Then show Raspberry Pi terminal.

```text
This terminal is running the Raspberry Pi client script. It sends heartbeat data and reads light state from the backend.
```

## 9. Live Demo Part 4 - Light Control

Action:

Click buttons:

```text
Light 1 ON
Light 1 OFF
Light 2 ON
Light 2 OFF
```

Say:

```text
Now I will test the light control feature.

When I click Light 1 ON, the dashboard sends the command to the backend.

The Raspberry Pi client reads the latest light state from the backend and prints the updated status in the terminal.

This is currently a safe software-only demo. In the future, we can connect this logic to a relay module to control real classroom lights.
```

## 10. Live Demo Part 5 - Auto Light Logic

Say:

```text
Our system also supports automatic light control logic.

For example, if no students are detected in the classroom for a period of time, the system can automatically turn off the lights to save energy.

This supports the idea of a sustainable smart classroom.
```

## 11. Live Demo Part 6 - AI Events and Reports

Action:

Open AI Events or Reports page if available.

Say:

```text
The system can also keep AI monitoring events and report information.

This allows the teacher to review classroom activity later, instead of only watching in real time.

This feature is useful for tracking attention events, classroom activity, and monitoring history.
```

## 12. Current Completed Features

```text
So far, our project has completed these main features:

Web Dashboard
AI Monitoring page
AI Events and Reports
Raspberry Pi device status integration
Real Raspberry Pi client connection
Heartbeat system
Raspberry Pi IP address display
Software light control demo
Occupancy auto light sync
Raspberry Pi demo guide
Final demo checklist
```

## 13. Limitations

```text
At the current stage, the light control is still a software demo.

We have not connected the system to real classroom electrical lights yet because real electrical wiring needs safety preparation and proper relay hardware.

Also, Raspberry Pi camera-based AI detection can be improved further in the next version.
```

## 14. Future Improvements

```text
For future improvements, we plan to add real relay module control for physical lights.

We also plan to improve Raspberry Pi camera integration, improve AI attention detection, add more classroom test data, and connect the Flutter mobile application.

These improvements will make the system more complete and closer to real classroom deployment.
```

## 15. Closing

```text
In conclusion, our Smart Classroom system already supports web-based monitoring, Raspberry Pi IoT connection, device online status, software light control, and AI event/report features.

This project shows how AI and IoT can work together to make classroom management more reliable and sustainable.

Thank you teacher and everyone for listening. We are ready for questions.
```

## Very Short Version

Use this if the teacher gives only a short time.

```text
Good morning/afternoon teacher and everyone.

Our project is Smart Classroom AI Monitoring. It combines a web dashboard, FastAPI backend, AI monitoring features, and Raspberry Pi IoT connection.

The goal is to help teachers monitor classroom activity, device status, and light control from one dashboard.

In the demo, the laptop runs the backend and dashboard. The Raspberry Pi works as an IoT client. It sends heartbeat data to the backend, so the dashboard can show the Raspberry Pi as Online.

We can also control Light 1 and Light 2 from the dashboard. The Raspberry Pi reads the latest light state and prints the result in the terminal. This is currently a safe software demo, and later it can be connected to a real relay module.

Our system also supports AI events, reports, and automatic light logic when no students are detected.

In conclusion, this project shows how AI and IoT can support a more reliable and sustainable smart classroom.

Thank you.
```

## Backup Explanation if Raspberry Pi Has Network Problem

```text
If the Raspberry Pi network connection has a problem during the live demo, we still have prepared screenshots and the dashboard features.

Previously, we successfully tested the Raspberry Pi connection. The dashboard showed the Raspberry Pi Online with its real IP address, and the Raspberry Pi terminal received light state updates from the backend.

So the feature is implemented, and the issue is only network setup, not the project logic.
```

## Q&A Preparation

### Question: Why use Raspberry Pi?

```text
We use Raspberry Pi because it can work as a small IoT edge device. It can connect to sensors, camera modules, and relay modules, and it can communicate with the backend over the network.
```

### Question: Is the light control real?

```text
At this stage, it is a safe software demo. The dashboard and backend logic are ready. For real electrical lights, we need a relay module and proper safety wiring.
```

### Question: What is heartbeat?

```text
Heartbeat means the Raspberry Pi sends a small status message to the backend regularly. If the backend receives it, the device is Online. If the backend does not receive it for a while, the device can be considered Offline.
```

### Question: What is the next step?

```text
The next step is to connect real hardware relay control, improve Raspberry Pi camera AI detection, and integrate the Flutter mobile app.
```

### Question: What makes this project useful?

```text
It helps teachers monitor classroom activity, review AI events, check IoT device status, and save energy through smart light control.
```
