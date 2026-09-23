#!/usr/bin/env bash
set -euo pipefail

[[ ${EUID} -eq 0 ]] || { echo 'Run this installer with sudo.' >&2; exit 1; }
source_dir=${1:?Usage: 10-install-app.sh <transferred-release-directory> <release-id>}
release_id=${2:?Usage: 10-install-app.sh <transferred-release-directory> <release-id>}
python_cmd=${JJM_PYTHON:-python3}
[[ -d "$source_dir/jjm_rag" && -f "$source_dir/requirements.txt" ]] || { echo 'The supplied directory is not a JJM RAG release.' >&2; exit 1; }
[[ "$release_id" =~ ^[A-Za-z0-9._-]+$ ]] || { echo 'Release ID contains unsupported characters.' >&2; exit 1; }
command -v "$python_cmd" >/dev/null 2>&1 || { echo "Python command not found: $python_cmd" >&2; exit 1; }
"$python_cmd" -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 10) else 1)' || { echo 'JJM RAG requires Python 3.10 or newer.' >&2; exit 1; }

id jjmrag >/dev/null 2>&1 || useradd --system --home-dir /opt/jjm-rag --shell /sbin/nologin jjmrag
install -d -o jjmrag -g jjmrag -m 0750 /opt/jjm-rag/releases /var/log/jjm-rag /var/lib/jjm-rag
install -d -o root -g jjmrag -m 0750 /etc/jjm-rag
target=/opt/jjm-rag/releases/$release_id
[[ ! -e "$target" ]] || { echo "Release target already exists: $target" >&2; exit 1; }

install -d -o jjmrag -g jjmrag -m 0750 "$target"
(cd "$source_dir" && tar --exclude=.git --exclude=.env --exclude=.venv --exclude=artifacts/v2 -cf - .) | (cd "$target" && tar xf -)
chown -R jjmrag:jjmrag "$target"
chmod -R go-w "$target"
runuser -u jjmrag -- /usr/bin/env bash -c "cd '$target' && '$python_cmd' -m venv --system-site-packages .venv && .venv/bin/python -m pip install --upgrade pip && .venv/bin/python -m pip install --only-binary=:all: -r requirements.txt"
ln -sfn "$target" /opt/jjm-rag/current
echo "Installed release $release_id at $target"
