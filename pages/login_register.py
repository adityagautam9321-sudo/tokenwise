import streamlit as st

from ui.theme import hero

from db.user import authenticate, register_user

hero(
    "TokenWise",
    "Find the cheapest AI model that can do your job well — then run it.",
    pill="Sign in to continue",
)

_, mid, _ = st.columns([1, 2, 1])

with mid:
    tab_login, tab_register = st.tabs(["Login", "Register"])

    with tab_login:
        with st.form("login_form"):
            email = st.text_input("Email")
            password = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Log in", use_container_width=True, type="primary")
        if submitted:
                              
            try:
                user = authenticate(email, password)
            except Exception as e:
                st.error(f"Could not reach the database: {e}")
                st.stop()
            if user:
                st.session_state.user = user
                st.rerun()
            else:
                st.error("Wrong email or password.")
    with tab_register:
        with st.form("register_form"):
            name = st.text_input("Full name")
            r_email = st.text_input("Email", key="reg_email")
            r_pw = st.text_input("Password (min 8 characters)", type="password", key="reg_pw")
            r_pw2 = st.text_input("Confirm password", type="password")
            submitted = st.form_submit_button("Create account", use_container_width=True, type="primary")
        if submitted:
            if r_pw != r_pw2:
                st.error("Passwords do not match.")
            else:
                try:
                    ok, msg = register_user(name, r_email, r_pw)
                except Exception as e:
                    ok, msg = False, f"Could not reach the database: {e}"
                (st.success if ok else st.error)(msg)
