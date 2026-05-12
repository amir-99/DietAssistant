"""Consumption history — view, correct, delete."""
import streamlit as st
import sys, os
from datetime import date, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from components.style import inject_css, section_badge
from components import api_client as api

st.set_page_config(page_title="History 📜 | Diet Assistant", page_icon="📜", layout="wide")
inject_css()

if not st.session_state.get("authenticated"):
    st.warning("Please sign in first.")
    st.stop()

plan = api.get_plan_info()
if not plan:
    st.info("📋 No diet plan active. Upload one in the Plan Manager.")
    st.stop()

st.markdown("## 📜 Consumption History")

# Date filter
col_from, col_to = st.columns(2)
with col_from:
    filter_date = st.date_input("Filter by date (leave blank for all)", value=None, key="hist_date")

date_str = filter_date.strftime("%Y-%m-%d") if filter_date else None
events = api.get_events(date=date_str)

# Status filter
status_options = ["All", "confirmed", "needs_review", "corrected"]
status_filter = st.selectbox("Filter by status", status_options, key="hist_status")
if status_filter != "All":
    events = [e for e in events if e.get("status") == status_filter]

st.markdown(f"**{len(events)} event(s)**")

if not events:
    st.info("No consumption events found for the selected filters. 🌸")
    st.stop()

# Editable table view
import pandas as pd

df = pd.DataFrame(events)
display_cols = [c for c in [
    "event_id", "date_local", "timestamp_local", "log_type", "section",
    "option_no", "item_name", "consumed_qty_text", "consumed_qty_numeric",
    "consumed_unit", "confidence", "status", "notes"
] if c in df.columns]

st.markdown("### All Events")

for ev in events:
    eid = ev.get("event_id", "")
    section = ev.get("section") or ""
    badge = section_badge(section) if section else ""
    log_type = ev.get("log_type", "item")
    ts = (ev.get("timestamp_local") or "")[:16]
    status_val = ev.get("status", "confirmed")

    status_color = {
        "confirmed": "#4CAF50",
        "needs_review": "#FF9800",
        "corrected": "#2196F3",
        "deleted": "#9E9E9E",
    }.get(status_val, "#9E9E9E")

    if log_type == "option":
        title = f"Option {ev.get('option_no', '')} — {(ev.get('source_option_text') or '')[:50]}"
    else:
        title = f"{ev.get('item_name', '')} · {ev.get('consumed_qty_text', '')}"

    with st.expander(f"#{eid} · {ts} · {title}"):
        col_info, col_actions = st.columns([3, 1])

        with col_info:
            st.markdown(f"{badge} **{title}**")
            st.markdown(
                f'<span style="background:{status_color};color:white;padding:2px 10px;'
                f'border-radius:10px;font-size:0.8em">{status_val}</span>',
                unsafe_allow_html=True,
            )
            if ev.get("confidence"):
                st.caption(f"Match confidence: {ev['confidence']:.0f}%")
            if ev.get("notes"):
                st.caption(f"Notes: {ev['notes']}")

        with col_actions:
            st.markdown("**Edit**")

            new_item = st.text_input("Item name", value=ev.get("item_name") or "", key=f"item_{eid}")
            new_qty_text = st.text_input("Quantity text", value=ev.get("consumed_qty_text") or "", key=f"qty_{eid}")
            new_notes = st.text_input("Notes", value=ev.get("notes") or "", key=f"notes_{eid}")

            btn_col1, btn_col2 = st.columns(2)
            with btn_col1:
                if st.button("💾 Save", key=f"save_{eid}", use_container_width=True):
                    patch = {}
                    if new_item != (ev.get("item_name") or ""):
                        patch["item_name"] = new_item
                    if new_qty_text != (ev.get("consumed_qty_text") or ""):
                        patch["consumed_qty_text"] = new_qty_text
                    if new_notes != (ev.get("notes") or ""):
                        patch["notes"] = new_notes
                    if patch:
                        try:
                            api.patch_event(eid, patch)
                            st.success("Saved!")
                            st.rerun()
                        except Exception as exc:
                            st.error(f"Error: {exc}")
                    else:
                        st.info("No changes.")

            with btn_col2:
                if st.button("🗑️ Delete", key=f"del_{eid}", use_container_width=True):
                    try:
                        api.delete_event(eid)
                        st.success("Deleted.")
                        st.rerun()
                    except Exception as exc:
                        st.error(f"Error: {exc}")
