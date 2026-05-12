"""Settings page."""
import streamlit as st
import sys, os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from components.style import inject_css
from components import api_client as api

st.set_page_config(page_title="Settings ⚙️ | Diet Assistant", page_icon="⚙️", layout="wide")
inject_css()

if not st.session_state.get("authenticated"):
    st.warning("Please sign in first.")
    st.stop()

st.markdown("## ⚙️ Settings")

col1, col2 = st.columns(2)

with col1:
    st.markdown("### 🕐 Time & Region")
    st.markdown("""
    <div class="bubble-card">
    <b>Timezone:</b> Configured via <code>TZ</code> environment variable on the server.<br>
    Default: <code>Asia/Tehran</code>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("### 🤖 LLM Provider")
    st.markdown("""
    <div class="bubble-card">
    The AI provider is configured via environment variables on the server:
    <ul>
        <li><code>LLM_PROVIDER</code> — <code>anthropic</code> or <code>openai</code></li>
        <li><code>LLM_MODEL</code> — model name (e.g. <code>claude-sonnet-4-6</code>)</li>
        <li><code>ANTHROPIC_API_KEY</code> or <code>OPENAI_API_KEY</code></li>
    </ul>
    Edit the <code>.env</code> file on your server and restart the stack to change these.
    </div>
    """, unsafe_allow_html=True)

with col2:
    st.markdown("### 🎯 Matching Thresholds")
    st.markdown("""
    <div class="bubble-card">
    <b>Auto-log threshold:</b> ≥ 90% confidence — items are logged automatically.<br><br>
    <b>Confirmation threshold:</b> 70–89% confidence — assistant asks before logging.<br><br>
    <b>Below 70%:</b> Treated as unmatched; assistant asks for clarification.<br><br>
    Configure via <code>MATCH_CONFIDENCE_AUTO</code> and <code>MATCH_CONFIDENCE_CONFIRM</code>
    environment variables.
    </div>
    """, unsafe_allow_html=True)

    st.markdown("### 🔒 Security")
    st.markdown("""
    <div class="bubble-card">
    App password is set via the <code>APP_PASSWORD</code> environment variable.<br>
    Edit your <code>.env</code> file and restart to change it.
    </div>
    """, unsafe_allow_html=True)

st.markdown("---")
st.markdown("### 🏥 System Status")
try:
    health = api.health()
    st.success(f"✅ API: {health.get('status', 'ok')}")
except Exception as exc:
    st.error(f"❌ API unavailable: {exc}")

try:
    plan = api.get_plan_info()
    if plan:
        total = plan.get("total_options", 0)
        sections = len(plan.get("sections", []))
        st.success(f"✅ Diet plan active: {sections} sections, {total} options")
    else:
        st.warning("⚠️ No diet plan uploaded yet")
except Exception as exc:
    st.warning(f"⚠️ Plan status unknown: {exc}")

st.markdown("---")
st.markdown("### 📦 About")
st.markdown("""
<div class="bubble-card">
<b>Diet Tracking Assistant v1.0</b><br>
A personal, self-hosted nutrition tracking app powered by AI. 🌸<br><br>
<b>Stack:</b> FastAPI · PydanticAI · Streamlit · OpenPyXL · Caddy · Docker Compose
</div>
""", unsafe_allow_html=True)

if st.button("🚪 Sign Out", key="settings_signout"):
    st.session_state.authenticated = False
    st.rerun()
