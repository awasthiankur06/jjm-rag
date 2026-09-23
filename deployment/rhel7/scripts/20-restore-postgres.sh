#!/usr/bin/env bash
set -euo pipefail

dump_file=${1:?Usage: 20-restore-postgres.sh <dump-file> <sha256-file>}
checksum_file=${2:?Usage: 20-restore-postgres.sh <dump-file> <sha256-file>}
: "${JJM_RESTORE_DSN:?Set JJM_RESTORE_DSN in the protected operator environment.}"
[[ ${JJM_RESTORE_CONFIRM:-} == 'RESTORE_APPROVED_EMPTY_DATABASE' ]] || { echo 'Refusing restore: set JJM_RESTORE_CONFIRM=RESTORE_APPROVED_EMPTY_DATABASE only after confirming the target is empty and approved.' >&2; exit 1; }
[[ -f "$dump_file" && -f "$checksum_file" ]] || { echo 'Dump or checksum file is missing.' >&2; exit 1; }

sha256sum -c "$checksum_file"
echo 'Restoring archive without --clean, --create, ownership, or privileges changes.'
pg_restore --verbose --no-owner --no-privileges --dbname "$JJM_RESTORE_DSN" "$dump_file"
echo 'Restore finished. Run 21-validate-postgres.sh before using this database.'
