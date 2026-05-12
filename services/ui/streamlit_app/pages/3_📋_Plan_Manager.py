"""Plan manager: upload, preview, parse, download template."""
import streamlit as st
import sys, os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from components.style import inject_css, section_badge
from components import api_client as api

st.set_page_config(page_title="Plan Manager 📋 | Diet Assistant", page_icon="📋", layout="wide")
inject_css()

if not st.session_state.get("authenticated"):
    st.warning("Please sign in first.")
    st.stop()

st.markdown("## 📋 Diet Plan Manager")

tab_upload, tab_browse, tab_parsed = st.tabs(["⬆️ Upload Plan", "🔍 Browse Options", "🔬 Parsed Items"])

# ── Upload tab ────────────────────────────────────────────────────────────────
with tab_upload:
    col_up, col_tmpl = st.columns([2, 1])

    with col_up:
        st.markdown("### Upload Your Diet Plan Excel")
        st.markdown(
            "Upload an `.xlsx` file matching the supported format. "
            "Your plan data will never be overwritten — the app only adds tracking sheets."
        )
        uploaded = st.file_uploader("Choose your diet plan (.xlsx)", type=["xlsx"], key="plan_upload")
        if uploaded:
            if st.button("✅ Activate This Plan", use_container_width=True):
                with st.spinner("Validating and activating plan... 🌸"):
                    result = api.upload_plan(uploaded.read(), uploaded.name)
                    sc = result["status_code"]
                    data = result["data"]
                    if sc == 200:
                        st.success("🎉 Plan activated successfully! Ready to track your meals.")
                        st.session_state["show_calorie_goal_form"] = True
                        st.balloons()
                    elif sc == 422:
                        errors = data.get("detail", {}).get("validation_errors", [data])
                        st.error("Validation failed:")
                        for e in errors:
                            st.error(f"• {e}")
                    else:
                        st.error(f"Error {sc}: {data}")

    with col_tmpl:
        st.markdown("### Download Template")
        st.markdown("Need to create your plan from scratch? Download the Excel template:")
        try:
            tmpl_bytes = api.download_template()
            st.download_button(
                "⬇️ Download Template",
                data=tmpl_bytes,
                file_name="diet_plan_template.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
            )
        except Exception as exc:
            st.error(f"Could not load template: {exc}")

    st.markdown("---")

    # ── Calorie goal section ───────────────────────────────────────────────────
    st.markdown("### 🔥 Daily Calorie Goal")

    current_goal = api.get_calorie_goal()

    if current_goal:
        st.info(f"**Current goal:** {current_goal} kcal / day")
    else:
        st.warning("No calorie goal set yet. Set one below so the assistant can track your progress!")

    if st.session_state.get("show_calorie_goal_form", False) or not current_goal:
        with st.form("calorie_goal_form"):
            new_goal = st.number_input(
                "Set your daily calorie intake goal (kcal)",
                min_value=500,
                max_value=10000,
                value=current_goal or 2000,
                step=50,
                help="The assistant will remind you as you approach or reach this limit.",
            )
            submitted = st.form_submit_button("💾 Save Calorie Goal", use_container_width=True)
            if submitted:
                try:
                    api.set_calorie_goal(int(new_goal))
                    st.success(f"✅ Calorie goal set to **{int(new_goal)} kcal/day**!")
                    st.session_state["show_calorie_goal_form"] = False
                    st.rerun()
                except Exception as exc:
                    st.error(f"Failed to save: {exc}")
    else:
        if st.button("✏️ Update Calorie Goal"):
            st.session_state["show_calorie_goal_form"] = True
            st.rerun()

    st.markdown("---")

    # Current plan status
    plan = api.get_plan_info()
    if plan:
        st.markdown("### ✅ Active Plan")
        sections = plan.get("sections", [])
        cols = st.columns(3)
        for i, s in enumerate(sections):
            cols[i % 3].metric(s["section"], f"{s['option_count']} options")
    else:
        st.info("No active plan yet. Upload one above.")

# ── Browse tab ────────────────────────────────────────────────────────────────
with tab_browse:
    plan = api.get_plan_info()
    if not plan:
        st.info("Upload a plan first.")
    else:
        sections = api.get_sections()
        section_names = [s["section"] for s in sections]
        selected_section = st.selectbox("Select section", section_names, key="browse_section")

        if selected_section:
            options = api.get_options(section=selected_section)
            st.markdown(f"**{len(options)} options in {selected_section}**")

            search_q = st.text_input("🔍 Search options", key="option_search")

            for opt in options:
                text = opt.get("option_text", "")
                if search_q and search_q.lower() not in text.lower():
                    continue
                opt_no = opt.get("option_no", "")
                badge = section_badge(opt.get("section", ""))
                with st.expander(f"Option {opt_no}: {text[:60]}{'…' if len(text) > 60 else ''}"):
                    st.markdown(f"{badge} **Option {opt_no}**")
                    st.markdown(f"> {text}")
                    page = opt.get("pdf_page")
                    if page:
                        st.caption(f"PDF page: {page}")
                    detail = api.get_option_detail(opt["section"], opt_no)
                    if detail and detail.get("parsed_items"):
                        st.markdown("**Parsed constituent items:**")
                        for pi in detail["parsed_items"]:
                            conf = pi.get("parser_confidence", 0)
                            conf_color = "#4CAF50" if conf >= 0.7 else "#FF9800" if conf >= 0.4 else "#F44336"
                            st.markdown(
                                f"- {pi.get('item_name_guess', '')} &nbsp; "
                                f"<em>{pi.get('quantity_text', '')}</em> &nbsp; "
                                f'<span style="color:{conf_color};font-size:0.8em">'
                                f"{conf:.0%} confidence</span>",
                                unsafe_allow_html=True,
                            )

# ── Parsed items tab ──────────────────────────────────────────────────────────
with tab_parsed:
    plan = api.get_plan_info()
    if not plan:
        st.info("Upload a plan first.")
    else:
        col_r, col_s = st.columns([1, 3])
        with col_r:
            if st.button("🔄 Re-parse Options", use_container_width=True):
                with st.spinner("Parsing all options..."):
                    result = api.reparse_options()
                    st.success(f"Parsed {result.get('parsed_item_count', 0)} items.")

        items = api.get_parsed_items()
        if items:
            import pandas as pd
            df = pd.DataFrame(items)
            display_cols = [c for c in ["section", "option_no", "item_name_guess", "quantity_text",
                                         "quantity_numeric", "unit_guess", "parser_confidence", "review_status"]
                            if c in df.columns]
            st.dataframe(df[display_cols], use_container_width=True, hide_index=True)
        else:
            st.info("No parsed items yet. Try re-parsing above.")
