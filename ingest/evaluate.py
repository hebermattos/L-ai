"""Lightweight, offline retrieval-evaluation metrics for labeled source hits."""
import argparse
import json
from pathlib import Path

def evaluate(cases):
    if not cases:
        raise ValueError("No evaluation cases")
    hits, reciprocal = 0, 0.0
    for case in cases:
        expected = set(case["relevant_sources"])
        retrieved = list(case["retrieved_sources"])
        if not expected:
            raise ValueError("Each case must declare at least one relevant source")
        index = next((n for n, value in enumerate(retrieved, 1) if value in expected), None)
        if index is not None:
            hits += 1
            reciprocal += 1 / index
    return {"cases":len(cases), "hit_at_k":hits/len(cases), "mrr":reciprocal/len(cases)}

def main():
    p=argparse.ArgumentParser(description="Score captured RAG retrieval results (no model required)")
    p.add_argument("dataset", type=Path)
    args=p.parse_args()
    cases=json.loads(args.dataset.read_text(encoding="utf-8"))
    print(json.dumps(evaluate(cases), indent=2))
if __name__=="__main__":
    main()
