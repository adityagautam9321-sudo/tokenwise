"""Deterministic ranking: quality fit + token cost + token count."""
from core.model_registry import MODELS

WEB_CONTEXT_TOKENS = 1200  # rough size of attached search results


def _estimate(model: dict, plan: dict) -> dict:
    in_tok = plan["est_input_tokens"] + (WEB_CONTEXT_TOKENS if plan["needs_web"] else 0)
    out_tok = int(plan["est_output_tokens"] * model["verbosity"])
    cost = (in_tok * model["price_in"] + out_tok * model["price_out"]) / 1_000_000
    return {
        "in_tokens": in_tok,
        "out_tokens": out_tok,
        "total_tokens": in_tok + out_tok,
        "cost": cost,
    }


def recommend(plan, available_api_ids=None, top_n=2, priority=0.5, adjustments=None,
              prefer_vision=False):
    """Returns the top_n models, best first.

    priority: 0.0 = cheapest / fewest tokens, 1.0 = highest quality fit.
    adjustments: optional {(model_key, task_type): delta} from feedback learning.
    prefer_vision: boost models with vision=True when photos/camera are attached.
    """
    candidates = {
        k: m for k, m in MODELS.items()
        if available_api_ids is None or m["api_id"] in available_api_ids
    }
    if len(candidates) < top_n:  # availability check failed -> use all
        candidates = dict(MODELS)

    # Hard tasks must use a strong-enough model (when at least top_n qualify)
    min_fit = {1: 0, 2: 0, 3: 6, 4: 8, 5: 8}[plan["complexity"]]
    strong = {k: m for k, m in candidates.items() if m["fit"][plan["task_type"]] >= min_fit}
    if len(strong) >= top_n:
        candidates = strong

    rows = []
    for key, m in candidates.items():
        est = _estimate(m, plan)
        base_fit = m["fit"][plan["task_type"]]
        delta = (adjustments or {}).get((key, plan["task_type"]), 0)
        if prefer_vision and m.get("vision"):
            delta += 2
        fit = min(10, max(1, base_fit + delta))
        quality = fit / 10
        rows.append({"id": key, "model": m, "fit": fit, "quality": quality, **est})

    min_cost = max(min(r["cost"] for r in rows), 1e-9)
    min_tok = min(r["total_tokens"] for r in rows)

    w_q = 0.2 + 0.6 * priority  # 0 = cheapest, 1 = best quality
    w_cost, w_tok = (1 - w_q) * 0.6, (1 - w_q) * 0.4

    for r in rows:
        cost_eff = (min_cost / max(r["cost"], 1e-9)) ** 0.5
        tok_eff = (min_tok / r["total_tokens"]) ** 0.5
        r["score"] = round(100 * (w_q * r["quality"] + w_cost * cost_eff + w_tok * tok_eff))
        r["label"] = r["model"]["label"]
        r["reason"] = (
            f"{r['model']['note']} Fit for this task: {r['fit']}/10. "
            f"Estimated {r['total_tokens']:,} tokens (about ${r['cost']:.5f})."
        )

    rows.sort(key=lambda r: r["score"], reverse=True)
    return rows[:top_n]


def savings_vs_baseline(model: dict, in_tok: int, out_tok: int) -> dict:
    """Compare against the most expensive model in the pool, using the same tokens."""
    cost = lambda m: (in_tok * m["price_in"] + out_tok * m["price_out"]) / 1e6
    base = max(MODELS.values(), key=lambda m: m["price_out"])
    c, b = cost(model), cost(base)
    return {
        "baseline": base["label"],
        "cost": c,
        "baseline_cost": b,
        "percent": round(100 * (1 - c / b)) if b else 0,
        "saved": max(0.0, b - c),
    }
