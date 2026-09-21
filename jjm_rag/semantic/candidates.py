from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import re
from typing import Any, Iterable


_NUMERIC_ONLY = re.compile(r"^[\s\d,.;:%+\-()/]+$")
_CODE_ONLY = re.compile(r"^(?:format\s*)?[A-Z0-9_./()-]{1,24}$", re.I)
_NUMERIC_TOKEN = re.compile(r"^[\d,.;:%+\-()/]+$")


@dataclass(frozen=True)
class CandidateDecision:
    content_id: str
    eligible: bool
    reason: str
    candidate_id: str


def deterministic_candidate_id(content_id: str, text: str) -> str:
    return "sem-" + sha256(f"{content_id}|{text}".encode("utf-8")).hexdigest()[:32]


def _source_is_excluded(row: dict[str, Any]) -> bool:
    return row.get("filename") == "Status of Pipe Water Supply in School (2).xls" or row.get("production_included") is False


def select_semantic_candidates(rows: Iterable[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[CandidateDecision]]:
    """Select meaningful narrative units without embedding structured cell observations."""
    candidates: list[dict[str, Any]] = []
    decisions: list[CandidateDecision] = []
    for row in rows:
        content_id = str(row.get("content_id", ""))
        text = str(row.get("canonical_text") or "").replace("\x00", "").strip()
        content_type = str(row.get("content_type") or "").lower()
        if _source_is_excluded(row):
            reason = "excluded_source"
        elif not text:
            reason = "empty_text"
        elif content_type in {"cell", "observation", "structured_record"}:
            reason = "structured_unit"
        elif _NUMERIC_ONLY.fullmatch(text):
            reason = "numeric_only"
        elif content_type == "row":
            tokens = text.split()
            numeric_tokens = sum(bool(_NUMERIC_TOKEN.fullmatch(token)) for token in tokens)
            alpha_tokens = sum(any(character.isalpha() for character in token) for token in tokens)
            if numeric_tokens >= 3 and numeric_tokens >= alpha_tokens:
                reason = "numeric_dominant_row"
            else:
                reason = "eligible"
        elif _CODE_ONLY.fullmatch(text) and len(text.split()) <= 2:
            reason = "identifier_only"
        elif len(text) < 24:
            reason = "low_information_fragment"
        else:
            reason = "eligible"
        eligible = reason == "eligible"
        decision = CandidateDecision(content_id, eligible, reason, deterministic_candidate_id(content_id, text))
        decisions.append(decision)
        if eligible:
            candidates.append({**row, "candidate_id": decision.candidate_id, "content_hash": sha256(text.encode("utf-8")).hexdigest()})
    return candidates, decisions
