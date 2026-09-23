#!/usr/bin/env bash
set -euo pipefail

qdrant_url=${QDRANT_URL:-http://127.0.0.1:6333}
collection=jjm_rag_semantic_gemini_embedding_001_v2_header_repair
default_snapshot=/opt/installers/jjm-rag/deployment/rhel7/transfer/qdrant/jjm_rag_semantic_gemini_embedding_001_v2_header_repair-1184672206836481-2026-09-23-10-10-49.snapshot
snapshot_path=${1:-$default_snapshot}

[[ -f "$snapshot_path" ]] || { echo "Snapshot file not found: $snapshot_path" >&2; exit 1; }
curl --fail --silent --show-error "${qdrant_url%/}/" >/dev/null

if curl --fail --silent --output /dev/null "${qdrant_url%/}/collections/${collection}"; then
  echo "Refusing import: collection already exists: ${collection}" >&2
  exit 1
fi

curl --fail --show-error --max-time 900 \
  --request POST "${qdrant_url%/}/collections/${collection}/snapshots/upload" \
  --form "snapshot=@${snapshot_path}"
echo
echo 'Snapshot upload completed. Verify collection status with:'
echo "curl --fail --silent ${qdrant_url%/}/collections/${collection}"
