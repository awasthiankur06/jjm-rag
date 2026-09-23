#!/usr/bin/env bash
set -euo pipefail

[[ ${EUID} -eq 0 ]] || { echo 'Run with sudo.' >&2; exit 1; }
[[ -f /opt/jjm-rag/current/.venv/bin/python ]] || { echo 'Install the application first.' >&2; exit 1; }
[[ -f /etc/jjm-rag/jjm-rag.env ]] || { echo 'Create /etc/jjm-rag/jjm-rag.env from the template first.' >&2; exit 1; }
install -m 0644 /opt/jjm-rag/current/deployment/rhel7/templates/jjm-rag.service /etc/systemd/system/jjm-rag.service
chown root:jjmrag /etc/jjm-rag/jjm-rag.env
chmod 0640 /etc/jjm-rag/jjm-rag.env
systemctl daemon-reload
echo 'systemd unit installed. Start it only after PostgreSQL and Qdrant validation.'
