"""Daily dashboard page."""
import streamlit as st
import sys, os
from datetime import date, datetime
import pytz

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from components.style import inject_css, section_badge, bubble_card
from components import api_client as api

st.set_page_config(page_title="Dashboard 📊 | Diet Assistant", page_icon="📊", layout="wide")
inject_css()

if not st.session_state.get("authenticated"):
    st.warning("Please sign in first.")
    st.stop()

# ── Header ──────────────────────────────────────────────────────────────────
st.markdown("## 📊 Today's Dashboard")

tz = pytz.timezone("Asia/Tehran")
today_str = datetime.now(tz).strftime("%Y-%m-%d")
today_label = datetime.now(tz).strftime("%A, %B %d")

col_date, col_btn = st.columns([3, 1])
with col_date:
    selected_date = st.date_input("Select date", value=date.today(), key="dash_date")
    selected_str = selected_date.strftime("%Y-%m-%d")
with col_btn:
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("↻ Refresh", use_container_width=True):
        st.rerun()

# ── Check plan ───────────────────────────────────────────────────────────────
plan_info = api.get_plan_info()
if not plan_info:
    st.info("📋 No diet plan uploaded yet. Visit the **Plan Manager** to upload your Excel plan.")
    st.stop()

# ── Load daily status ────────────────────────────────────────────────────────
try:
    status = api.get_daily_tracking(selected_str)
except Exception as exc:
    st.error(f"Could not load tracking data: {exc}")
    st.stop()

if not status:
    st.info(f"No data for {selected_str}.")
    st.stop()

# ── Summary metrics ──────────────────────────────────────────────────────────
logged_options = status.get("logged_options", [])
logged_items = status.get("logged_items", [])
section_coverage = status.get("section_coverage", {})
all_sections = ["Breakfast", "Lunch", "Dinner", "Snack 1", "Snack 2", "Snack 3"]
covered = len(section_coverage)

st.markdown(f"### ✨ {today_label}" if selected_str == today_str else f"### 📅 {selected_str}")

m1, m2, m3, m4 = st.columns(4)
m1.metric("🍽️ Full Options Logged", len(logged_options))
m2.metric("🥑 Individual Items Logged", len(logged_items))
m3.metric("📋 Sections Covered", f"{covered}/{len(all_sections)}")
m4.metric("📝 Total Entries", len(logged_options) + len(logged_items))

st.markdown("---")

# ── Section coverage ─────────────────────────────────────────────────────────
st.markdown("### 🗂️ Meal Sections")
cols = st.columns(3)
for i, section in enumerate(all_sections):
    col = cols[i % 3]
    with col:
        cov = section_coverage.get(section)
        if cov:
            count = cov.get("options", 0) + cov.get("items", 0)
            st.markdown(
                f"""<div class="bubble-card">
                {section_badge(section)}
                <br><span style="color:#2D2D2D;font-weight:600">{count} log(s) today</span>
                </div>""",
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                f"""<div class="bubble-card" style="opacity:0.55">
                {section_badge(section)}
                <br><span style="color:#999">Not logged yet</span>
                </div>""",
                unsafe_allow_html=True,
            )

st.markdown("---")

# ── Logged options ────────────────────────────────────────────────────────────
if logged_options:
    st.markdown("### 🍱 Logged Plan Options")
    for ev in logged_options:
        section = ev.get("section", "")
        badge = section_badge(section) if section else ""
        opt_no = ev.get("option_no", "")
        text = (ev.get("source_option_text") or "")[:80]
        ts = ev.get("timestamp_local", "")[:16]
        eid = ev.get("event_id", "")
        st.markdown(
            f"""<div class="bubble-card">
            {badge}
            {'<strong>Option ' + str(opt_no) + '</strong> — ' if opt_no else ''}
            {text}
            <br><small style="color:#999">🕐 {ts} &nbsp;|&nbsp; #{eid}</small>
            </div>""",
            unsafe_allow_html=True,
        )

# ── Logged items ──────────────────────────────────────────────────────────────
if logged_items:
    st.markdown("### 🥗 Logged Individual Items")
    for ev in logged_items:
        section = ev.get("section", "")
        badge = section_badge(section) if section else ""
        item = ev.get("item_name", "") or ""
        qty = ev.get("consumed_qty_text", "") or ""
        ts = ev.get("timestamp_local", "")[:16]
        eid = ev.get("event_id", "")
        conf = ev.get("confidence")
        conf_label = f" · {conf:.0f}% match" if conf else ""
        st.markdown(
            f"""<div class="bubble-card">
            {badge}
            <strong>{item}</strong>  <em>{qty}</em>
            <br><small style="color:#999">🕐 {ts} &nbsp;|&nbsp; #{eid}{conf_label}</small>
            </div>""",
            unsafe_allow_html=True,
        )

# ── Status items with remaining ───────────────────────────────────────────────
status_items = [s for s in status.get("status_items", []) if s.get("status_type") == "item" and s.get("remaining_qty_numeric") is not None]
if status_items:
    st.markdown("### 📉 Remaining Amounts (where calculable)")
    for si in status_items:
        item = si.get("item_name", "")
        consumed = si.get("consumed_qty_numeric", 0) or 0
        remaining = si.get("remaining_qty_numeric", 0) or 0
        pct = si.get("completion_pct", 0) or 0
        planned = si.get("planned_qty_text", "")
        col_a, col_b = st.columns([2, 1])
        with col_a:
            st.markdown(f"**{item}**  ·  planned: {planned}")
            st.progress(min(pct / 100, 1.0))
        with col_b:
            if remaining < 0:
                st.error(f"⚠️ Over by {abs(remaining):.1f}")
            else:
                st.success(f"Remaining: {remaining:.1f}")

# ── Download ──────────────────────────────────────────────────────────────────
st.markdown("---")
try:
    wb_bytes = api.download_workbook()
    st.download_button(
        "⬇️ Download Workbook with Tracking",
        data=wb_bytes,
        file_name="diet_plan_tracking.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=False,
    )
except Exception:
    pass
