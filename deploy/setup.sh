#!/usr/bin/env bash
# One-time setup script for FamBank systemd service.
# Run as root on the target server.
set -euo pipefail

APP_DIR="/opt/fambank"
SERVICE_FILE="fambank.service"

echo "==> Copying service file to systemd..."
cp "$(dirname "$0")/${SERVICE_FILE}" /etc/systemd/system/${SERVICE_FILE}

echo "==> Creating fambank system user (if not exists)..."
id -u fambank &>/dev/null || useradd --system --home-dir ${APP_DIR} --shell /usr/sbin/nologin fambank

echo "==> Setting ownership..."
chown -R fambank:fambank ${APP_DIR}

echo "==> Reloading systemd daemon..."
systemctl daemon-reload

echo "==> Enabling fambank service (auto-start on boot)..."
systemctl enable fambank

echo "==> Starting fambank service..."
systemctl start fambank

echo "==> Done. Check status with: systemctl status fambank"
echo "==> View logs with: journalctl -u fambank -f"
