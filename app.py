import streamlit as st
from googleapiclient.discovery import build
from datetime import datetime, timedelta
import isodate
import pandas as pd

# ==========================================
# 🔐 API 키는 Streamlit Cloud의 'Secrets'에서 가져옵니다.
# ==========================================

st.set_page_config(page_title="SIGNAL - YouTube Hunter", layout="wide", page_icon="📡")

# 🌑 [스타일링: Red Killer Ultimate - 모든 상태 강제 오버라이드]
st.markdown("""
<style>
    /* 1. 전체 배경 */
    .stApp { background-color: #0E1117; color: #FAFAFA; }
    
    /* 2. 사이드바 디자인 */
    section[data-testid="stSidebar"] { min-width: 700px !important; }
    [data-testid="stSidebar"] { 
        background-color: #1A1C24; 
        border-right: 1px solid #333; 
        text-align: center; 
    }

    /* 3. 테이블 스타일 */
    th { background-color: #162447 !important; color: white !important; text-align: center !important; }
    td { vertical-align: middle !important; text-align: center !important; font-size: 15px !important; }
    
    /* 4. 링크 스타일 */
    a { text-decoration: none; color: #00E5FF !important; font-weight: bold; }
    a:hover { color: #FFFFFF !important; text-decoration: underline; }
    
    /* 5. 썸네일 이미지 */
    img { border-radius: 6px; }
    
    /* =================================================================
       ⭐ [Red Killer] 버튼 및 입력창 색상 강제 변경 (우선순위 최상)
    ================================================================= */
    
    /* (1) 버튼 & 링크 버튼 (유튜브 보기) */
    /* normal, visited, hover, focus, active 모든 상태 커버 */
    div.stButton > button, 
    a[kind="primary"],
    a[kind="primary"]:visited,
    a[kind="primary"]:focus {
        background: linear-gradient(90deg, #00C6FF 0%, #0072FF 100%) !important;
        color: white !important;
        border: none !important;
        font-weight: bold !important;
        box-shadow: 0 4px 6px rgba(0, 198, 255, 0.3) !important;
        text-decoration: none !important;
        outline: none !important;
    }
    
    div.stButton > button:hover, 
    a[kind="primary"]:hover {
        transform: scale(1.02) !important;
        box-shadow: 0 6px 12px rgba(0, 198, 255, 0.6) !important;
        color: white !important;
    }
    
    div.stButton > button:active,
    a[kind="primary"]:active {
        background: #0072FF !important; /* 클릭 순간 */
        box-shadow: none !important;
    }

    /* (2) Pills, Slider, Checkbox, Radio */
    div[data-testid="stPills"] button[aria-pressed="true"] {
        background-color: #00E5FF !important;
        color: black !important;
        border: 1px solid #00E5FF !important;
    }
    div[data-testid="stSlider"] div[data-baseweb="slider"] div {
        background-color: #00E5FF !important;
    }
    div[role="radiogroup"] > label > div:first-child {
        background-color: #00E5FF !important;
        border-color: #00E5FF !important;
    }
    /* 체크박스 체크 색상 */
    div[data-testid="stCheckbox"] label span[data-baseweb="checkbox"] div {
        background-color: #00E5FF !important;
        border-color: #00E5FF !important;
    }

    /* (3) Expander & Input Focus (검색 옵션 빨간 테두리 제거) */
    .streamlit-expanderHeader {
        color: #00E5FF !important;
    }
    div[data-testid="stExpander"] {
        border-color: rgba(0, 229, 255, 0.3) !important;
    }
    input:focus, textarea:focus, div[data-baseweb="select"] > div:focus-within {
        border-color: #00E5FF !important;
        box-shadow: 0 0 0 1px #00E5FF !important;
    }

    /* 6. 사이드바 로고 박스 */
    .sidebar-logo {
        background: linear-gradient(135deg, #1e3a8a 0%, #00c6ff 100%);
        padding: 12px;
        border-radius: 8px;
        margin-bottom: 20px;
        text-align: center;
        border: 1px solid rgba(255, 255, 255, 0.2);
        box-shadow: 0 4px 15px rgba(0, 198, 255, 0.3);
        width: 90%;
        margin-left: auto;
        margin-right: auto;
    }
    
    /* 7. 메트릭 숫자 색상 */
    [data-testid="stMetricValue"] { font-size: 28px !important; color: #00E5FF !important; font-weight: 700 !important; }
</style>
""", unsafe_allow_html=True)

st.title("📡 SIGNAL : Trend Radar")

# -------------------------------------------------------------------------
# 함수 정의
# -------------------------------------------------------------------------
def parse_duration(d):
    try:
        dur = isodate.parse_duration(d)
        sec = int(dur.total_seconds())
        m, s = divmod(sec, 60)
        h, m = divmod(m, 60)
        return f"{h}:{m:02}:{s:02}" if h else f"{m}:{s:02}"
    except: return d

# -------------------------------------------------------------------------
# 1. 상단 (Top) 검색창
# -------------------------------------------------------------------------
api_key = st.secrets.get("YOUTUBE_API_KEY", None)

with st.expander("🔎 검색 옵션 (펼치기)", expanded=True):
    with st.form(key='search_form'):
        if not api_key:
            api_key = st.text
