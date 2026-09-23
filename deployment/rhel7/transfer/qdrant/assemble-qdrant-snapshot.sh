#!/usr/bin/env bash
set -euo pipefail

parts_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
snapshot_name='jjm_rag_semantic_gemini_embedding_001_v2_header_repair-1184672206836481-2026-09-23-10-10-49.snapshot'
output_path=${1:-"$parts_dir/$snapshot_name"}

if [[ -e "$output_path" ]]; then
  echo "Refusing to overwrite existing output: $output_path" >&2
  exit 1
fi

cat "$parts_dir"/qdrant.snapshot.part.* > "$output_path"
(cd "$parts_dir" && sha256sum -c qdrant.snapshot.sha256)
echo "Reassembled Qdrant snapshot: $output_path"
