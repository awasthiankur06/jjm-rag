#!/usr/bin/env bash
set -euo pipefail

if [[ ${EUID} -ne 0 ]]; then
  echo 'Run this preflight with sudo.' >&2
  exit 1
fi
if [[ ! -f /etc/redhat-release ]]; then
  echo 'This bundle is intended for a RHEL-compatible host.' >&2
  exit 1
fi

echo 'Operating system:'
cat /etc/redhat-release
echo 'Required tools:'
missing=0
for tool in psql pg_restore curl httpd systemctl; do
  if command -v "$tool" >/dev/null 2>&1; then
    printf '  OK: %s (%s)\n' "$tool" "$(command -v "$tool")"
  else
    printf '  MISSING: %s\n' "$tool" >&2
    missing=1
  fi
done
python_cmd=${JJM_PYTHON:-python3}
if ! command -v "$python_cmd" >/dev/null 2>&1; then
  echo "  MISSING: Python command $python_cmd" >&2
  missing=1
else
  python_version=$($python_cmd -c 'import sys; print("%s.%s" % sys.version_info[:2])')
  printf '  OK: Python %s (%s)\n' "$python_version" "$(command -v "$python_cmd")"
  if ! "$python_cmd" -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 10) else 1)'; then
    echo '  UNSUPPORTED: JJM RAG needs Python 3.10 or newer; do not use RHEL 7 system Python.' >&2
    missing=1
  fi
fi
if (( missing )); then
  echo 'Install the missing tools from your approved RHEL repositories before continuing.' >&2
  exit 1
fi
echo 'Next: install the application release.'
