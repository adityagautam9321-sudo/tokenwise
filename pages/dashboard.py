import streamlit as st

from core.work_modes import WORK_MODES
from ui.theme import hero

ss = st.session_state

hero(
    "Dashboard",
    "TokenWise picks the cheapest capable AI model for your job, runs it, "
    "saves history, and shows what you saved — without burning premium tokens by default.",
    pill="Hub · benefits · start working",
)

st.subheader("Why TokenWise")
b1, b2, b3 = st.columns(3)
with b1, st.container(border=True):
    st.markdown("**Right-sized models**")
    st.caption("Advisor + scoring recommend the best-value Groq model, not always the biggest.")
with b2, st.container(border=True):
    st.markdown("**Race & learn**")
    st.caption("Compare top picks side-by-side and rate results so recommendations improve.")
with b3, st.container(border=True):
    st.markdown("**History & savings**")
    st.caption("Chats and runs stay in your account. Cost savings live under History.")

st.divider()
st.subheader("Choose how you want to work")
st.caption("Pick a mode to open the Assistant with the right setup. Or talk freely below.")

modes = list(WORK_MODES.items())
# 3 + 2 layout
row1, row2 = modes[:3], modes[3:]

def _mode_card(key: str, mode: dict, btn_key: str):
    with st.container(border=True):
        st.markdown(f"### {mode['icon']} {mode['title']}")
        st.write(mode["blurb"])
        st.caption(mode["benefit"])
        if st.button(f"Start · {mode['title']}", key=btn_key, use_container_width=True, type="primary"):
            for k in (
                "chat", "plan", "recs", "result", "selected_model", "conversation_id",
                "race_ids", "race_results", "sources_text", "feedback_given", "result_pdf",
            ):
                ss.pop(k, None)
            ss.work_mode = key
            ss.chat = [{"role": "assistant", "content": mode["welcome"]}]
            ss.plan = None
            ss.recs = []
            st.switch_page("pages/assistant.py")

cols = st.columns(3)
for (key, mode), col in zip(row1, cols):
    with col:
        _mode_card(key, mode, f"mode_{key}")

cols2 = st.columns(2)
for (key, mode), col in zip(row2, cols2):
    with col:
        _mode_card(key, mode, f"mode_{key}")

st.divider()
st.subheader("Talk to the Assistant")
st.write(
    "Skip the mode picker and describe anything — coding, news, PDFs, images, or recommendations. "
    "If you ask **two or more questions**, TokenWise answers each one separately."
)
c1, c2 = st.columns([3, 1])
with c1:
    direct = st.text_input(
        "Message",
        placeholder="e.g. Explain recursion, and separately: what is Big-O of binary search?",
        label_visibility="collapsed",
        key="dash_direct_msg",
    )
with c2:
    go = st.button("💬 Open chat", use_container_width=True, type="primary")

if go:
    for k in (
        "plan", "recs", "result", "selected_model", "conversation_id",
        "race_ids", "race_results", "sources_text", "feedback_given", "result_pdf",
    ):
        ss.pop(k, None)
    ss.work_mode = None
    if direct and direct.strip():
        ss.chat = []
        ss.pending_user_prompt = direct.strip()
    else:
        ss.chat = []
    st.switch_page("pages/assistant.py")
