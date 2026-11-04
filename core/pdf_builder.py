"""Turns the model's light-markdown text into a PDF (reportlab)."""
import re
from io import BytesIO
from xml.sax.saxutils import escape

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer


def _inline(text: str) -> str:
    # The built-in PDF fonts only cover Latin-1, so unsupported characters become '?'
    text = text.encode("cp1252", errors="replace").decode("cp1252")
    text = escape(text)
    return re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text)


def build_pdf(text: str, default_title: str = "Document") -> bytes:
    styles = getSampleStyleSheet()
    body = ParagraphStyle("body", parent=styles["BodyText"], fontSize=11, leading=15)
    bullet = ParagraphStyle("bullet", parent=body, leftIndent=18, bulletIndent=6)

    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=2.2 * cm, rightMargin=2.2 * cm,
                            topMargin=2 * cm, bottomMargin=2 * cm, title=default_title)
    story, para = [], []

    def flush():
        if para:
            story.append(Paragraph(_inline(" ".join(para)), body))
            story.append(Spacer(1, 6))
            para.clear()

    has_title = False
    for raw in text.splitlines():
        line = raw.strip()
        if line.startswith("```"):
            continue
        if not line:
            flush()
        elif line.startswith("### "):
            flush(); story.append(Paragraph(_inline(line[4:]), styles["Heading3"]))
        elif line.startswith("## "):
            flush(); story.append(Paragraph(_inline(line[3:]), styles["Heading2"]))
        elif line.startswith("# "):
            flush()
            story.append(Paragraph(_inline(line[2:]),
                                   styles["Title"] if not has_title else styles["Heading1"]))
            has_title = True
        elif re.match(r"^([-*•]|\d+\.)\s+", line):
            flush()
            content = re.sub(r"^([-*•]|\d+\.)\s+", "", line)
            story.append(Paragraph(_inline(content), bullet, bulletText="•"))
        else:
            para.append(line)
    flush()

    if not has_title:
        story.insert(0, Paragraph(_inline(default_title), styles["Title"]))
    if len(story) <= 1:
        story.append(Paragraph("(empty document)", body))

    doc.build(story)
    return buf.getvalue()
