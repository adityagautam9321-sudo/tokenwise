"""
Candidate models served through Groq.

- price_in / price_out : USD per 1M tokens (approximate)
- verbosity            : output-token multiplier (reasoning models spend extra)
- fit                  : 1-10 quality heuristic per task type
If Groq retires a model, the app detects it automatically and skips it.
"""

TASK_TYPES = [
    "pdf_generation", "summarization", "question_answering", "coding",
    "writing", "translation", "data_extraction", "general",
]


def _fit(*scores):
    return dict(zip(TASK_TYPES, scores))


MODELS = {
    "gpt-oss-20b": {
        "label": "GPT-OSS 20B",
        "api_id": "openai/gpt-oss-20b",
        "price_in": 0.075, "price_out": 0.30,
        "context": 131072, "verbosity": 1.5, "reasoning_effort": "low",
        "fit": _fit(7, 7, 7, 8, 7, 6, 7, 7),
        "note": "Cheap reasoning model, good for coding and logic.",
    },
    "gpt-oss-120b": {
        "label": "GPT-OSS 120B",
        "api_id": "openai/gpt-oss-120b",
        "price_in": 0.15, "price_out": 0.60,
        "context": 131072, "verbosity": 1.5, "reasoning_effort": "low",
        "fit": _fit(9, 9, 9, 9, 9, 8, 9, 9),
        "note": "Strongest all-rounder in the pool.",
    },
    "qwen3.8-27b": {
        "label": "Qwen3.8 27B",
        "api_id": "qwen/qwen3.8-27b",
        "price_in": 0.15, "price_out": 0.45,
        "context": 131072, "verbosity": 1.2,
        "vision": True,
        "fit": _fit(8, 8, 8, 8, 8, 9, 8, 9),
        "note": "Vision + text model — best for photos, OCR, and rewritten media.",
    },
    "allam-2-7b": {
        "label": "ALLaM 2 7B",
        "api_id": "allam-2-7b",
        "price_in": 0.05, "price_out": 0.08,
        "context": 8192, "verbosity": 1.0,
        "fit": _fit(5, 6, 6, 4, 5, 7, 5, 5),
        "note": "Tiny and very cheap. Best for simple tasks.",
    },
}
