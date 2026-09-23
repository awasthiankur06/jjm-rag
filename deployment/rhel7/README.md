# JJM RAG RHEL 7 deployment bundle

This folder is the operator bundle for JJM RAG behind Apache HTTP Server (`httpd`). It contains no credentials, database dump, Qdrant snapshot, or source corpus.

## Transfer to RHEL

Transfer the whole repository/release directory without `.env` files, plus a verified PostgreSQL custom archive and checksum. Transfer a Qdrant snapshot only if it was captured from exactly the same canonical PostgreSQL corpus.

PostgreSQL is authoritative. Qdrant is derived and can be rebuilt from PostgreSQL.

## Command order on RHEL

Run every command only after the previous command succeeds:

```bash
cd /path/to/transferred/jjm-rag
sudo bash deployment/rhel7/scripts/00-preflight.sh
sudo bash deployment/rhel7/scripts/10-install-app.sh "$(pwd)" v1-20260923
sudo install -m 0640 -o root -g jjmrag deployment/rhel7/templates/jjm-rag.env.example /etc/jjm-rag/jjm-rag.env
sudo vi /etc/jjm-rag/jjm-rag.env
sudo bash deployment/rhel7/scripts/30-install-service.sh
sudo bash deployment/rhel7/scripts/40-install-httpd.sh
```

Use a release ID containing only letters, digits, `.`, `_`, or `-`. Configure real credentials only in `/etc/jjm-rag/jjm-rag.env`; never put them in this repository or command arguments.

To populate the known local PostgreSQL/Qdrant values and enter provider keys without echoing them, run:

```bash
sudo bash deployment/rhel7/scripts/70-configure-runtime.sh
```

The script writes keys only to `/etc/jjm-rag/jjm-rag.env`, which is root-owned and readable by the `jjmrag` service group. It never prints keys or writes them into Git.

### RHEL 7 Python package note

When using the documented micromamba runtime, install compiled `numpy` and `pandas` in that runtime before application installation. The release installer creates a virtual environment with access to those packages and refuses to compile source distributions on RHEL 7's legacy compiler.

```bash
sudo /root/jjm-micromamba-download/bin/micromamba install -y \
  --prefix /opt/jjm-runtime --channel conda-forge --strict-channel-priority \
  numpy pandas
```

## Restore PostgreSQL

The DBA must make an empty dedicated database and a least-privilege role. Store its password in a protected `PGPASSFILE`.

```bash
export PGPASSFILE=/etc/jjm-rag/.pgpass
chmod 0600 "$PGPASSFILE"
export JJM_RESTORE_DSN='<operator-supplied-dsn>'
export JJM_RESTORE_CONFIRM='RESTORE_APPROVED_EMPTY_DATABASE'
sudo -E bash deployment/rhel7/scripts/20-restore-postgres.sh \
  /secure-transfer/jjm-rag/jjm_rag_canonical.dump \
  /secure-transfer/jjm-rag/jjm_rag_canonical.dump.sha256
export JJM_DATABASE_URL="$JJM_RESTORE_DSN"
bash deployment/rhel7/scripts/21-validate-postgres.sh
unset JJM_RESTORE_DSN JJM_DATABASE_URL
```

The restore does not use `--clean`, does not drop databases, and requires explicit confirmation.

## Qdrant

Load Qdrant variables without displaying them, then inspect its collection:

```bash
set -a
source /etc/jjm-rag/jjm-rag.env
set +a
bash deployment/rhel7/scripts/22-qdrant-status.sh
```

If snapshot alignment cannot be proven, rebuild a new versioned collection from restored PostgreSQL:

```bash
sudo -u jjmrag -H /opt/jjm-rag/current/.venv/bin/python -m jjm_rag.production.cloud_cli --dry-run
sudo -u jjmrag -H /opt/jjm-rag/current/.venv/bin/python -m jjm_rag.production.cloud_cli --checkpoint /var/lib/jjm-rag/semantic_index_checkpoint.json
```

To import the bundled, split Qdrant snapshot after reassembly, run:

```bash
bash deployment/rhel7/scripts/60-import-qdrant-snapshot.sh
```

The import script refuses to overwrite the JJM collection and never modifies unrelated Qdrant collections.

## Start and verify

```bash
sudo systemctl enable --now jjm-rag httpd
bash deployment/rhel7/scripts/50-healthcheck.sh
sudo systemctl status jjm-rag httpd --no-pager
```

Do not expose port `8000`; Apache is the only public endpoint. Read `docs/RHEL7_DEPLOYMENT_GUIDE.md` for backup, rollback, and security details.
