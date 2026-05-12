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

# Display conversation history
for msg in st.session_state.messages:
    with st.chat_message(msg["role"], avatar="🌸" if msg["role"] == "assistant" else "👤"):
        st.markdown(msg["content"])
        if msg.get("logged_entries"):
            with st.expander("📋 Logged entries", expanded=False):
                for e in msg["logged_entries"]:
                    badge = section_badge(e.get("section", "")) if e.get("section") else ""
                    item_desc = e.get("item_name") or e.get("source_option_text", "")[:60]
                    qty = e.get("consumed_qty_text", "")
                    st.markdown(
                        f"{badge} **{item_desc}** {qty} "
                        f'<span style="color:#999;font-size:0.8em">#{e.get("event_id","")}</span>',
                        unsafe_allow_html=True,
                    )
        if msg.get("warnings"):
            for w in msg["warnings"]:
                st.warning(w)
        if msg.get("confirmation_requests"):
            st.info("⚠️ The assistant needs clarification — see the response above.")

# Chat input
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
                    result = {"assistant_text": response_text, "logged_entries": [], "warnings": [], "confirmation_requests": []}
                else:
                    result = api.send_message(
                        user_input,
                        session_id=st.session_state.session_id,
                    )
                    response_text = result.get("assistant_text", "I'm not sure what happened. Please try again.")
            except Exception as exc:
                response_text = f"Oops! Something went wrong: {exc} 😔"
                result = {"assistant_text": response_text, "logged_entries": [], "warnings": [], "confirmation_requests": []}

        st.markdown(response_text)

        logged = result.get("logged_entries", [])
        warnings = result.get("warnings", [])

        if logged:
            with st.expander(f"📋 {len(logged)} item(s) logged", expanded=True):
                for e in logged:
                    badge = section_badge(e.get("section", "")) if e.get("section") else ""
                    item_desc = e.get("item_name") or (e.get("source_option_text") or "")[:60]
                    qty = e.get("consumed_qty_text", "")
                    st.markdown(
                        f"{badge} **{item_desc}** {qty} "
                        f'<span style="color:#999;font-size:0.8em">#{e.get("event_id","")}</span>',
                        unsafe_allow_html=True,
                    )
        for w in warnings:
            st.warning(w)

    st.session_state.messages.append({
        "role": "assistant",
        "content": response_text,
        "logged_entries": result.get("logged_entries", []),
        "warnings": result.get("warnings", []),
        "confirmation_requests": result.get("confirmation_requests", []),
    })
    st.rerun()
