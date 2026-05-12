GLOBAL_CSS = """
<style>
/* ── Pink bubbly theme ── */
@import url('https://fonts.googleapis.com/css2?family=Nunito:wght@400;600;700;800&display=swap');

html, body, [class*="css"] {
    font-family: 'Nunito', sans-serif !important;
}

/* Main background */
.stApp {
    background: linear-gradient(135deg, #FFF0F5 0%, #FFE4EF 50%, #FFF0F5 100%);
}

/* Sidebar */
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #FCB8D4 0%, #F78FB3 100%) !important;
}
[data-testid="stSidebar"] * {
    color: #3D1A2B !important;
}

/* Cards / containers */
[data-testid="stVerticalBlock"] > div {
    border-radius: 16px;
}

/* Metric cards */
[data-testid="stMetric"] {
    background: rgba(255,255,255,0.75);
    border: 2px solid #F48FB1;
    border-radius: 20px;
    padding: 16px;
    box-shadow: 0 4px 12px rgba(233,30,140,0.08);
}

/* Chat messages */
[data-testid="stChatMessage"] {
    border-radius: 20px !important;
    margin-bottom: 8px;
    box-shadow: 0 2px 8px rgba(0,0,0,0.06);
}

/* Buttons */
.stButton > button {
    background: linear-gradient(135deg, #E91E8C, #FF6EC7) !important;
    color: white !important;
    border: none !important;
    border-radius: 25px !important;
    padding: 0.5rem 1.5rem !important;
    font-weight: 700 !important;
    box-shadow: 0 4px 12px rgba(233,30,140,0.3) !important;
    transition: transform 0.15s ease, box-shadow 0.15s ease !important;
}
.stButton > button:hover {
    transform: translateY(-2px) !important;
    box-shadow: 0 6px 20px rgba(233,30,140,0.4) !important;
}

/* Download button */
[data-testid="stDownloadButton"] > button {
    background: linear-gradient(135deg, #9C27B0, #E040FB) !important;
    color: white !important;
    border-radius: 25px !important;
    border: none !important;
    font-weight: 700 !important;
}

/* File uploader */
[data-testid="stFileUploader"] {
    background: rgba(255,255,255,0.6) !important;
    border: 2px dashed #F48FB1 !important;
    border-radius: 20px !important;
}

/* Input fields */
.stTextInput > div > div > input,
.stTextArea > div > div > textarea {
    border-radius: 16px !important;
    border: 2px solid #F8BBD9 !important;
    background: rgba(255,255,255,0.8) !important;
}
.stTextInput > div > div > input:focus,
.stTextArea > div > div > textarea:focus {
    border-color: #E91E8C !important;
    box-shadow: 0 0 0 2px rgba(233,30,140,0.15) !important;
}

/* Select boxes */
.stSelectbox > div > div {
    border-radius: 16px !important;
    border: 2px solid #F8BBD9 !important;
}

/* Expanders */
[data-testid="stExpander"] {
    border: 2px solid #F8BBD9 !important;
    border-radius: 16px !important;
    background: rgba(255,255,255,0.6) !important;
}

/* Progress bars */
.stProgress > div > div > div {
    background: linear-gradient(90deg, #E91E8C, #FF6EC7) !important;
    border-radius: 10px !important;
}

/* Tabs */
.stTabs [data-baseweb="tab-list"] {
    gap: 8px;
}
.stTabs [data-baseweb="tab"] {
    border-radius: 20px 20px 0 0 !important;
    background: rgba(255,255,255,0.5) !important;
}
.stTabs [aria-selected="true"] {
    background: linear-gradient(135deg, #E91E8C, #FF6EC7) !important;
    color: white !important;
}

/* Section headers */
h1 { color: #AD1457 !important; }
h2 { color: #C2185B !important; }
h3 { color: #D81B60 !important; }

/* Data editor */
[data-testid="stDataFrame"] {
    border-radius: 16px !important;
    border: 2px solid #F8BBD9 !important;
    overflow: hidden;
}

/* Success / info / warning banners */
.stSuccess {
    background: rgba(200,230,201,0.8) !important;
    border-radius: 16px !important;
    border: 1px solid #4CAF50 !important;
}
.stInfo {
    background: rgba(225,190,231,0.5) !important;
    border-radius: 16px !important;
    border: 1px solid #CE93D8 !important;
}
.stWarning {
    background: rgba(255,236,179,0.8) !important;
    border-radius: 16px !important;
}
.stError {
    background: rgba(255,205,210,0.8) !important;
    border-radius: 16px !important;
}

/* Bubble card helper */
.bubble-card {
    background: rgba(255,255,255,0.8);
    border: 2px solid #F8BBD9;
    border-radius: 20px;
    padding: 16px 20px;
    margin: 8px 0;
    box-shadow: 0 4px 12px rgba(233,30,140,0.08);
}

/* Scrollbar */
::-webkit-scrollbar { width: 8px; }
::-webkit-scrollbar-track { background: #FFF0F5; }
::-webkit-scrollbar-thumb { background: #F48FB1; border-radius: 10px; }
</style>
"""


def inject_css():
    import streamlit as st
    st.markdown(GLOBAL_CSS, unsafe_allow_html=True)


def bubble_card(content: str):
    import streamlit as st
    st.markdown(f'<div class="bubble-card">{content}</div>', unsafe_allow_html=True)


def section_badge(section: str) -> str:
    colors = {
        "Breakfast": "#FF8A65",
        "Lunch": "#66BB6A",
        "Dinner": "#42A5F5",
        "Snack 1": "#AB47BC",
        "Snack 2": "#FF7043",
        "Snack 3": "#26C6DA",
    }
    color = colors.get(section, "#E91E8C")
    return (
        f'<span style="background:{color};color:white;padding:3px 12px;'
        f'border-radius:12px;font-size:0.8em;font-weight:700">{section}</span>'
    )
