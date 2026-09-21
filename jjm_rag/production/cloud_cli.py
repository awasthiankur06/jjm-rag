from __future__ import annotations

import argparse
import json
from jjm_rag.config import settings as _settings
from pathlib import Path

from .cloud_indexing import dry_run, index_candidates


def main() -> int:
    parser = argparse.ArgumentParser(description="JJM Gemini + Qdrant semantic index")
    parser.add_argument("--manifest", default=str(Path("artifacts/phase6b_semantic_candidate_manifest.json")))
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--checkpoint", default="tmp/semantic_index_checkpoint.json")
    parser.add_argument("--probe", action="store_true", help="embed and upsert at most one currently missing candidate")
    args = parser.parse_args()
    result = dry_run(args.manifest, args.limit) if args.dry_run else index_candidates(args.manifest, limit=args.limit, checkpoint_path=args.checkpoint, max_new=1 if args.probe else None)
    print(json.dumps(result.__dict__, indent=2, default=str))
    return 0 if result.status in {"DRY_RUN", "SUCCESS"} else 2


if __name__ == "__main__":
    raise SystemExit(main())
