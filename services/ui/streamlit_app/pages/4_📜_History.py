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

# Log type filter
log_type_options = ["All", "option", "item", "unregistered", "mixed"]
log_type_filter = st.selectbox("Filter by type", log_type_options, key="hist_log_type")
if log_type_filter != "All":
    events = [e for e in events if e.get("log_type") == log_type_filter]

st.markdown(f"**{len(events)} event(s)**")

if not events:
    st.info("No consumption events found for the selected filters. 🌸")
    st.stop()


def _has_calorie_warning(ev: dict) -> bool:
    notes = ev.get("notes") or ""
    return "CALORIE_WARNING" in notes or "exceeded" in notes.lower()


def _format_calorie_warning(notes: str) -> str:
    """Extract and clean the calorie warning from the notes string."""
    if "CALORIE_WARNING" in notes:
        idx = notes.index("CALORIE_WARNING")
        return notes[idx:].replace("CALORIE_WARNING:", "").replace("CALORIE_WARNING", "").strip()
    return ""


st.markdown("### All Events")

for ev in events:
    eid = ev.get("event_id", "")
    section = ev.get("section") or ""
    badge = section_badge(section) if section else ""
    log_type = ev.get("log_type", "item")
    ts = (ev.get("timestamp_local") or "")[:16]
    status_val = ev.get("status", "confirmed")
    cal = ev.get("estimated_calories")
    notes = ev.get("notes") or ""
    has_warning = _has_calorie_warning(ev)

    status_color = {
        "confirmed": "#4CAF50",
        "needs_review": "#FF9800",
        "corrected": "#2196F3",
        "deleted": "#9E9E9E",
    }.get(status_val, "#9E9E9E")

    if log_type == "option":
        title = f"Option {ev.get('option_no', '')} — {(ev.get('source_option_text') or '')[:50]}"
        type_icon = "🗒️"
    elif log_type == "unregistered":
        original = ""
        if "Original meal:" in notes:
            original = notes.split("Original meal:")[1].split("—")[0].strip()
        display_name = original or ev.get("item_name") or "Unknown meal"
        title = f"⚠️ Unregistered: {display_name[:60]}"
        type_icon = "❓"
    else:
        title = f"{ev.get('item_name', '')} · {ev.get('consumed_qty_text', '')}"
        type_icon = "🍽️"

    cal_str = f" · 🔥 ~{int(cal)} kcal" if cal else ""
    warning_indicator = " 🚨" if has_warning else ""

    with st.expander(f"{type_icon} #{eid} · {ts} · {title}{cal_str}{warning_indicator}"):
        col_info, col_actions = st.columns([3, 1])

        with col_info:
            st.markdown(f"{badge} **{title}**", unsafe_allow_html=True)
            st.markdown(
                f'<span style="background:{status_color};color:white;padding:2px 10px;'
                f'border-radius:10px;font-size:0.8em">{status_val}</span>'
                f'&nbsp;&nbsp;<span style="background:#607D8B;color:white;padding:2px 10px;'
                f'border-radius:10px;font-size:0.8em">{log_type}</span>',
                unsafe_allow_html=True,
            )

            if cal:
                st.markdown(f"🔥 **Estimated calories:** ~{int(cal)} kcal")

            if log_type == "unregistered":
                mapped_to = ev.get("source_option_text") or ev.get("item_name") or ""
                if mapped_to:
                    st.info(f"📌 Mapped to closest plan item: **{mapped_to[:80]}**")
                if "Original meal:" in notes:
                    original_part = notes.split("CALORIE_WARNING")[0].strip() if "CALORIE_WARNING" in notes else notes
                    st.caption(f"📝 {original_part}")

            if has_warning:
                warning_text = _format_calorie_warning(notes)
                if warning_text:
                    st.warning(f"⚠️ **Calorie notice:** {warning_text}")
                else:
                    st.warning("⚠️ This meal exceeded the intended calorie amount.")
            elif notes and log_type != "unregistered":
                if ev.get("confidence"):
                    st.caption(f"Match confidence: {ev['confidence']:.0f}%")
                st.caption(f"Notes: {notes}")
            elif not log_type == "unregistered":
                if ev.get("confidence"):
                    st.caption(f"Match confidence: {ev['confidence']:.0f}%")

        with col_actions:
            st.markdown("**Edit**")

            new_item = st.text_input("Item name", value=ev.get("item_name") or "", key=f"item_{eid}")
            new_qty_text = st.text_input("Quantity text", value=ev.get("consumed_qty_text") or "", key=f"qty_{eid}")
            new_notes = st.text_input("Notes", value=notes, key=f"notes_{eid}")

            btn_col1, btn_col2 = st.columns(2)
            with btn_col1:
                if st.button("💾 Save", key=f"save_{eid}", use_container_width=True):
                    patch = {}
                    if new_item != (ev.get("item_name") or ""):
                        patch["item_name"] = new_item
                    if new_qty_text != (ev.get("consumed_qty_text") or ""):
                        patch["consumed_qty_text"] = new_qty_text
                    if new_notes != notes:
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
