#!/usr/bin/env bash
# ==============================================================================
# FEMS Backup & Disaster Recovery Manager - Linux Systemd Service Installer
# ==============================================================================

set -e

APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SERVICE_NAME="fems-backup-manager"
SERVICE_FILE="/etc/systemd/system/${SERVICE_NAME}.service"
BACKUP_DIR="/var/backups/FEMS_Backup"

echo "==========================================================="
echo " Installing FEMS Database Backup & DR Subsystem"
echo " Directory:   ${APP_DIR}"
echo " Service:     ${SERVICE_NAME}"
echo " Storage Root: ${BACKUP_DIR}"
echo "==========================================================="

# Check root privileges
if [ "$EUID" -ne 0 ]; then
  echo "[ERROR] Please run this script with sudo or as root."
  exit 1
fi

# Ensure backup destination exists with correct permissions
mkdir -p "${BACKUP_DIR}"
chmod 755 "${BACKUP_DIR}"

# Check Python 3
if ! command -v python3 &> /dev/null; then
    echo "[ERROR] python3 could not be found. Please install python3 first."
    exit 1
fi

# Create Systemd Service
echo "Creating systemd unit file at ${SERVICE_FILE}..."
cat <<EOF > "${SERVICE_FILE}"
[Unit]
Description=FEMS Database Backup and Disaster Recovery Manager
After=network.target docker.service
Wants=docker.service

[Service]
Type=simple
User=root
WorkingDirectory=${APP_DIR}
ExecStart=/usr/bin/python3 ${APP_DIR}/app.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
EOF

# Reload daemon and start service
echo "Reloading systemd daemon..."
systemctl daemon-reload

echo "Enabling ${SERVICE_NAME} on system startup..."
systemctl enable "${SERVICE_NAME}"

echo "Starting ${SERVICE_NAME}..."
systemctl restart "${SERVICE_NAME}"

echo "Checking service status..."
systemctl is-active --quiet "${SERVICE_NAME}" && echo "✅ FEMS Backup Manager is ACTIVE and RUNNING!" || echo "⚠️ Service failed to start. Check: journalctl -u ${SERVICE_NAME} -f"

echo ""
echo "==========================================================="
echo " Installation Complete!"
echo " Web Dashboard:   http://$(hostname -I | awk '{print $1}'):5051"
echo " Service Logs:    sudo journalctl -u ${SERVICE_NAME} -f"
echo " Backup Folder:   ${BACKUP_DIR}"
echo "==========================================================="
