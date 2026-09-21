# Framework Bake-off

## Result

`CUSTOM_PREFERRED`

This is a controlled comparative spike, not a rewrite. The existing custom Python implementation is the observed baseline and its full test suite remains green: 23 passed.

## Environment limitation

LangChain, LangGraph, and LlamaIndex are not installed. No packages were added and no production code was rewritten around them. Their runtime integration effort, latency, and dependency footprint therefore remain unmeasured.

## Workflow comparison

| Workflow | Custom Python | LangChain | LangGraph | LlamaIndex |
|---|---|---|---|---|
| Semantic retrieval | Existing validated component | Runtime spike unavailable | Not a graph requirement | Runtime spike unavailable |
| Exact retrieval | Existing deterministic component | No demonstrated replacement | No demonstrated replacement | No demonstrated replacement |
| Structured retrieval | Existing row/column logic | Tool wrapper would still be custom | State wrapper would still be custom | Structured adapter would still be custom |
| Hybrid retrieval | Existing decomposition/fusion | Integration possible but unmeasured | No stateful need shown | Integration possible but unmeasured |
| Cross-document retrieval | Existing alignment metadata | Provenance logic remains custom | Branching not required by current workflow | Schema alignment remains custom |
| Evidence/provenance | Native typed evidence | Requires explicit metadata contract | Requires explicit state contract | Requires explicit node/metadata contract |

## Decision

Custom Python is preferred because it already maps to the validated architecture, has direct tests, and avoids introducing abstractions without measured benefit. LangChain, LangGraph, and LlamaIndex remain optional future experiments only if a concrete integration problem appears.

LangGraph is specifically not justified: no durable state, human approval, resumable workflow, or complex branching requirement has been demonstrated.
