#!/usr/bin/env bash
set -euo pipefail

SERVICE_NAME="smart-classroom-pi-client.service"
PROJECT_DIR="/home/sopheak/Smart-Classroom-AI-V2"
SERVICE_SOURCE="$PROJECT_DIR/raspberry_pi/smart-classroom-pi-client.service.example"
SERVICE_TARGET="/etc/systemd/system/$SERVICE_NAME"

echo "Smart Classroom Pi Client Service Installer"
echo "Project directory: $PROJECT_DIR"
echo "Service source: $SERVICE_SOURCE"
echo "Service target: $SERVICE_TARGET"
echo

if [ ! -f "$SERVICE_SOURCE" ]; then
  echo "ERROR: Service example file not found: $SERVICE_SOURCE"
  exit 1
fi

if [ ! -f "$PROJECT_DIR/raspberry_pi/pi_client.py" ]; then
  echo "ERROR: pi_client.py not found in project directory."
  exit 1
fi

echo "Installing service file..."
sudo cp "$SERVICE_SOURCE" "$SERVICE_TARGET"

echo "Reloading systemd..."
sudo systemctl daemon-reload

echo "Enabling service to start on boot..."
sudo systemctl enable "$SERVICE_NAME"

echo
echo "Installation completed."
echo

echo "To start now:"
echo "  sudo systemctl start $SERVICE_NAME"
echo

echo "To check status:"
echo "  sudo systemctl status $SERVICE_NAME"
echo

echo "To view live logs:"
echo "  journalctl -u $SERVICE_NAME -f"
echo

echo "To stop service:"
echo "  sudo systemctl stop $SERVICE_NAME"
