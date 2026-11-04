"""Attachments: photos, camera, files → text/OCR context + PDF/image outputs."""
from __future__ import annotations

import base64
import io
import os
import re
from typing import Any

from dotenv import load_dotenv

load_dotenv()

VISION_MODEL = "qwen/qwen3.8-27b"
TEXT_EXTS = {".txt", ".md", ".csv", ".json", ".py", ".js", ".ts", ".html", ".css", ".log"}
IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp"}
MAX_FILE_CHARS = 12_000
MAX_IMAGE_BYTES = 4_000_000  # keep base64 payloads reasonable


def _mime_for_name(name: str) -> str:
    n = (name or "").lower()
    if n.endswith(".png"):
        return "image/png"
    if n.endswith(".webp"):
        return "image/webp"
    if n.endswith(".gif"):
        return "image/gif"
    return "image/jpeg"


def encode_image_bytes(data: bytes, name: str = "photo.jpg") -> str:
    """Return a data-URL for Groq/Gemini vision."""
    if len(data) > MAX_IMAGE_BYTES:
        # Downscale with Pillow when possible
        try:
            from PIL import Image

            img = Image.open(io.BytesIO(data))
            img = img.convert("RGB")
            img.thumbnail((1280, 1280))
            buf = io.BytesIO()
            img.save(buf, format="JPEG", quality=85)
            data = buf.getvalue()
            name = "photo.jpg"
        except Exception:
            data = data[:MAX_IMAGE_BYTES]
    b64 = base64.b64encode(data).decode("ascii")
    return f"data:{_mime_for_name(name)};base64,{b64}"


def extract_text_from_bytes(data: bytes, filename: str) -> str:
    """Read text from common document types."""
    name = (filename or "file").lower()
    ext = "." + name.rsplit(".", 1)[-1] if "." in name else ""

    if ext in TEXT_EXTS or ext == "":
        for enc in ("utf-8", "latin-1", "cp1252"):
            try:
                text = data.decode(enc)
                break
            except Exception:
                text = None
        if text is None:
            return "(Could not decode file as text.)"
        return text[:MAX_FILE_CHARS]

    if ext == ".pdf":
        try:
            from pypdf import PdfReader

            reader = PdfReader(io.BytesIO(data))
            parts = []
            for page in reader.pages[:30]:
                parts.append(page.extract_text() or "")
            text = "\n".join(parts).strip()
            return text[:MAX_FILE_CHARS] if text else "(PDF had no extractable text.)"
        except Exception as e:
            return f"(PDF read failed: {e})"

    if ext in {".docx"}:
        try:
            import zipfile
            from xml.etree import ElementTree as ET

            with zipfile.ZipFile(io.BytesIO(data)) as zf:
                xml = zf.read("word/document.xml")
            root = ET.fromstring(xml)
            texts = [
                node.text for node in root.iter()
                if node.tag.endswith("}t") and node.text
            ]
            return ("\n".join(texts)[:MAX_FILE_CHARS] or "(Empty Word document.)")
        except Exception as e:
            return f"(DOCX read failed: {e})"

    return f"(Unsupported file type `{ext}`. Upload txt/md/csv/pdf/docx or an image.)"


def analyze_image(data: bytes, filename: str = "photo.jpg",
                  instruction: str | None = None) -> dict[str, Any]:
    """OCR + visual understanding via Groq vision (Qwen). Falls back to Gemini."""
    prompt = instruction or (
        "Analyse this image carefully. Include:\n"
        "1) What you see (scene / objects / people)\n"
        "2) All readable text (OCR), preserving layout when possible\n"
        "3) Any issues, errors, or notable details\n"
        "Be concrete and structured."
    )
    data_url = encode_image_bytes(data, filename)

    # 1) Groq vision
    try:
        from groq import Groq

        key = (os.getenv("GROQ_API_KEY") or "").strip()
        if not key:
            raise RuntimeError("GROQ_API_KEY missing")
        client = Groq(api_key=key, timeout=60.0)
        resp = client.chat.completions.create(
            model=VISION_MODEL,
            messages=[{
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": data_url}},
                ],
            }],
            temperature=0.2,
            max_tokens=2048,
        )
        text = (resp.choices[0].message.content or "").strip()
        if text:
            return {"ok": True, "text": text, "data_url": data_url, "via": "groq"}
    except Exception as groq_err:
        last = groq_err

    # 2) Gemini vision fallback
    try:
        from google import genai
        from google.genai import types

        key = (os.getenv("GEMINI_API_KEY") or "").strip()
        if not key:
            raise RuntimeError(f"Gemini key missing; Groq failed: {last}")
        client = genai.Client(api_key=key, http_options={"timeout": 45_000})
        raw = data
        mime = _mime_for_name(filename)
        # Prefer JPEG bytes for Gemini
        try:
            from PIL import Image

            img = Image.open(io.BytesIO(data)).convert("RGB")
            buf = io.BytesIO()
            img.save(buf, format="JPEG", quality=90)
            raw = buf.getvalue()
            mime = "image/jpeg"
        except Exception:
            pass

        for model in ("gemini-3.5-flash-lite", "gemini-3.1-flash-lite", "gemini-3.5-flash"):
            try:
                resp = client.models.generate_content(
                    model=model,
                    contents=[
                        types.Content(
                            role="user",
                            parts=[
                                types.Part.from_bytes(data=raw, mime_type=mime),
                                types.Part.from_text(text=prompt),
                            ],
                        )
                    ],
                    config=types.GenerateContentConfig(max_output_tokens=2048, temperature=0.2),
                )
                text = (resp.text or "").strip()
                if text:
                    return {"ok": True, "text": text, "data_url": data_url, "via": model}
            except Exception:
                continue
        raise RuntimeError("All Gemini vision models failed")
    except Exception as e:
        return {
            "ok": False,
            "text": f"(Image analysis failed: {e})",
            "data_url": data_url,
            "via": None,
        }


def process_upload(data: bytes, filename: str, kind: str = "file") -> dict[str, Any]:
    """Normalise an upload into an attachment dict."""
    name = filename or ("camera.jpg" if kind == "camera" else "upload.bin")
    ext = ("." + name.rsplit(".", 1)[-1].lower()) if "." in name else ""
    is_image = kind in ("photo", "camera") or ext in IMAGE_EXTS

    if is_image:
        vision = analyze_image(data, name)
        return {
            "id": f"{kind}:{name}:{len(data)}",
            "kind": kind if kind in ("photo", "camera") else "photo",
            "name": name,
            "is_image": True,
            "summary": vision.get("text") or "",
            "data_url": vision.get("data_url"),
            "via": vision.get("via"),
            "ok": bool(vision.get("ok")),
        }

    text = extract_text_from_bytes(data, name)
    return {
        "id": f"file:{name}:{len(data)}",
        "kind": "file",
        "name": name,
        "is_image": False,
        "summary": text,
        "data_url": None,
        "via": "extractor",
        "ok": True,
    }


def attachments_context(attachments: list[dict]) -> str:
    """Flatten attachments into prompt context for advisor / runner."""
    if not attachments:
        return ""
    blocks = []
    for i, a in enumerate(attachments, 1):
        label = a.get("kind", "file").upper()
        name = a.get("name", "attachment")
        body = (a.get("summary") or "").strip()
        blocks.append(
            f"--- ATTACHMENT {i} ({label}: {name}) ---\n{body}\n--- END ATTACHMENT {i} ---"
        )
    return (
        "The user attached media. Use it as source material. "
        "You can summarise, rewrite, correct, expand, or redesign it, "
        "and produce a clean PDF-ready document or a revised image card.\n\n"
        + "\n\n".join(blocks)
    )


def image_data_urls(attachments: list[dict], limit: int = 3) -> list[str]:
    urls = []
    for a in attachments or []:
        if a.get("data_url"):
            urls.append(a["data_url"])
        if len(urls) >= limit:
            break
    return urls


def render_result_image(title: str, body: str, accent=(37, 99, 235)) -> bytes:
    """Create a shareable PNG 'AI card' from model output (Pillow)."""
    from PIL import Image, ImageDraw, ImageFont

    W, H = 1080, 1350
    img = Image.new("RGB", (W, H), (7, 11, 22))
    draw = ImageDraw.Draw(img)

    # Soft panels
    draw.rounded_rectangle((40, 40, W - 40, H - 40), radius=36, fill=(18, 28, 51))
    draw.rounded_rectangle((40, 40, W - 40, 180), radius=36, fill=accent)

    try:
        font_title = ImageFont.truetype("arial.ttf", 42)
        font_body = ImageFont.truetype("arial.ttf", 28)
        font_small = ImageFont.truetype("arial.ttf", 22)
    except Exception:
        font_title = ImageFont.load_default()
        font_body = font_title
        font_small = font_title

    title = (title or "TokenWise result")[:80]
    draw.text((70, 85), title, fill=(255, 255, 255), font=font_title)
    draw.text((70, 200), "Generated by TokenWise", fill=(148, 163, 184), font=font_small)

    # Wrap body text
    clean = re.sub(r"[#>*`]+", "", body or "")
    clean = re.sub(r"\n{3,}", "\n\n", clean).strip()
    words = clean.split()
    lines, cur = [], ""
    for w in words:
        trial = (cur + " " + w).strip()
        if len(trial) > 52:
            lines.append(cur)
            cur = w
        else:
            cur = trial
    if cur:
        lines.append(cur)

    y = 260
    for line in lines[:28]:
        draw.text((70, y), line[:60], fill=(232, 238, 252), font=font_body)
        y += 36
        if y > H - 100:
            break

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def direct_chat_with_attachments(
    question: str,
    attachments: list[dict],
    history: list[dict] | None = None,
) -> str:
    """Answer a question directly using vision / text, no advisor routing.

    For image attachments the actual image pixels are sent to the vision model.
    For document attachments the extracted text is included in the prompt.
    history: list of {role, content} dicts (plain text only) for multi-turn context.
    Returns the assistant reply string.
    """
    import os
    from groq import Groq

    key = (os.getenv("GROQ_API_KEY") or "").strip()
    if not key:
        raise RuntimeError("GROQ_API_KEY is missing.")

    # Build user content
    image_urls = [
        a["data_url"]
        for a in attachments
        if a.get("is_image") and a.get("data_url")
    ][:4]

    text_blocks = []
    for a in attachments:
        if not a.get("is_image"):
            body = (a.get("summary") or "").strip()
            if body:
                text_blocks.append(
                    f"[Document: {a.get('name')}]\n{body[:8000]}"
                )

    # Compose the user message
    parts: list[dict] = []
    if text_blocks:
        parts.append({"type": "text", "text": "\n\n".join(text_blocks)})
    if question.strip():
        parts.append({"type": "text", "text": question.strip()})
    elif not text_blocks:
        parts.append({"type": "text", "text": "Please describe and analyse these attachments."})

    for url in image_urls:
        parts.append({"type": "image_url", "image_url": {"url": url}})

    # Build messages list
    system = (
        "You are a helpful AI assistant. The user has uploaded files or images. "
        "Look at the images carefully and answer the user's question directly and concisely. "
        "If there is text in the image, read and include it. "
        "If a document is attached, use its content to answer. "
        "Be natural and conversational — this is a chat, not a report."
    )

    messages: list[dict] = [{"role": "system", "content": system}]

    # Include last few turns of history for context (text only)
    for msg in (history or [])[-6:]:
        role = msg.get("role", "user")
        content = msg.get("content", "")
        # Strip attachment context blocks from history to keep it clean
        if "--- ATTACHMENT" in content:
            content = content.split("\n\n---")[0].strip()
        if content:
            messages.append({"role": role, "content": content})

    # Current user turn with image(s)
    messages.append({"role": "user", "content": parts if (image_urls or len(parts) > 1) else (parts[0]["text"] if parts else question)})

    client = Groq(api_key=key, timeout=60.0)
    resp = client.chat.completions.create(
        model=VISION_MODEL,
        messages=messages,
        temperature=0.3,
        max_tokens=2048,
    )
    return (resp.choices[0].message.content or "").strip()
