"""Chat page — main conversation interface."""
import streamlit as st
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from components.style import inject_css, section_badge
from components import api_client as api

st.set_page_config(page_title="Chat 💬 | Diet Assistant", page_icon="💬", layout="wide")
inject_css()

# Auth guard
if not st.session_state.get("authenticated"):
    st.warning("Please sign in first.")
    st.stop()

st.markdown("## 💬 Chat with your Diet Assistant")
st.markdown("Tell me what you ate, ask about your plan, or request a summary!")

# Init chat history
if "messages" not in st.session_state:
    st.session_state.messages = []
if "session_id" not in st.session_state:
    import uuid
    st.session_state.session_id = str(uuid.uuid4())[:8]

# Sidebar controls
with st.sidebar:
    st.markdown("### 💬 Chat Options")
    if st.button("Clear Chat History", key="clear_chat"):
        st.session_state.messages = []
        st.rerun()
    st.markdown("---")
    st.markdown("**Try saying:**")
    st.markdown("- *I ate breakfast option 3*")
    st.markdown("- *I had one glass of milk and 2 dates*")
    st.markdown("- *What have I eaten today?*")
    st.markdown("- *How much of my plan is left?*")
    st.markdown("- *Undo my last entry*")
    st.markdown("---")
    workbook_ok = api.get_plan_info() is not None
    if workbook_ok:
        st.success("✅ Diet plan active")
        wb_data = api.download_workbook()
        st.download_button(
            "⬇️ Download Workbook",
            data=wb_data,
            file_name="diet_plan_tracking.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
    else:
        st.warning("⚠️ No diet plan uploaded yet")


def _render_reasoning_steps(steps: list) -> None:
    """Render tool call steps in a friendly collapsible panel."""
    if not steps:
        return
    with st.expander(f"🧠 {len(steps)} step(s) taken — click to see", expanded=False):
        for i, step in enumerate(steps, 1):
            icon = step.get("icon", "🔧")
            label = step.get("label", step.get("tool_name", ""))
            args_summary = step.get("args_summary", "")
            result_summary = step.get("result_summary", "")

            # Colour the result row based on content
            is_warning = "⚠️" in result_summary or "Nothing was saved" in result_summary
            is_ok = result_summary.startswith("Saved") or "✅" in result_summary

            st.markdown(
                f"""
<div style="
    border-left: 3px solid {'#FF9800' if is_warning else '#4CAF50' if is_ok else '#607D8B'};
    padding: 6px 12px;
    margin-bottom: 6px;
    border-radius: 0 6px 6px 0;
    background: rgba(0,0,0,0.03);
">
<strong>{i}. {icon} {label}</strong><br>
<span style="color:#666;font-size:0.85em">Input: {args_summary}</span><br>
<span style="color:{'#E65100' if is_warning else '#2E7D32' if is_ok else '#37474F'};font-size:0.85em">Result: {result_summary}</span>
</div>
""",
                unsafe_allow_html=True,
            )


def _render_logged_entries(logged: list) -> None:
    if not logged:
        return
    with st.expander(f"📋 {len(logged)} item(s) logged", expanded=True):
        for e in logged:
            badge = section_badge(e.get("section", "")) if e.get("section") else ""
            item_desc = e.get("item_name") or (e.get("source_option_text") or "")[:60]
            qty = e.get("consumed_qty_text", "")
            cal = e.get("estimated_calories")
            cal_str = f" · 🔥 ~{int(cal)} kcal" if cal else ""
            log_type = e.get("log_type", "")
            unregistered_tag = " ⚠️ *unregistered*" if log_type == "unregistered" else ""
            st.markdown(
                f"{badge} **{item_desc}** {qty}{cal_str}{unregistered_tag} "
                f'<span style="color:#999;font-size:0.8em">#{e.get("event_id","")}</span>',
                unsafe_allow_html=True,
            )


# ── Render conversation history ──────────────────────────────────────────────
for msg in st.session_state.messages:
    with st.chat_message(msg["role"], avatar="🌸" if msg["role"] == "assistant" else "👤"):
        st.markdown(msg["content"])
        if msg.get("reasoning_steps"):
            _render_reasoning_steps(msg["reasoning_steps"])
        if msg.get("logged_entries"):
            _render_logged_entries(msg["logged_entries"])
        for w in msg.get("warnings", []):
            st.warning(w)
        if msg.get("confirmation_requests"):
            st.info("⚠️ The assistant needs clarification — see the response above.")

# ── Chat input ───────────────────────────────────────────────────────────────
user_input = st.chat_input("What did you eat? Ask anything... 🌸")
if user_input:
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user", avatar="👤"):
        st.markdown(user_input)

    with st.chat_message("assistant", avatar="🌸"):
        with st.spinner("Thinking... 🌸"):
            try:
                plan_info = api.get_plan_info()
                if not plan_info:
                    response_text = (
                        "I'd love to help you track your meals, but I need your diet plan first! "
                        "Please go to the **Plan Manager** page and upload your Excel diet plan. 📋"
                    )
                    result = {"assistant_text": response_text, "logged_entries": [], "warnings": [], "reasoning_steps": []}
                else:
                    result = api.send_message(
                        user_input,
                        session_id=st.session_state.session_id,
                    )
                    response_text = result.get("assistant_text", "I'm not sure what happened. Please try again.")
            except Exception as exc:
                response_text = f"Oops! Something went wrong: {exc} 😔"
                result = {"assistant_text": response_text, "logged_entries": [], "warnings": [], "reasoning_steps": []}

        st.markdown(response_text)
        _render_reasoning_steps(result.get("reasoning_steps", []))
        _render_logged_entries(result.get("logged_entries", []))
        for w in result.get("warnings", []):
            st.warning(w)

    st.session_state.messages.append({
        "role": "assistant",
        "content": response_text,
        "reasoning_steps": result.get("reasoning_steps", []),
        "logged_entries": result.get("logged_entries", []),
        "warnings": result.get("warnings", []),
        "confirmation_requests": result.get("confirmation_requests", []),
    })
    st.rerun()
