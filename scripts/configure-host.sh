#!/usr/bin/env bash
# Run explicitly as root on Ubuntu; never transports credentials or changes SSH/UFW.
set -euo pipefail
[[ "$EUID" == 0 ]] || { echo 'Run as root on the target VM' >&2; exit 1; }
project_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
install -m 0750 "$project_root/scripts/infra/host-health.sh" /usr/local/sbin/clinic-host-health.sh
cat > /etc/systemd/system/clinic-host-health.service <<'UNIT'
[Unit]
Description=Clinic host RAM, disk and load health check
[Service]
Type=oneshot
ExecStart=/usr/local/sbin/clinic-host-health.sh
User=root
NoNewPrivileges=true
ProtectSystem=strict
ProtectHome=true
PrivateTmp=true
StandardOutput=journal
StandardError=journal
UNIT
cat > /etc/systemd/system/clinic-host-health.timer <<'UNIT'
[Unit]
Description=Check clinic host health every five minutes
[Timer]
OnBootSec=2min
OnUnitActiveSec=5min
[Install]
WantedBy=timers.target
UNIT
systemctl daemon-reload
systemctl enable --now clinic-host-health.timer
systemctl start clinic-host-health.service
systemctl show clinic-host-health.service -p Result -p ExecMainStatus