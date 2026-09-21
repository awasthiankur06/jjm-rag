# Gemini semantic full-index attempt

## Status

`COMPLETE`

The approved 635-candidate Gemini semantic index was started with the existing isolated Qdrant collection and resumable existing-point skipping.

Observed state:

- Initial points before this resume: 89
- Controlled probe: 1 candidate embedded and upserted successfully
- Resume additions across controlled attempts, excluding the probe: 176 candidates embedded and upserted successfully
- Current unique points: 635
- Remaining approved candidates: 0
- Duplicate logical content units: 0
- Excluded-source points: 0
- Successful resume batches across controlled attempts: 22
- Gemini requests across controlled attempts: 24
- Rate-limit retries across controlled attempts: 6
- Failed resume batch: none
- Failure: none

No unrelated Qdrant collection was modified. The checkpoint remains at [tmp/semantic_index_checkpoint.json](../tmp/semantic_index_checkpoint.json) so existing points can be skipped on a later controlled resume. The indexer uses sequential conservative batches, deliberate request delay, exponential backoff with jitter, Retry-After when available, and bounded retries.

No credentials were printed or stored, and no local model inference was used. Protected artifacts and corpus hashes remain unchanged.

The full 635-candidate Gemini semantic index completed using the existing checkpoint and quota-aware sequential indexer. Existing points were preserved and missing candidates were embedded/upserted without resetting the collection.

Final integrity: 635 unique Qdrant canonical IDs, 0 missing, 0 duplicates, 0 excluded-source points, 635 PostgreSQL resolutions, valid deterministic point IDs, 768-dimensional vectors, correct Gemini metadata, checkpoint `complete=true`, and full pytest `52 passed`.

## TPM quota gate

The confirmed provider dashboard state is RPM `88/100`, TPM `38.37K/30K`, and RPD `275/1K`; TPM is the active constraint. The indexer now uses a rolling one-minute accounting window, a 65% safety budget (`19,500` estimated tokens), sequential requests, deliberate delay, bounded backoff with jitter, and provider retry metadata when available. The SDK response does not expose embedding token usage, so the local conservative estimate is `ceil(character_count / 3)`. No provider call was made while the dashboard TPM was already over quota.
