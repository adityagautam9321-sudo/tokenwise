"""Assistant page — unified chat + file/image upload."""
import streamlit as st

from core import advisor, runner, scoring
from core.media import (
    attachments_context,
    direct_chat_with_attachments,
    process_upload,
)
from core.tokenizer import TOKENIZER_MODELS, tokenize_text
from core.work_modes import WORK_MODES
from db.user import (
    delete_conversation,
    get_conversation,
    get_fit_adjustments,
    list_conversations,
    save_conversation,
)
from ui.theme import hero

ss = st.session_state
ss.setdefault("chat", [])
ss.setdefault("plan", None)
ss.setdefault("recs", [])
ss.setdefault("priority", 0.5)
ss.setdefault("conversation_id", None)
ss.setdefault("work_mode", None)
ss.setdefault("attachments", [])
ss.setdefault("camera_active", False)
# Track which uploader file ids have already been processed
ss.setdefault("_processed_upload_ids", set())

mode = WORK_MODES.get(ss.work_mode) if ss.work_mode else None
pill = f"Mode · {mode['title']}" if mode else "AI assistant"
hero(
    "TokenWise",
    mode["blurb"] if mode else "Upload files or images and ask me anything about them.",
    pill=pill,
)

# ── sidebar ──────────────────────────────────────────────────────────────────
with st.sidebar:
    # ── Past conversations list ──
    try:
        _conv_list = list_conversations(ss.user["id"], limit=40)
    except Exception:
        _conv_list = []

    st.markdown("#### Chats")

    if _conv_list:
        for _c in _conv_list:
            _is_active = ss.get("conversation_id") == _c["id"]
            _label = _c["title"] or "Untitled"
            _short = (_label[:32] + "…") if len(_label) > 33 else _label

            _col_title, _col_del = st.columns([5, 1])
            with _col_title:
                if st.button(
                    _short,
                    key=f"conv_{_c['id']}",
                    use_container_width=True,
                    type="primary" if _is_active else "secondary",
                    help=_label,
                ):
                    # Save current chat before switching, so nothing is lost
                    if ss.get("chat") and len(ss.get("chat", [])) > 1:
                        try:
                            ss.conversation_id = save_conversation(
                                ss.user["id"], ss.chat, ss.plan, ss.conversation_id
                            )
                        except Exception:
                            pass
                    try:
                        _full = get_conversation(ss.user["id"], _c["id"])
                    except Exception as _e:
                        st.error(f"Could not load: {_e}")
                        _full = None
                    if _full:
                        ss.conversation_id = _full["id"]
                        ss.chat = _full["messages"]
                        ss.plan = _full.get("plan")
                        ss.recs = []
                        ss.result = None
                        ss.result_pdf = None
                        ss.result_image = None
                        ss.attachments = []
                        ss._processed_upload_ids = set()
                        ss.pop("race_ids", None)
                        ss.pop("race_results", None)
                        ss.pop("run_pending", None)
                        st.rerun()
            with _col_del:
                if st.button("🗑", key=f"del_{_c['id']}", help="Delete this chat"):
                    try:
                        delete_conversation(ss.user["id"], _c["id"])
                        if ss.get("conversation_id") == _c["id"]:
                            for k in ("chat", "plan", "recs", "conversation_id",
                                      "result", "result_pdf", "result_image"):
                                ss.pop(k, None)
                        st.rerun()
                    except Exception as _e:
                        st.error(f"Delete failed: {_e}")
    else:
        st.caption("No saved chats yet. Start chatting below!")

    # ── New chat button — below the history list ──
    st.divider()
    if st.button("✏️  New chat", use_container_width=True, type="primary"):
        # Save the current chat first so it appears in history
        if ss.get("chat") and len(ss.get("chat", [])) > 1:
            try:
                save_conversation(
                    ss.user["id"], ss.chat, ss.plan, ss.conversation_id
                )
            except Exception:
                pass
        # Clear state for a fresh conversation
        for k in (
            "chat", "plan", "recs", "result", "selected_model",
            "conversation_id", "race_ids", "race_results",
            "sources", "sources_text", "feedback_given",
            "result_pdf", "result_image", "pending_user_prompt",
            "image_note", "uploaded_image_name",
            "work_mode", "attachments", "_processed_upload_ids",
            "run_pending", "race_elapsed",
        ):
            ss.pop(k, None)
        st.rerun()

    st.divider()

    # ── Priority slider ──
    if mode:
        st.markdown(f"#### {mode['icon']} {mode['title']}")
        st.caption(mode["benefit"])
        st.divider()

    st.markdown("#### Recommendation priority")
    priority = st.slider(
        "Cheapest ← → Best quality",
        min_value=0.0, max_value=1.0,
        value=float(ss.priority), step=0.05,
        help="0 favours cheap / low-token models. 1 favours higher task-fit quality.",
        key="priority_slider",
    )
    ss.priority = priority
    l, r = st.columns(2)
    l.caption("Cost"); r.caption("Quality")
    st.progress(priority)

    st.divider()

    if st.button("Back to Dashboard", use_container_width=True):
        st.switch_page("pages/dashboard.py")


# ── helpers ───────────────────────────────────────────────────────────────────
def _has_images() -> bool:
    return any(a.get("is_image") for a in ss.get("attachments") or [])


def _recommend_for(plan):
    try:
        adj = get_fit_adjustments()
    except Exception:
        adj = {}
    return scoring.recommend(
        plan,
        runner.available_api_ids(),
        priority=ss.priority,
        adjustments=adj,
        prefer_vision=_has_images(),
    )


def _add_attachment(data: bytes, name: str, kind: str) -> dict | None:
    """Process and store one upload. Returns the attachment dict."""
    with st.spinner(f"Reading {name}…"):
        att = process_upload(data, name, kind=kind)
    # deduplicate by name
    ss.attachments = [a for a in ss.attachments if a.get("name") != att["name"]]
    ss.attachments.append(att)
    return att


def _display_attachment_strip():
    """Compact thumbnail row shown above the input — images at fixed 80 px."""
    if not ss.attachments:
        return
    # Use HTML to pin image thumbnails to a small fixed size
    thumb_html_parts = []
    doc_parts = []
    for i, a in enumerate(ss.attachments):
        if a.get("data_url") and str(a["data_url"]).startswith("data:image"):
            thumb_html_parts.append(
                f'<img src="{a["data_url"]}" '
                f'style="width:80px;height:80px;object-fit:cover;'
                f'border-radius:6px;margin:2px;" '
                f'title="{a.get("name","image")}" />'
            )
        else:
            doc_parts.append(a.get("name", "file"))

    if thumb_html_parts:
        st.markdown(
            '<div style="display:flex;flex-wrap:wrap;gap:4px;margin-bottom:4px;">'
            + "".join(thumb_html_parts)
            + "</div>",
            unsafe_allow_html=True,
        )
    if doc_parts:
        st.caption("📄 " + "  ·  ".join(doc_parts))

    # Remove buttons in a separate compact row
    if len(ss.attachments) <= 6:
        rm_cols = st.columns(len(ss.attachments))
        for i, (col, a) in enumerate(zip(rm_cols, list(ss.attachments))):
            with col:
                if st.button(f"✕ {a.get('name','file')[:12]}", key=f"rm_att_{i}",
                             use_container_width=True):
                    ss.attachments.pop(i)
                    ss._processed_upload_ids.discard(
                        f"{a.get('name')}:{a.get('id','')}"
                    )
                    st.rerun()
    else:
        if st.button("Clear all attachments", key="rm_all"):
            ss.attachments.clear()
            ss._processed_upload_ids.clear()
            st.rerun()


# ── direct vision chat → routes to run_task for full result display ───────────
def _vision_turn(user_text: str):
    """Send user question + attachments to vision model, then show result in run_task."""
    import time
    from core.model_registry import MODELS

    ss.chat.append({"role": "user", "content": user_text})

    with st.spinner("Thinking…"):
        try:
            t0 = time.time()
            reply = direct_chat_with_attachments(
                question=user_text,
                attachments=ss.attachments,
                history=ss.chat[:-1],
            )
            elapsed = round(time.time() - t0, 2)
        except Exception as e:
            ss.chat.pop()
            st.error(f"Vision model error: {e}")
            st.stop()

    ss.chat.append({"role": "assistant", "content": reply})
    try:
        ss.conversation_id = save_conversation(
            ss.user["id"], ss.chat, ss.plan, ss.conversation_id
        )
    except Exception:
        pass

    # Package reply as a result so run_task can display it with downloads
    in_tok = max(1, len(user_text) // 4)
    out_tok = max(1, len(reply) // 4)
    ss.result = {
        "text": reply,
        "input_tokens": in_tok,
        "output_tokens": out_tok,
        "seconds": elapsed,
    }
    # Build a minimal plan so run_task knows what to render
    if not ss.get("plan"):
        ss.plan = {
            "ready": True,
            "reply": "",
            "task_type": "image_analysis" if _has_images() else "document_analysis",
            "output_format": "text",
            "complexity": 3,
            "est_input_tokens": in_tok,
            "est_output_tokens": out_tok,
            "needs_web": False,
            "search_query": "",
            "task_prompt": user_text,
        }
    # Pick the vision model as selected_model for run_task header
    from core.media import VISION_MODEL
    vision_key = next(
        (k for k, m in MODELS.items() if m.get("api_id") == VISION_MODEL),
        next(iter(MODELS)),  # fallback to first model
    )
    ss.selected_model = vision_key
    ss.run_pending = False   # result already computed, skip re-running
    ss.result_pdf = None     # will be auto-built in run_task
    ss.result_image = None
    ss.feedback_given = False
    ss.sources_text = ""
    st.switch_page("pages/run_task.py")


# ── advisor planning chat (no attachments) ────────────────────────────────────
def _advisor_turn(user_text: str):
    content = user_text.strip() or "Help me."
    ss.chat.append({"role": "user", "content": content})

    with st.spinner("Thinking…"):
        try:
            plan = advisor.analyze(ss.chat, work_mode=ss.get("work_mode"))
        except Exception as e:
            ss.chat.pop()
            st.error(f"Advisor error: {e}")
            st.stop()

    ss.chat.append({"role": "assistant", "content": plan["reply"] or "Got it."})
    if plan["ready"]:
        ss.plan = plan
        ss.recs = _recommend_for(plan)
    else:
        ss.plan, ss.recs = None, []
    try:
        ss.conversation_id = save_conversation(
            ss.user["id"], ss.chat, ss.plan, ss.conversation_id
        )
    except Exception:
        pass


# ── welcome message ───────────────────────────────────────────────────────────
if not ss.chat:
    ss.chat.append({
        "role": "assistant",
        "content": (
            mode["welcome"] if mode else
            "Hi! Upload an image or file using the 📎 button below, then ask me anything about it."
        ),
    })

# ── render chat history ───────────────────────────────────────────────────────
for m in ss.chat:
    st.chat_message(m["role"]).write(m["content"])

# ── attachment thumbnail strip ────────────────────────────────────────────────
_display_attachment_strip()

# ── file uploader (auto-processes files as soon as they are selected) ─────────
with st.expander("📎 Attach files or images", expanded=not bool(ss.attachments)):
    uploaded_files = st.file_uploader(
        "Images (png/jpg/webp/gif) · Documents (pdf/txt/md/csv/json/docx/py/log)",
        type=["png", "jpg", "jpeg", "webp", "gif",
              "pdf", "txt", "md", "csv", "json", "docx", "py", "log"],
        accept_multiple_files=True,
        key="unified_uploader",
        label_visibility="collapsed",
    )

    # Auto-process any file not yet seen this session
    if uploaded_files:
        newly_added = []
        for f in uploaded_files:
            uid = f"{f.name}:{f.size}"
            if uid not in ss._processed_upload_ids:
                ext = f.name.rsplit(".", 1)[-1].lower() if "." in f.name else ""
                kind = "photo" if ext in {"png", "jpg", "jpeg", "webp", "gif"} else "file"
                att = _add_attachment(f.getvalue(), f.name, kind)
                ss._processed_upload_ids.add(uid)
                newly_added.append(f.name)
        if newly_added:
            st.rerun()   # refresh to show thumbnails immediately

    # Camera
    cam_col1, cam_col2 = st.columns([1, 1])
    with cam_col1:
        if not ss.get("camera_active"):
            if st.button("📷 Camera", key="btn_open_cam", use_container_width=True):
                ss["camera_active"] = True
                st.rerun()
        else:
            if st.button("✕ Close camera", key="btn_close_cam", use_container_width=True):
                ss["camera_active"] = False
                st.rerun()

    if ss.get("camera_active"):
        shot = st.camera_input("Take a photo", key="cam_input")
        if shot is not None:
            if st.button("Use this photo", key="btn_use_cam"):
                _add_attachment(shot.getvalue(), "camera.jpg", "camera")
                ss["camera_active"] = False
                st.rerun()

# ── chat input ────────────────────────────────────────────────────────────────
prompt = st.chat_input("Ask me anything… (or just send a message)")
if prompt:
    if ss.attachments:
        # Images or docs attached → answer directly via vision model
        _vision_turn(prompt)
    else:
        # No attachments → advisor planning flow
        _advisor_turn(prompt)
    st.rerun()

# ── model recommendations (only shown after advisor planning, no attachments) ─
if ss.plan and ss.recs and not ss.attachments:
    plan = ss.plan
    st.divider()
    st.subheader("Top recommended models")
    st.caption(
        f"Task: **{plan['task_type'].replace('_', ' ').title()}** · "
        f"Output: **{plan['output_format'].upper()}** · "
        f"Complexity: **{plan['complexity']}/5**"
        + (" · web search" if plan["needs_web"] else "")
        + f" · Priority: **{int(ss.priority * 100)}% quality**"
    )

    cols = st.columns(len(ss.recs))
    for i, (col, rec) in enumerate(zip(cols, ss.recs)):
        with col:
            with st.container(border=True):
                vision_tag = " · Vision" if rec["model"].get("vision") else ""
                st.markdown(f"### {'🥇' if i == 0 else '🥈'} {rec['label']}{vision_tag}")
                st.metric("Suitability", f"{rec['score']}/100")
                st.progress(min(1.0, rec["score"] / 100))
                st.write(rec["reason"])
                st.caption(
                    f"~{rec['in_tokens']:,} in + ~{rec['out_tokens']:,} out "
                    f"· ≈ ${rec['cost']:.5f}"
                )
                if st.button(
                    f"Use {rec['label']}",
                    key=f"pick_{rec['id']}",
                    type="primary" if i == 0 else "secondary",
                    use_container_width=True,
                ):
                    ss.selected_model = rec["id"]
                    ss.pop("race_ids", None)
                    ss.pop("race_results", None)
                    ss.run_pending = True
                    ss.result = None
                    ss.result_pdf = None
                    ss.result_image = None
                    ss.feedback_given = False
                    st.switch_page("pages/run_task.py")

    if len(ss.recs) >= 2:
        if st.button("Race both models", type="secondary", use_container_width=True):
            ss.race_ids = [r["id"] for r in ss.recs]
            ss.selected_model = ss.recs[0]["id"]
            ss.run_pending = True
            ss.result = None
            ss.result_pdf = None
            ss.result_image = None
            ss.race_results = None
            ss.feedback_given = False
            st.switch_page("pages/run_task.py")

    with st.expander("Token analysis"):
        tk = st.selectbox("Tokenizer", list(TOKENIZER_MODELS))
        if st.button("Analyse tokens"):
            with st.spinner("Loading tokenizer…"):
                t = tokenize_text(plan["task_prompt"], tk)
            c1, c2, c3 = st.columns(3)
            c1.metric("Characters", t["characters"])
            c2.metric("Words", t["words"])
            c3.metric("Tokens", t["token_count"])
            st.write(t["tokens"])
