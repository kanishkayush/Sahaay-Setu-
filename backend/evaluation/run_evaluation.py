"""Run deterministic retrieval and multi-turn evaluation without an LLM."""

from __future__ import annotations

import argparse
import json
import os
from collections import defaultdict
from datetime import date
from pathlib import Path

from evaluation.dataset_v1 import (
    BUSINESS_IDS,
    EDUCATION_ID,
    MULTI_TURN_CONVERSATIONS,
    SINGLE_TURN_CASES,
    TERM_ID,
    VOICE_LIKE_CASES,
    EvalCase,
)
from app.rag.language_detect import detect_language_and_intent
from app.rag.query_context import build_retrieval_query
from app.rag.retriever import reset_store, retrieve_ranked_schemes
from app.schemas.chat import ChatProfile


def _rank(query: str, profile: ChatProfile | None = None):
    detection = detect_language_and_intent(query)
    spec = build_retrieval_query(query, profile=profile, detection=detection)
    ranked = retrieve_ranked_schemes(
        query=spec.search_text,
        organization_filter=spec.organization_scope,
        domain_filter=spec.domain,
        assistance_type_filter=spec.assistance_type,
        retrieval_query=spec,
        top_k=5,
    )
    return detection, spec, ranked


def _voice_case(index: int, query: str) -> EvalCase:
    lowered = query.lower()
    if lowered in {"btech", "बीटेक", "पढ़ाई", "padhai", "education", "college"}:
        return EvalCase(f"voice-{index:02}", query, "hi" if index not in {4, 19, 20} else "en", "EDUCATION", "LOAN", (EDUCATION_ID,), "voice")
    if lowered in {"shop", "दुकान", "business"}:
        return EvalCase(f"voice-{index:02}", query, "hi" if lowered == "दुकान" else "en", "BUSINESS", "LOAN", BUSINESS_IDS, "voice")
    return EvalCase(f"voice-{index:02}", query, "hi" if any("\u0900" <= c <= "\u097f" for c in query) or lowered in {"kheti"} else "en", "AGRICULTURE", "LOAN", (TERM_ID,), "voice")


def _evaluate_cases(cases: list[EvalCase]):
    sums = defaultdict(float)
    groups: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))
    variants: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))
    failures = []
    for case in cases:
        detection, spec, ranked = _rank(case.query)
        ids = [item.scheme_id for item in ranked]
        expected = set(case.expected_scheme_ids)
        position = next((i + 1 for i, sid in enumerate(ids) if sid in expected), None)
        no_match_correct = not expected and not ids
        top_correct = bool(position == 1)
        for bucket in (sums, groups[case.group], variants[case.variant]):
            bucket["count"] += 1
            bucket["recall_1"] += float(bool(position and position <= 1) or no_match_correct)
            bucket["recall_3"] += float(bool(position and position <= 3) or no_match_correct)
            bucket["recall_5"] += float(bool(position and position <= 5) or no_match_correct)
            bucket["mrr"] += (1 / position) if position else float(no_match_correct)
            bucket["language"] += float(detection.detected_language == case.language)
            bucket["domain"] += float(spec.domain == case.domain)
            bucket["assistance"] += float(
                case.assistance_type is None or spec.assistance_type == case.assistance_type
            )
            bucket["organization"] += float(not ranked or all(r.organization == "NSFDC" for r in ranked))
            contaminated = False
            if case.domain == "EDUCATION":
                contaminated = any(r.scheme_id != EDUCATION_ID for r in ranked)
            elif case.domain in {"AGRICULTURE", "BUSINESS"}:
                contaminated = any(r.scheme_id == EDUCATION_ID for r in ranked)
            bucket["contamination_free"] += float(not contaminated)
            bucket["active_grounded"] += float(
                not ranked
                or all(
                    getattr(r, "lifecycle_status", "UNCLEAR_STATUS")
                    in {"CURRENT_ACTIVE", "CURRENT_BUT_LIMITED"}
                    for r in ranked
                )
            )
        if not top_correct and not no_match_correct:
            failures.append(
                {
                    "id": case.id,
                    "query": case.query,
                    "expected": list(expected),
                    "actual": ids,
                    "domain": spec.domain,
                }
            )
    return sums, groups, variants, failures


def _percentage_metrics(raw):
    count = max(raw["count"], 1)
    return {
        key: round(value / count, 4)
        for key, value in raw.items()
        if key != "count"
    } | {"count": int(raw["count"])}


def _apply_turn(profile: ChatProfile, query: str):
    _, spec, _ = _rank(query, profile)
    if spec.domain in {"EDUCATION", "AGRICULTURE", "BUSINESS"}:
        profile.projectType = spec.domain
    if spec.activity:
        profile.activity = spec.activity
    if spec.requested_amount is not None:
        profile.estimatedProjectCost = int(spec.requested_amount)
    return spec


def _multi_turn_metrics():
    retained = switched = relevant = 0
    failures = []
    for conversation in MULTI_TURN_CONVERSATIONS:
        profile = ChatProfile()
        domains = []
        for turn in conversation["turns"]:
            domains.append(_apply_turn(profile, turn).domain)
        _, final_spec, ranked = _rank(conversation["turns"][-1], profile)
        ids = [item.scheme_id for item in ranked]
        target = conversation["domain"]
        retained += int(final_spec.domain == target)
        has_switch = len({domain for domain in domains if domain}) > 1
        switched += int(not has_switch or final_spec.domain == target)
        relevant += int(bool(set(ids) & set(conversation["expected_scheme_ids"])))
        if final_spec.domain != target or not set(ids) & set(conversation["expected_scheme_ids"]):
            failures.append({"id": conversation["id"], "domains": domains, "actual": ids})
    count = len(MULTI_TURN_CONVERSATIONS)
    return {
        "count": count,
        "context_retention": round(retained / count, 4),
        "topic_switch_accuracy": round(switched / count, 4),
        "final_retrieval_relevance": round(relevant / count, 4),
        "failures": failures,
    }


def run():
    if os.environ.get("SAARTHI_MOCK_EMBEDDING") == "1":
        # Query and corpus vectors must come from the same provider. Rebuild an
        # in-memory test index instead of comparing mock queries to production
        # MiniLM vectors.
        from app.rag.embeddings import embed
        from app.rag.scheme_knowledge import load_knowledge_chunks
        from app.rag.vector_store import build_store

        reset_store(build_store(load_knowledge_chunks(), embed))
    voice_cases = [_voice_case(i, query) for i, query in enumerate(VOICE_LIKE_CASES, 1)]
    raw, groups, variants, failures = _evaluate_cases([*SINGLE_TURN_CASES, *voice_cases])
    ambiguous = groups["ambiguous"]
    report = {
        "dataset_version": "v1",
        "evaluated_on": date.today().isoformat(),
        "single_turn_cases": len(SINGLE_TURN_CASES),
        "voice_like_cases": len(voice_cases),
        "multi_turn_conversations": len(MULTI_TURN_CONVERSATIONS),
        "overall": _percentage_metrics(raw),
        "groups": {name: _percentage_metrics(values) for name, values in groups.items()},
        "language_variants": {
            name: _percentage_metrics(values) for name, values in variants.items()
        },
        "no_match_precision": round(ambiguous["recall_1"] / max(ambiguous["count"], 1), 4),
        "multi_turn": _multi_turn_metrics(),
        "top_1_failures": failures,
    }
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = run()
    rendered = json.dumps(result, ensure_ascii=False, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)
