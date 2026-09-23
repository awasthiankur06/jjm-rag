#!/usr/bin/env bash
set -euo pipefail

: "${QDRANT_URL:?Set QDRANT_URL.}"
: "${QDRANT_COLLECTION:?Set QDRANT_COLLECTION.}"
header=()
if [[ -n ${QDRANT_API_KEY:-} ]]; then
  header=(-H "api-key: $QDRANT_API_KEY")
fi
curl --fail --silent --show-error "${QDRANT_URL%/}/collections/${QDRANT_COLLECTION}" "${header[@]}"
echo
echo 'Review status, vector dimension, distance, and points_count against the source deployment before enabling semantic retrieval.'
