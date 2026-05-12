"""Home / login page — the app entry point."""
import os
import streamlit as st
from components.style import inject_css

st.set_page_config(
    page_title="Diet Assistant 🌸",
    page_icon="🌸",
    layout="wide",
    initial_sidebar_state="expanded",
)

inject_css()

APP_PASSWORD = os.environ.get("APP_PASSWORD", "dietassistant")


def check_auth():
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False

    if st.session_state.authenticated:
        return True

    st.markdown(
        """
        <div style="text-align:center;padding:60px 20px 20px">
            <div style="font-size:4rem">🌸</div>
            <h1 style="color:#AD1457;font-size:2.5rem;margin:0">Diet Assistant</h1>
            <p style="color:#880E4F;font-size:1.1rem;margin-top:8px">
                Your personal nutrition companion ✨
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        with st.form("login_form"):
            pwd = st.text_input("Password", type="password", placeholder="Enter your password")
            submitted = st.form_submit_button("Sign In 💕", use_container_width=True)
            if submitted:
                if pwd == APP_PASSWORD:
                    st.session_state.authenticated = True
                    st.rerun()
                else:
                    st.error("Incorrect password. Please try again. 🔒")
    return False


if not check_auth():
    st.stop()

# ── Authenticated home ──────────────────────────────────────────────────────
st.markdown(
    """
    <div style="text-align:center;padding:20px">
        <div style="font-size:3rem">🌸</div>
        <h1 style="color:#AD1457">Welcome back! ✨</h1>
        <p style="color:#880E4F;font-size:1.1rem">
            Your personal diet tracking assistant is ready to help you today.
        </p>
    </div>
    """,
    unsafe_allow_html=True,
)

col1, col2 = st.columns(2)
with col1:
    st.markdown(
        """
        <div class="bubble-card" style="text-align:center">
            <div style="font-size:2.5rem">💬</div>
            <h3 style="color:#AD1457">Chat with Assistant</h3>
            <p>Tell me what you ate in natural language and I'll track it for you.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    if st.button("Open Chat →", key="go_chat", use_container_width=True):
        st.switch_page("pages/1_💬_Chat.py")

with col2:
    st.markdown(
        """
        <div class="bubble-card" style="text-align:center">
            <div style="font-size:2.5rem">📊</div>
            <h3 style="color:#AD1457">Today's Dashboard</h3>
            <p>See what you've logged today and what's remaining in your plan.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    if st.button("Open Dashboard →", key="go_dash", use_container_width=True):
        st.switch_page("pages/2_📊_Dashboard.py")

col3, col4 = st.columns(2)
with col3:
    st.markdown(
        """
        <div class="bubble-card" style="text-align:center">
            <div style="font-size:2.5rem">📋</div>
            <h3 style="color:#AD1457">Plan Manager</h3>
            <p>Upload your diet plan Excel file and browse meal options.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    if st.button("Manage Plan →", key="go_plan", use_container_width=True):
        st.switch_page("pages/3_📋_Plan_Manager.py")

with col4:
    st.markdown(
        """
        <div class="bubble-card" style="text-align:center">
            <div style="font-size:2.5rem">📜</div>
            <h3 style="color:#AD1457">History</h3>
            <p>Review and correct past food logs.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    if st.button("View History →", key="go_hist", use_container_width=True):
        st.switch_page("pages/4_📜_History.py")

# Sidebar
with st.sidebar:
    st.markdown("### 🌸 Diet Assistant")
    st.markdown("---")
    st.markdown("**Quick tips:**")
    st.markdown("- 💬 Chat to log meals")
    st.markdown("- 📊 Dashboard for daily status")
    st.markdown("- 📋 Upload your plan first")
    st.markdown("---")
    if st.button("Sign Out", key="signout"):
        st.session_state.authenticated = False
        st.rerun()
