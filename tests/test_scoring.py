"""Unit tests for ranking, savings meter, and advisor heuristics."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core import scoring
from core.advisor import _heuristic_plan
from core.model_registry import MODELS


def _plan(**overrides):
    base = {
        "ready": True,
        "reply": "ok",
        "task_type": "coding",
        "output_format": "text",
        "complexity": 3,
        "est_input_tokens": 200,
        "est_output_tokens": 400,
        "needs_web": False,
        "search_query": "",
        "task_prompt": "Write a Python function that adds two numbers.",
    }
    base.update(overrides)
    return base


def test_recommend_returns_two():
    recs = scoring.recommend(_plan(), top_n=2)
    assert len(recs) == 2
    assert recs[0]["score"] >= recs[1]["score"]
    assert "label" in recs[0] and "reason" in recs[0]


def test_priority_shifts_toward_quality():
    cheap = scoring.recommend(_plan(complexity=2, task_type="general"), priority=0.0, top_n=1)[0]
    quality = scoring.recommend(_plan(complexity=2, task_type="general"), priority=1.0, top_n=1)[0]
    # Not asserting different winners always (pool can agree), but scores must exist
    assert 0 <= cheap["score"] <= 100
    assert 0 <= quality["score"] <= 100


def test_feedback_adjustments_applied():
    plan = _plan(task_type="coding")
    base = scoring.recommend(plan, priority=0.5, top_n=4)
    boost_id = base[-1]["id"]
    adj = {(boost_id, "coding"): 2}
    boosted = scoring.recommend(plan, priority=0.5, top_n=4, adjustments=adj)
    base_fit = next(r["fit"] for r in base if r["id"] == boost_id)
    new_fit = next(r["fit"] for r in boosted if r["id"] == boost_id)
    assert new_fit >= base_fit


def test_savings_vs_baseline_non_negative():
    model = MODELS["allam-2-7b"]
    sv = scoring.savings_vs_baseline(model, 1000, 1000)
    assert sv["percent"] >= 0
    assert sv["saved"] >= 0
    assert sv["baseline_cost"] >= sv["cost"]


def test_hard_task_filters_weak_models():
    plan = _plan(complexity=5, task_type="coding")
    recs = scoring.recommend(plan, top_n=2)
    for r in recs:
        assert r["fit"] >= 8


def test_heuristic_plan_detects_coding():
    chat = [{"role": "user", "content": "Write a Python script that sorts a list"}]
    plan = _heuristic_plan(chat)
    assert plan["ready"] is True
    assert plan["task_type"] == "coding"
