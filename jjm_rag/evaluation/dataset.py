from __future__ import annotations

from dataclasses import dataclass


@dataclass
class EvaluationCase:
    id: str
    question: str
    expected_strategy: str
    expected_source_family: str | None = None


def load_eval_cases() -> list[EvaluationCase]:
    return [
        EvaluationCase("Q1", "What does the JJM guidance say about operational definitions?", "semantic", "policy"),
        EvaluationCase("Q2", "Which state has the highest FHTC coverage?", "structured", "coverage"),
        EvaluationCase("Q3", "What is the verified scheme count for Assam?", "structured", "progress"),
        EvaluationCase("Q6", "Which report contains the latest sanction order listing?", "exact", "sanction"),
        EvaluationCase("Q8", "Which files are version variants of the progress tracker?", "exact", "version"),
        EvaluationCase("Q23", "What is the current coverage status in Assam and which report provides it?", "hybrid", "coverage"),
    ]
