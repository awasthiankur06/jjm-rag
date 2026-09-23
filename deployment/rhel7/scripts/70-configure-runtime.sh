#!/usr/bin/env bash
set -euo pipefail

config_file=/etc/jjm-rag/jjm-rag.env
[[ ${EUID} -eq 0 ]] || { echo 'Run with sudo.' >&2; exit 1; }
[[ -f "$config_file" ]] || { echo "Configuration file not found: $config_file" >&2; exit 1; }

read -r -s -p 'Gemini API key: ' gemini_key
echo
read -r -s -p 'xAI API key: ' xai_key
echo
read -r -s -p 'Qdrant API key (press Enter for local unauthenticated Qdrant): ' qdrant_key
echo

[[ -n "$gemini_key" ]] || { echo 'Gemini API key is required.' >&2; exit 1; }
[[ -n "$xai_key" ]] || { echo 'xAI API key is required.' >&2; exit 1; }

escape_sed() {
  printf '%s' "$1" | sed -e 's/[\\&|]/\\&/g'
}

set_value() {
  local key=$1
  local value=$2
  local escaped
  escaped=$(escape_sed "$value")
  if grep -q "^${key}=" "$config_file"; then
    sed -i "s|^${key}=.*|${key}=${escaped}|" "$config_file"
  else
    printf '%s=%s\n' "$key" "$value" >> "$config_file"
  fi
}

set_value JJM_DATABASE_URL 'postgresql://jjmrag@127.0.0.1:5432/jjm_rag'
set_value PGPASSFILE '/etc/jjm-rag/.pgpass'
set_value QDRANT_URL 'http://127.0.0.1:6333'
set_value QDRANT_COLLECTION 'jjm_rag_semantic_gemini_embedding_001_v2_header_repair'
set_value QDRANT_API_KEY "$qdrant_key"
set_value GEMINI_API_KEY "$gemini_key"
set_value GEMINI_EMBEDDING_MODEL 'gemini-embedding-001'
set_value GEMINI_EMBEDDING_DIMENSION '768'
set_value XAI_API_KEY "$xai_key"
set_value XAI_BASE_URL 'https://api.x.ai/v1'
set_value XAI_MODEL 'grok-4.6'

chown root:jjmrag "$config_file"
chmod 0640 "$config_file"
echo "Configured $config_file. API key values were not displayed."
