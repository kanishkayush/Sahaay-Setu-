from evaluation.dataset_v1 import (
    MULTI_TURN_CONVERSATIONS,
    SINGLE_TURN_CASES,
    VOICE_LIKE_CASES,
)
from evaluation.run_evaluation import run


def test_dataset_meets_required_coverage():
    assert len(SINGLE_TURN_CASES) >= 220
    assert len(MULTI_TURN_CONVERSATIONS) >= 20
    assert len(VOICE_LIKE_CASES) >= 20


def test_retrieval_quality_release_thresholds():
    report = run()
    overall = report["overall"]
    assert overall["recall_1"] >= 0.95
    assert overall["recall_3"] >= 0.97
    assert overall["mrr"] >= 0.95
    assert overall["domain"] >= 0.95
    assert overall["organization"] == 1.0
    assert overall["contamination_free"] == 1.0
    assert report["no_match_precision"] == 1.0
    assert report["multi_turn"]["context_retention"] >= 0.95
    assert report["multi_turn"]["topic_switch_accuracy"] >= 0.95
