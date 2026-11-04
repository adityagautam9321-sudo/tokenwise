"""Run the selected Groq model on a task prompt (optionally with web + media)."""
import os
import time

from dotenv import load_dotenv
from groq import Groq

from core.model_registry import MODELS

load_dotenv()

_REQUEST_TIMEOUT_S = 60.0
_MAX_OUTPUT_TOKENS = 4096
_VISION_API_IDS = {"qwen/qwen3.8-27b"}


def available_api_ids() -> list:
    """Return registry api_ids when Groq is configured (no network round-trip)."""
    if not (os.getenv("GROQ_API_KEY") or "").strip():
        return []
    return [m["api_id"] for m in MODELS.values()]


def run(model: dict, plan: dict, context: str = "", image_urls: list | None = None) -> dict:
    """Run task_prompt through the selected Groq model.

    image_urls: optional list of data-URLs / https URLs for vision models.
    """
    key = (os.getenv("GROQ_API_KEY") or "").strip()
    if not key:
        raise RuntimeError("GROQ_API_KEY is missing.")

    prompt = plan["task_prompt"]
    if context:
        prompt = (
            "Here is extra context (web search and/or attached files/photos):\n"
            "-------------------------------------\n"
            f"{context}\n"
            "-------------------------------------\n\n"
            f"User Request: {plan['task_prompt']}\n"
            "Use the context above. If the user asked to rewrite, correct, redesign, "
            "or turn the attachment into a PDF/image card, do that clearly."
        )

    system = (
        "You are a helpful AI studio assistant. Complete the user's task clearly. "
        "If media/files are attached, read them carefully (OCR text, document text). "
        "You can summarise, rewrite, fix mistakes, restructure, or redesign the content. "
        "If multiple questions appear, answer EACH under ## Question N / ## Answer N. "
        "Prefer clean headings and short paragraphs so the result exports well to PDF."
    )
    if plan.get("output_format") == "pdf":
        system += " Structure the result as a polished document with a title and sections."

    api_id = model["api_id"]
    urls = [u for u in (image_urls or []) if u][:3]
    use_vision = bool(urls) and api_id in _VISION_API_IDS

    if use_vision:
        user_content = [{"type": "text", "text": prompt}]
        for u in urls:
            user_content.append({"type": "image_url", "image_url": {"url": u}})
    else:
        user_content = prompt

    kwargs = {
        "model": api_id,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user_content},
        ],
        "temperature": 0.3,
        "max_tokens": _MAX_OUTPUT_TOKENS,
    }
    if model.get("reasoning_effort"):
        kwargs["reasoning_effort"] = model["reasoning_effort"]

    start_time = time.time()
    try:
        client = Groq(api_key=key, timeout=_REQUEST_TIMEOUT_S)
        response = client.chat.completions.create(**kwargs)
    except Exception as e:
        raise RuntimeError(f"Connection or model error: {e}") from e

    choice = response.choices[0].message
    text = (choice.content or "").strip()
    if not text:
        raise RuntimeError(
            f"Model `{api_id}` returned an empty answer. Try another recommended model."
        )

    elapsed = round(time.time() - start_time, 2)
    usage = getattr(response, "usage", None)
    input_tokens = getattr(usage, "prompt_tokens", max(1, len(prompt) // 4))
    output_tokens = getattr(usage, "completion_tokens", max(1, len(text) // 4))

    return {
        "text": text,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "seconds": elapsed,
    }
