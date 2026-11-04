"""TokenWise entry point: login gate + page router.  Run: streamlit run app.py"""
import streamlit as st

from ui.theme import inject

st.set_page_config(page_title="TokenWise", page_icon="🤖", layout="wide")
inject()

# Ensure Phase 4 tables exist (safe no-op if already created).
try:
    from db.migrate import ensure_schema
    ensure_schema()
except Exception:
    pass

user = st.session_state.get("user")

if user:
    pages = [
        st.Page("pages/dashboard.py", title="Dashboard", icon="📊", default=True),
        st.Page("pages/assistant.py", title="Assistant", icon="💬"),
        st.Page("pages/run_task.py", title="Run Task", icon="⚙️"),
        st.Page("pages/history.py", title="History", icon="🕘"),
    ]
    with st.sidebar:
        st.markdown("### TokenWise")
        st.write(f"👤 **{user['name']}**")
        st.caption(user["email"])
        st.divider()
        if st.button("Log out", use_container_width=True):
            st.session_state.clear()
            st.rerun()
else:
    pages = [st.Page("pages/login_register.py", title="Login", icon="🔐")]

st.navigation(pages).run()
