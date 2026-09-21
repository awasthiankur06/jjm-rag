"""Isolated LangGraph state/branch/retry/evidence-validation spike."""
try:
    from langgraph.graph import END, StateGraph
except ImportError as exc:
    raise SystemExit(f"BLOCKED_BY_MISSING_LANGGRAPH: {exc}")

# The state shape is intentionally local to this spike and is not production code.
class BenchmarkState(dict):
    pass

print("LangGraph spike prerequisites available; measure state, branch, retry, and validation steps here.")
