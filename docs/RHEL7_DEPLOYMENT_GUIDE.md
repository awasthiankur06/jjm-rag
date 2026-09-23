# JJM RAG deployment on RHEL 7

This runbook transfers the validated application, canonical PostgreSQL corpus, and optional Qdrant semantic collection to a RHEL 7 host. It does not transfer source-control secrets, does not re-ingest the corpus, and does not use SQLite in production.

## Important platform decision

RHEL 7 is in its Extended Life Phase. Red Hat recommends moving to a supported RHEL release; if RHEL 7 must remain in use, use RHEL 7.9 with the appropriate Extended Life-cycle Support entitlement and keep the deployment on a private, patched, monitored network. See Red Hat's [RHEL 7 lifecycle FAQ](https://access.redhat.com/articles/7005471).

The preferred target is RHEL 8/9. The procedure below is suitable for an existing RHEL 7 deployment, but it is not a reason to expose an unpatched RHEL 7 host to the internet.

## Architecture and transfer rule

| Component | Role | Transfer method |
| --- | --- | --- |
| PostgreSQL | Authoritative source of truth: documents, raw values, structured records, observations, canonical content, provenance, audit records | Full custom-format `pg_dump` archive and `pg_restore` |
| Qdrant | Derived semantic index only; every accepted point must match PostgreSQL canonical text and content ID | Snapshot import only when it matches the transferred PostgreSQL corpus; otherwise rebuild from PostgreSQL |
| Application | FastAPI UI/API, deterministic PostgreSQL retrieval, optional Qdrant and provider clients | Deploy a pinned source revision and Python virtual environment |
| Original XLS/PDF corpus | Immutable evidence and future re-ingestion input | Transfer read-only, preserving filenames and hashes |

Never import a Qdrant collection into a database with different canonical content IDs/text. PostgreSQL is authoritative; Qdrant can always be rebuilt.

The excluded corrupted workbook, `Status of Pipe Water Supply in School (2).xls`, must remain absent from `documents`, `structured_records`, `observations`, `canonical_content`, and Qdrant.

## 1. Preflight and release bundle

Perform these commands from a controlled administrator workstation or the current validated host. Do not put passwords in shell history, command lines, Git, logs, or artifacts.

Record the deployed code revision and capture a clean release bundle:

```bash
git rev-parse HEAD
git status --short
python -m pytest -q
```

Copy the repository at that revision, the immutable `knowlade base files/` directory, `artifacts/`, `db/migrations/`, and this `docs/` directory to a protected staging location. Preserve the corpus filenames and hashes. Do not copy a local `.env` file containing credentials.

Use a current PostgreSQL client version that is compatible with the source server. PostgreSQL's custom dump format is designed for `pg_restore`; use the same or newer major-version client on the restore host where possible. See the official [pg_dump](https://www.postgresql.org/docs/current/app-pgdump.html) and [pg_restore](https://www.postgresql.org/docs/current/app-pgrestore.html) documentation.

## 2. Export the existing canonical PostgreSQL database

On the current database-side environment, set the database connection only in the session or a protected `PGPASSFILE`. The database archive contains corpus data and must be encrypted in transit and at rest.

```bash
install -d -m 0700 /secure-transfer/jjm-rag
export PGPASSFILE=/secure-transfer/.pgpass
chmod 0600 "$PGPASSFILE"

# PGP_DUMP_DSN is supplied by the operator; never echo it.
pg_dump --format=custom --verbose --file /secure-transfer/jjm-rag/jjm_rag_canonical.dump "$PG_DUMP_DSN"
sha256sum /secure-transfer/jjm-rag/jjm_rag_canonical.dump > /secure-transfer/jjm-rag/jjm_rag_canonical.dump.sha256
pg_restore --list /secure-transfer/jjm-rag/jjm_rag_canonical.dump > /secure-transfer/jjm-rag/jjm_rag_canonical.dump.toc
```

Transfer the dump, its checksum, and table-of-contents file with an approved encrypted transfer mechanism. Do not send the database URL, `.pgpass`, provider keys, or Qdrant API key with the archive.

### What not to do

- Do not export a SQLite file as the production database.
- Do not run a new ingestion merely to populate the RHEL host when a verified canonical PostgreSQL dump is being restored.
- Do not use `pg_restore --clean` against an existing production database.
- Do not run `001_initial_schema.sql` before restoring a full schema-and-data dump; the dump already contains the schema.

## 3. Export the existing Qdrant collection

First record the active collection name, Qdrant version, vector configuration, and point count. Do not include any API key in the saved report.

```bash
curl --fail --silent --show-error "$QDRANT_URL/collections/$QDRANT_COLLECTION" \
  -H "api-key: $QDRANT_API_KEY" > /secure-transfer/jjm-rag/qdrant_collection_before.json
```

Create a collection snapshot using the Qdrant instance's supported snapshot API, then download it to the protected transfer directory. The exact authentication/proxy arrangement is deployment-specific; use the Qdrant snapshot endpoint documented for the installed server version.

```bash
# Create a collection snapshot. Save the returned snapshot name.
curl --fail --silent --show-error --request POST \
  "$QDRANT_URL/collections/$QDRANT_COLLECTION/snapshots" \
  -H "api-key: $QDRANT_API_KEY" > /secure-transfer/jjm-rag/qdrant_snapshot_create.json

# Download the named snapshot returned above. Replace SNAPSHOT_NAME only in the shell session.
curl --fail --silent --show-error \
  "$QDRANT_URL/collections/$QDRANT_COLLECTION/snapshots/$SNAPSHOT_NAME" \
  -H "api-key: $QDRANT_API_KEY" \
  --output /secure-transfer/jjm-rag/qdrant_collection.snapshot
sha256sum /secure-transfer/jjm-rag/qdrant_collection.snapshot > /secure-transfer/jjm-rag/qdrant_collection.snapshot.sha256
```

Keep the old collection available until the RHEL deployment passes acceptance. If snapshot import is not supported by the installed Qdrant edition/version, or any canonical alignment check fails, do **not** force the import: rebuild a new, versioned collection from the restored PostgreSQL corpus.

## 4. Prepare the RHEL 7 host

Create a dedicated non-login service account and protected directories. Paths below are examples; use your organisation's standard locations.

```bash
sudo useradd --system --home-dir /opt/jjm-rag --shell /sbin/nologin jjmrag
sudo install -d -o jjmrag -g jjmrag -m 0750 /opt/jjm-rag /var/log/jjm-rag /var/lib/jjm-rag
sudo install -d -o root -g jjmrag -m 0750 /etc/jjm-rag
```

Install a supported Python runtime and PostgreSQL client packages through approved RHEL repositories or your organisation's package mirror. RHEL 7's system Python is too old for this project; do not replace the system Python. Use a separately installed supported Python runtime, for example Python 3.11, and create a virtual environment.

```bash
cd /opt/jjm-rag
/path/to/python3.11 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -r requirements.txt
```

Run the application as `jjmrag`, never as root. Keep source documents read-only for that account after initial transfer:

```bash
sudo chown -R jjmrag:jjmrag /opt/jjm-rag
sudo chmod -R go-w /opt/jjm-rag/knowlade\ base\ files
```

## 5. Restore PostgreSQL to the RHEL environment

Create a dedicated database and least-privilege application role through the database administration process. The role needs access to the JJM database only; it does not need PostgreSQL superuser privileges.

Restore first into a temporary validation database. A successful restore is not a release approval.

```bash
# The DBA creates jjm_rag_restore_check. Connection details are supplied through
# a protected environment/PGPASSFILE, never written into this document.
export PGPASSFILE=/etc/jjm-rag/.pgpass
chmod 0600 "$PGPASSFILE"

sha256sum -c /secure-transfer/jjm-rag/jjm_rag_canonical.dump.sha256
pg_restore --verbose --no-owner --no-privileges --dbname "$JJM_RESTORE_DSN" \
  /secure-transfer/jjm-rag/jjm_rag_canonical.dump
```

After validation, restore the same verified archive into the empty dedicated production database. Do not overwrite an active production database. Set the runtime's `JJM_DATABASE_URL` only after the production restore is accepted.

### PostgreSQL restore checks

Run these against the restored database:

```sql
SELECT COUNT(*) AS documents FROM documents;
SELECT COUNT(*) AS structured_records FROM structured_records;
SELECT COUNT(*) AS observations FROM observations;
SELECT COUNT(*) AS canonical_content FROM canonical_content;
SELECT COUNT(*) AS provenance_records FROM provenance_records;

SELECT filename, ingestion_status
FROM documents
WHERE filename = 'Status of Pipe Water Supply in School (2).xls';
```

The excluded-source query must return zero rows. Compare all five counts to the source environment's export-time counts. Also confirm the expected schema objects exist in `public`, foreign keys are present, and the application role can read/write only the intended database.

## 6. Restore or rebuild Qdrant

### Option A: import the snapshot

Use this only when the PostgreSQL canonical dump and Qdrant snapshot were captured from the same validated corpus revision. Upload/import the snapshot through the Qdrant snapshot API supported by the installed Qdrant server. Use a **new versioned collection name** for the RHEL deployment where the server supports restoring under a different name.

After import, inspect the collection:

```bash
curl --fail --silent --show-error "$QDRANT_URL/collections/$QDRANT_COLLECTION" \
  -H "api-key: $QDRANT_API_KEY"
```

Require the expected cosine distance, vector dimension, deterministic point IDs, and expected point count. The validated local reference collection used 768-dimensional cosine vectors; do not assume this is valid if you deploy a different embedding model.

### Option B: rebuild from PostgreSQL (preferred if there is any doubt)

Set a new collection name, run the dry run, then build from the restored canonical PostgreSQL data:

```bash
export QDRANT_COLLECTION=jjm_rag_semantic_rhel_<release_id>
.venv/bin/python -m jjm_rag.production.cloud_cli --dry-run
.venv/bin/python -m jjm_rag.production.cloud_cli --checkpoint /var/lib/jjm-rag/semantic_index_checkpoint.json
```

Do not change the live `QDRANT_COLLECTION` until validation passes. Retain the previous collection for rollback.

### Qdrant safety checks

1. Qdrant count equals the expected candidate count for the restored corpus.
2. Every point's `content_unit_id` resolves to `canonical_content` in PostgreSQL and the point payload text exactly equals canonical text.
3. No point payload has `filename` equal to `Status of Pipe Water Supply in School (2).xls`.
4. The collection's embedding provider/model/dimension metadata match the runtime configuration.

The application has `CanonicalValidatedQdrantRetriever`; it rejects stale/mismatched points at query time. This is a last safety barrier, not a substitute for deployment validation.

## 7. Runtime environment file

Create `/etc/jjm-rag/jjm-rag.env` with root ownership and mode `0640`. Populate values through the deployment secret manager or an approved protected process.

```ini
# Required: dedicated PostgreSQL production database. Do not put a real URL in Git.
JJM_DATABASE_URL=<secret-managed-postgresql-dsn>

# Qdrant is optional at startup but required for semantic retrieval.
QDRANT_URL=<private-qdrant-url>
QDRANT_COLLECTION=<validated-versioned-collection>
QDRANT_API_KEY=<secret-managed-value>
QDRANT_TIMEOUT=60
QDRANT_BATCH_SIZE=32

# Required only when semantic retrieval is enabled. This is an embedding key,
# not an answer-generation key.
GEMINI_API_KEY=<secret-managed-value>
GEMINI_EMBEDDING_MODEL=gemini-embedding-001
GEMINI_EMBEDDING_DIMENSION=768
GEMINI_TIMEOUT_SECONDS=60

# Configure only the providers you intend to use.
XAI_API_KEY=<secret-managed-value>
XAI_BASE_URL=https://api.x.ai/v1
XAI_MODEL=grok-4.6
XAI_TIMEOUT_SECONDS=20
XAI_MAX_RETRIES=2

RAG_MAX_EVIDENCE=10
RAG_MAX_OUTPUT_TOKENS=800
DEFAULT_CHUNK_SIZE=800
DEFAULT_CHUNK_OVERLAP=120
```

```bash
sudo chown root:jjmrag /etc/jjm-rag/jjm-rag.env
sudo chmod 0640 /etc/jjm-rag/jjm-rag.env
```

Provider keys and database credentials must never be placed in `/opt/jjm-rag/.env`, Git, systemd unit text, shell history, logs, screenshots, or support tickets.

## 8. Run the application with systemd

Create `/etc/systemd/system/jjm-rag.service`:

```ini
[Unit]
Description=JJM RAG API and browser console
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=jjmrag
Group=jjmrag
WorkingDirectory=/opt/jjm-rag
EnvironmentFile=/etc/jjm-rag/jjm-rag.env
Environment=PYTHONUNBUFFERED=1
ExecStart=/opt/jjm-rag/.venv/bin/python -m uvicorn jjm_rag.production.main:app --host 127.0.0.1 --port 8000
Restart=on-failure
RestartSec=5
TimeoutStartSec=90
NoNewPrivileges=true
PrivateTmp=true
ProtectHome=true
ReadWritePaths=/var/log/jjm-rag /var/lib/jjm-rag
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

Enable and inspect it:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now jjm-rag
sudo systemctl status jjm-rag --no-pager
sudo journalctl -u jjm-rag -n 100 --no-pager
curl --fail http://127.0.0.1:8000/health
curl --fail http://127.0.0.1:8000/ready
```

Bind Uvicorn to `127.0.0.1` only. Put the existing Apache HTTP Server (`httpd`) in front for TLS, authentication, request-size limits, and access logging. Do not expose port 8000 directly.

On SELinux-enforcing RHEL, use an approved policy configuration. For Apache HTTP Server to proxy to the local upstream, the common boolean is:

```bash
sudo setsebool -P httpd_can_network_connect 1
```

Confirm this change with the security team; do not disable SELinux globally.

## 9. Apache HTTP Server (`httpd`) reverse-proxy

Enable the Apache proxy, HTTP, headers, and SSL modules through the packages and configuration approved for your RHEL 7 installation. Verify them before enabling the site:

```bash
sudo httpd -M | grep -E 'proxy_module|proxy_http_module|headers_module|ssl_module'
```

Create `/etc/httpd/conf.d/jjm-rag.conf`. Use certificates supplied by your organisation. This example intentionally contains no hostname or certificate path.

```apache
<VirtualHost *:443>
    ServerName <approved-dns-name>

    SSLEngine on
    SSLCertificateFile <managed-certificate-path>
    SSLCertificateKeyFile <managed-private-key-path>

    LimitRequestBody 2097152
    ProxyRequests Off
    ProxyPreserveHost On
    ProxyAddHeaders On
    ProxyPass        / http://127.0.0.1:8000/ connectiontimeout=5 timeout=90
    ProxyPassReverse / http://127.0.0.1:8000/

    RequestHeader set X-Forwarded-Proto "https"
    ErrorLog  /var/log/httpd/jjm-rag-error.log
    CustomLog /var/log/httpd/jjm-rag-access.log combined
</VirtualHost>
```

Validate Apache configuration and reload it only after the local API passes its health check:

```bash
sudo httpd -t
sudo systemctl reload httpd
curl --fail --resolve <approved-dns-name>:443:127.0.0.1 https://<approved-dns-name>/health
```

Restrict inbound access at the firewall/load balancer to the intended users and Apache only. Configure authentication before allowing users outside the trusted network.

## 10. Production acceptance checklist

Before routing users to the RHEL deployment, require all of the following:

1. `GET /health` returns `healthy` and `GET /ready` reports the intended provider state.
2. PostgreSQL table counts match the validated source-side count report.
3. The excluded corrupted workbook count is zero in PostgreSQL and Qdrant.
4. Run canonical ingestion a second time only in a separate validation environment; verify `ALREADY_INGESTED` and unchanged counts. Do not use production truncation to test idempotency.
5. Direct numeric lookup returns raw value, numeric value, document, and provenance.
6. A compatible calculation returns validated operands and result provenance.
7. A missing entity or incompatible mixed-scope query abstains/clarifies rather than guessing.
8. Qdrant alignment checks pass, or semantic retrieval remains disabled until it is rebuilt.
9. Run `pytest -q` using the deployed revision and archive the result outside source control.
10. Keep the previous PostgreSQL backup and previous Qdrant collection until the release is accepted.

## 11. Rollback

### Application rollback

Deploy the prior approved code revision, retain the same validated PostgreSQL database and Qdrant collection, then restart only `jjm-rag.service`.

### Qdrant rollback

Set `QDRANT_COLLECTION` back to the previous validated collection in `/etc/jjm-rag/jjm-rag.env`, restart `jjm-rag.service`, and re-run readiness plus canonical-alignment checks. Do not modify PostgreSQL to address a Qdrant issue.

### PostgreSQL rollback

Do not restore over an active database as the first response. Restore the prior custom dump to a separate recovery database, validate counts/provenance/exclusion safety, then promote through the database change-control process.

## 12. Ongoing operations

- Back up PostgreSQL on a schedule and periodically test restore into a separate database.
- Snapshot Qdrant before index changes, but treat PostgreSQL backup/restore as the recovery authority.
- Rebuild Qdrant only from the current PostgreSQL `canonical_content` rows.
- Monitor systemd service restarts, API readiness, PostgreSQL connection failures, Qdrant failures, provider timeouts, disk capacity, backup completion, and excluded-source safety.
- Rotate credentials through the secret manager, then restart the service. Never log secret values.
- Plan a supported-OS migration from RHEL 7; do not defer it indefinitely.
