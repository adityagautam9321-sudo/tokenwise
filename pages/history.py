import streamlit as st

from core.model_registry import MODELS
from core.scoring import savings_vs_baseline
from db.user import (
    delete_conversation,
    delete_request,
    get_conversation,
    get_history,
    list_conversations,
)
from ui.theme import hero, savings_meter

ss = st.session_state
user_id = ss.user["id"]

hero(
    "History",
    "Reopen saved chats, clean up past runs, and review cost savings.",
    pill="Saved in your account",
)

tab_chats, tab_runs, tab_savings = st.tabs(
    ["💬 Chat sessions", "⚙️ Model runs", "💰 Savings"]
)

with tab_chats:
    try:
        chats = list_conversations(user_id)
    except Exception as e:
        st.error(f"Could not load chats: {e}")
        chats = []

    if not chats:
        st.info("No saved chats yet. Talk to the Assistant — chats auto-save.")
    else:
        st.caption(f"{len(chats)} conversation(s)")
        for c in chats:
            with st.container(border=True):
                left, mid, right = st.columns([5, 1.2, 1.2])
                with left:
                    st.markdown(f"**{c['title']}**")
                    task = (c.get("task_type") or "—").replace("_", " ")
                    st.caption(f"{task} · updated {c['updated_at']}")
                with mid:
                    if st.button("Open", key=f"open_{c['id']}", use_container_width=True):
                        try:
                            full = get_conversation(user_id, c["id"])
                        except Exception as e:
                            st.error(f"Load failed: {e}")
                            full = None
                        if full:
                            ss.conversation_id = full["id"]
                            ss.chat = full["messages"]
                            ss.plan = full.get("plan")
                            ss.recs = []
                            ss.result = None
                            ss.pop("race_ids", None)
                            ss.pop("race_results", None)
                            st.switch_page("pages/assistant.py")
                with right:
                    if st.button("Delete", key=f"del_c_{c['id']}", use_container_width=True):
                        try:
                            delete_conversation(user_id, c["id"])
                            if ss.get("conversation_id") == c["id"]:
                                for k in ("chat", "plan", "recs", "conversation_id"):
                                    ss.pop(k, None)
                            st.toast("Chat deleted.")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Delete failed: {e}")

with tab_runs:
    try:
        rows = get_history(user_id, limit=50)
    except Exception as e:
        st.error(f"Could not load runs: {e}")
        rows = []

    if not rows:
        st.info("No model runs logged yet.")
    else:
        for r in rows:
            with st.container(border=True):
                left, right = st.columns([6, 1.2])
                with left:
                    preview = r.get("prompt_preview") or ""
                    st.markdown(
                        f"**{(r.get('task') or 'general').replace('_', ' ').title()}**"
                    )
                    st.caption(
                        f"{r.get('chosen_model')} · "
                        f"{(r.get('input_tokens') or 0) + (r.get('output_tokens') or 0):,} tokens · "
                        f"{r.get('created_at')}"
                    )
                    if preview:
                        st.write(preview)
                with right:
                    if st.button("Delete", key=f"del_r_{r['id']}", use_container_width=True):
                        try:
                            delete_request(user_id, r["id"])
                            st.toast("Run deleted.")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Delete failed: {e}")

with tab_savings:
    st.markdown("#### What you saved vs the most expensive model")
    st.caption(
        "Savings are calculated from your logged runs (and this session’s race/runs). "
        "They are not shown in the chat."
    )

    # Session log first (richest detail)
    session_log = ss.get("savings_log") or []
    # Also derive from DB history
    derived = []
    try:
        hist = get_history(user_id, limit=50)
    except Exception:
        hist = []

    api_to_model = {m["api_id"]: (key, m) for key, m in MODELS.items()}
    for r in hist:
        match = api_to_model.get(r.get("chosen_model"))
        if not match:
            continue
        _key, m = match
        in_tok = int(r.get("input_tokens") or 0)
        out_tok = int(r.get("output_tokens") or 0)
        sv = savings_vs_baseline(m, in_tok, out_tok)
        derived.append({
            "model": m["label"],
            "task": r.get("task"),
            "percent": sv["percent"],
            "saved": sv["saved"],
            "cost": sv["cost"],
            "baseline": sv["baseline"],
            "baseline_cost": sv["baseline_cost"],
            "when": str(r.get("created_at")),
            "in_tok": in_tok,
            "out_tok": out_tok,
        })

    # Prefer session entries when present, else history-derived
    entries = session_log if session_log else derived
    if session_log and derived:
        # Show session on top, then DB without trying to de-dupe perfectly
        entries = list(session_log) + [
            d for d in derived
            if not any(
                abs(d["saved"] - s["saved"]) < 1e-9 and d["model"] == s["model"]
                for s in session_log
            )
        ]

    if not entries:
        st.info("Run a task to see savings here.")
    else:
        total_saved = sum(float(e.get("saved") or 0) for e in entries)
        avg_pct = sum(float(e.get("percent") or 0) for e in entries) / len(entries)
        m1, m2, m3 = st.columns(3)
        m1.metric("Runs tracked", len(entries))
        m2.metric("Total saved (est.)", f"${total_saved:.6f}")
        m3.metric("Avg. cheaper", f"{avg_pct:.0f}%")

        latest = entries[0]
        savings_meter(int(latest.get("percent") or 0), latest.get("baseline") or "flagship")

        for i, e in enumerate(entries[:20]):
            with st.container(border=True):
                st.markdown(
                    f"**{e.get('model')}** · "
                    f"{(e.get('task') or 'task').replace('_', ' ')} · "
                    f"{e.get('when', '')}"
                )
                st.caption(
                    f"{int(e.get('in_tok') or 0) + int(e.get('out_tok') or 0):,} tokens · "
                    f"cost ${float(e.get('cost') or 0):.6f} vs "
                    f"{e.get('baseline')} ${float(e.get('baseline_cost') or 0):.6f}"
                )
                savings_meter(int(e.get("percent") or 0), e.get("baseline") or "flagship")
