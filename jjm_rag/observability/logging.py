from __future__ import annotations

import logging
from pathlib import Path


def configure_logging(log_dir: str | Path | None = None) -> logging.Logger:
    logger = logging.getLogger("jjm_rag")
    logger.setLevel(logging.INFO)
    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s")
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    return logger
