"""Gemini advisor: chats with the user and returns a structured task plan."""
import json
import os
import re
import time

from dotenv import load_dotenv

from core.model_registry import TASK_TYPES

load_dotenv()

SYSTEM_PROMPT = f"""You are the advisor of TokenWise, an app that picks the cheapest AI model that can do a user's job well.
Chat briefly with the user to understand the job. If the request is too vague to estimate
(missing the actual content, topic or goal), ask ONE short clarifying question and set "ready" to false.
Otherwise set "ready" to true.

MULTI-QUESTION RULE:
If the user asks two or more distinct questions in one message, set ready=true and build task_prompt so the
worker model must answer EACH question in its own clearly numbered section:
  ## Question 1
  <restate briefly>
  ## Answer 1
  ...
  ## Question 2
  ...
Never merge multiple questions into one blended paragraph.

PDF RULE: Prefer output_format "pdf" when the user wants a report, summary pack, recommendations list,
image analysis write-up, rewritten document, or explicitly asks for a PDF.

MEDIA RULE: If ATTACHMENT blocks appear in the chat (photos, camera shots, or files), set ready=true
when the user asks to read / summarise / rewrite / fix / redesign them. Put the attachment content
into task_prompt (or reference it) and ask the worker to produce a clear rewritten result suitable
for PDF and for an AI image card.

Reply with JSON ONLY, using exactly these keys:
{{
  "ready": boolean,
  "reply": string,
  "task_type": one of {TASK_TYPES},
  "output_format": "text" or "pdf",
  "complexity": integer 1-5,
  "est_input_tokens": integer,
  "est_output_tokens": integer,
  "needs_web": boolean,
  "search_query": string,
  "task_prompt": string
}}
Never wrap the JSON in markdown."""

# Prefer Lite first: faster + usually less 503 pressure than flagship Flash.
_FALLBACK_MODELS = (
    "gemini-3.5-flash-lite",
    "gemini-3.1-flash-lite",
    "gemini-3.5-flash",
    "gemini-3.6-flash",
)
_TIMEOUT_MS = 35_000
_MAX_OUTPUT_TOKENS = 512
_CHAT_TAIL = 8  # keep prompt small for lower latency


def _client_gemini():
    from google import genai

    key = (os.getenv("GEMINI_API_KEY") or "").strip()
    if not key:
        raise RuntimeError("GEMINI_API_KEY is missing.")
    return genai.Client(api_key=key, http_options={"timeout": _TIMEOUT_MS})


def _model_chain() -> list[str]:
    preferred = (os.getenv("GEMINI_MODEL") or "").strip()
    chain = []
    if preferred:
        chain.append(preferred)
    for m in _FALLBACK_MODELS:
        if m not in chain:
            chain.append(m)
    return chain


def _parse_json(text: str) -> dict:
    text = (text or "").strip()
    text = re.sub(r"^```(?:json)?|```$", "", text, flags=re.MULTILINE).strip()
    # Recover if the model adds prose around the object.
    if not text.startswith("{"):
        start, end = text.find("{"), text.rfind("}")
        if start != -1 and end != -1 and end > start:
            text = text[start : end + 1]
    return json.loads(text)


def _clean(plan: dict) -> dict:
    task = plan.get("task_type")
    return {
        "ready": bool(plan.get("ready", False)),
        "reply": str(plan.get("reply", "")),
        "task_type": task if task in TASK_TYPES else "general",
        "output_format": "pdf" if plan.get("output_format") == "pdf" else "text",
        "complexity": min(5, max(1, int(plan.get("complexity", 3) or 3))),
        "est_input_tokens": max(50, int(plan.get("est_input_tokens", 300) or 300)),
        "est_output_tokens": max(50, int(plan.get("est_output_tokens", 600) or 600)),
        "needs_web": bool(plan.get("needs_web", False)),
        "search_query": str(plan.get("search_query", "") or ""),
        "task_prompt": str(plan.get("task_prompt", "") or ""),
    }


def _split_questions(text: str) -> list[str]:
    """Best-effort split when the user packs multiple questions into one message."""
    parts = re.split(r"(?:\n\s*\n+|\n(?=\s*(?:\d+[\).]|[-*•]|Q\d+[:.)]))|(?<=[?])\s+(?=[A-Z0-9]))", text)
    parts = [p.strip(" \n\t-•*") for p in parts if p and p.strip()]
    # Also split on " and separately" / "also," style cues
    if len(parts) < 2:
        alt = re.split(r"(?i)\b(?:and separately|also tell me|second(?:ly)?|another question)\b[:\s]*", text)
        parts = [p.strip() for p in alt if p and p.strip()]
    return parts if len(parts) >= 2 else [text.strip()]


def _multi_question_prompt(questions: list[str]) -> str:
    numbered = "\n".join(f"{i}. {q}" for i, q in enumerate(questions, 1))
    return (
        "The user asked multiple questions. Answer EACH one separately and clearly.\n"
        "Use this exact structure:\n"
        "## Question 1\n<short restatement>\n## Answer 1\n...\n"
        "## Question 2\n...\n## Answer 2\n...\n"
        "(continue for every question)\n\n"
        f"Questions:\n{numbered}"
    )


def _heuristic_plan(chat: list, work_mode: str | None = None) -> dict:
    last_user = next(
        (m["content"] for m in reversed(chat) if m["role"] == "user"),
        "Perform the task",
    )
    lower = last_user.lower()
    needs_web = any(w in lower for w in ("today", "latest", "news", "current", "price", "202"))
    task_type = "general"
    if any(w in lower for w in ("pdf", "report")):
        task_type = "pdf_generation"
    elif any(w in lower for w in ("summar", "tldr")):
        task_type = "summarization"
    elif any(w in lower for w in ("code", "python", "script", "bug", "function", "math")):
        task_type = "coding"
    elif any(w in lower for w in ("recommend", "suggest")):
        task_type = "question_answering"
    elif any(w in lower for w in ("image", "picture", "detect", "photo")):
        task_type = "data_extraction"
    elif any(w in lower for w in ("translat",)):
        task_type = "translation"
    elif any(w in lower for w in ("write", "essay", "email", "blog")):
        task_type = "writing"

    prefer_pdf = "pdf" in lower or "report" in lower or "summar" in lower or "recommend" in lower
    if work_mode:
        try:
            from core.work_modes import WORK_MODES
            mode = WORK_MODES.get(work_mode) or {}
            task_type = mode.get("task_type", task_type)
            needs_web = needs_web or bool(mode.get("needs_web"))
            prefer_pdf = prefer_pdf or bool(mode.get("prefer_pdf"))
        except Exception:
            pass

    questions = _split_questions(last_user)
    task_prompt = _multi_question_prompt(questions) if len(questions) > 1 else last_user

    return {
        "ready": True,
        "reply": (
            f"I found {len(questions)} questions — I'll answer each separately."
            if len(questions) > 1
            else "I built a task plan from your request (advisor model was busy)."
        ),
        "task_type": task_type,
        "output_format": "pdf" if prefer_pdf else "text",
        "complexity": 3,
        "est_input_tokens": max(50, len(last_user) // 4),
        "est_output_tokens": 600 * max(1, len(questions)),
        "needs_web": needs_web,
        "search_query": last_user[:120] if needs_web else "",
        "task_prompt": task_prompt,
    }


def _call_gemini(transcript: str, model: str) -> dict:
    from google.genai import types

    client = _client_gemini()
    resp = client.models.generate_content(
        model=model,
        contents=transcript,
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            response_mime_type="application/json",
            temperature=0.2,
            max_output_tokens=_MAX_OUTPUT_TOKENS,
        ),
    )
    return _clean(_parse_json(resp.text))


def _call_groq_advisor(transcript: str) -> dict:
    """Fast JSON fallback via Groq when Gemini is overloaded."""
    from groq import Groq

    key = (os.getenv("GROQ_API_KEY") or "").strip()
    if not key:
        raise RuntimeError("GROQ_API_KEY missing for advisor fallback")

    client = Groq(api_key=key, timeout=30.0)
    resp = client.chat.completions.create(
        model="qwen/qwen3.8-27b",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": transcript},
        ],
        temperature=0.2,
        max_tokens=_MAX_OUTPUT_TOKENS,
        response_format={"type": "json_object"},
    )
    return _clean(_parse_json(resp.choices[0].message.content or ""))


def analyze(chat: list, work_mode: str | None = None) -> dict:
    """chat = [{'role': 'user'|'assistant', 'content': str}, ...]"""
    recent = chat[-_CHAT_TAIL:]
    mode_note = f"\nACTIVE_WORK_MODE: {work_mode}" if work_mode else ""
    transcript = "\n".join(f"{m['role'].upper()}: {m['content']}" for m in recent) + mode_note

    # 1) Groq first — usually <2s and avoids Gemini 503 spikes.
    try:
        t0 = time.time()
        plan = _call_groq_advisor(transcript)
        print(f"Advisor OK via Groq in {time.time() - t0:.2f}s")
    except Exception as groq_err:
        print(f"Groq advisor failed ({groq_err}); trying Gemini...")
        plan = None
        last_err = groq_err
        for model in _model_chain():
            for attempt in range(2):  # one quick retry on transient 503
                try:
                    t0 = time.time()
                    plan = _call_gemini(transcript, model)
                    print(f"Advisor OK via {model} in {time.time() - t0:.2f}s")
                    break
                except Exception as e:
                    last_err = e
                    msg = str(e)
                    transient = (
                        "503" in msg
                        or "UNAVAILABLE" in msg
                        or "high demand" in msg.lower()
                    )
                    print(f"Advisor {model} failed ({e})")
                    if transient and attempt == 0:
                        time.sleep(0.6)
                        continue
                    break
            if plan is not None:
                break
        if plan is None:
            print(f"All advisors failed ({last_err}); using heuristic plan.")
            plan = _heuristic_plan(chat, work_mode=work_mode)

    if plan["ready"] and not plan["task_prompt"]:
        plan["task_prompt"] = "\n".join(m["content"] for m in chat if m["role"] == "user")

    # Enforce multi-question structure even if the LLM forgot.
    last_user = next((m["content"] for m in reversed(chat) if m["role"] == "user"), "")
    qs = _split_questions(last_user) if last_user else []
    if plan["ready"] and len(qs) > 1 and "## Question 1" not in plan["task_prompt"]:
        plan["task_prompt"] = _multi_question_prompt(qs)
        if "separately" not in (plan.get("reply") or "").lower():
            plan["reply"] = (plan.get("reply") or "Got it.") + f" I'll answer all {len(qs)} questions separately."

    if work_mode:
        try:
            from core.work_modes import WORK_MODES
            mode = WORK_MODES.get(work_mode) or {}
            if mode.get("prefer_pdf"):
                plan["output_format"] = "pdf"
            if mode.get("needs_web") and not plan.get("search_query"):
                plan["needs_web"] = True
                plan["search_query"] = last_user[:120]
        except Exception:
            pass

    return plan
