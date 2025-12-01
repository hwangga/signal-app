import streamlit as st
from googleapiclient.discovery import build
from datetime import datetime, timedelta
import isodate
import pandas as pd

# ==========================================
# 🔐 API 키는 Streamlit Cloud의 'Secrets'에서 가져옵니다.
# ==========================================

st.set_page_config(page_title="SIGNAL - YouTube Hunter", layout="wide", page_icon="📡")

# 🌑 [스타일링: Red Killer V6 - Expander & Logo Color Fix]
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
    a { text-decoration: none; color: #00E5FF; font-weight: bold; }
    a:hover { color: #FFFFFF; text-decoration: underline; }
    
    /* 5. 썸네일 이미지 */
    img { border-radius: 6px; }
    
    /* =================================================================
       ⭐ [Red Killer] 빨간색 요소 박멸 (Expander 추가)
    ================================================================= */
    
    /* (1) 버튼 */
    div.stButton > button, 
    a[kind="primary"] {
        background: linear-gradient(90deg, #00C6FF 0%, #0072FF 100%) !important;
        color: white !important;
        border: none !important;
        font-weight: bold !important;
        box-shadow: 0 4px 6px rgba(0, 198, 255, 0.3) !important;
    }
    div.stButton > button:hover, 
    a[kind="primary"]:hover {
        transform: scale(1.02) !important;
        box-shadow: 0 6px 12px rgba(0, 198, 255, 0.5) !important;
        color: white !important;
    }

    /* (2) Pills, Slider, Checkbox */
    div[data-testid="stPills"] button[aria-pressed="true"] {
        background-color: #00E5FF !important;
        color: #000000 !important;
        border: 1px solid #00E5FF !important;
        font-weight: bold !important;
    }
    div[data-testid="stSlider"] div[data-baseweb="slider"] div {
        background-color: #00E5FF !important;
    }
    div[role="radiogroup"] > label > div:first-child {
        background-color: #00E5FF !important;
        border-color: #00E5FF !important;
    }

    /* (3) ⭐ [추가] Expander (검색 옵션 박스) 빨간색 제거 */
    .streamlit-expanderHeader {
        color: #00E5FF !important; /* 헤더 글씨 민트색 */
        font-weight: bold !important;
    }
    .streamlit-expanderContent {
        border-color: #30475e !important;
    }
    /* 선택된 입력창 테두리 색상 */
    input:focus, div[data-baseweb="select"] > div:focus-within {
        border-color: #00E5FF !important;
    }

    /* ================================================================= */

   /* 사이드바 로고 박스 */
    .sidebar-logo {
        background: linear-gradient(135deg, #1e3a8a 0%, #00c6ff 100%) !important;
        padding: 12px;
        border-radius: 8px;
        margin-bottom: 20px;
        text-align: center;
        
        /* 👇 [여기!] 이 줄을 찾아서 아래처럼 바꾸세요 */
        border: 2px solid #00E5FF !important;  /* 민트색 진한 테두리 */
        
        box-shadow: 0 4px 15px rgba(0, 198, 255, 0.3);
        width: 90%;
        margin-left: auto;
        margin-right: auto;
    }
    
    /* 7. 메트릭 숫자 색상 */
    [data-testid="stMetricValue"] { font-size: 28px !important; color: #00E5FF !important; font-weight: 700 !important; }
</style>
""", unsafe_allow_html=True)

st.title("📡 SIGNAL : YouTube Hunter")

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
            api_key = st.text_input("API 키 입력 (로컬 테스트용)", type="password")

        c1, c2, c3, c4 = st.columns([2, 1, 1, 1])
        with c1: query = st.text_input("키워드", "")
        with c2: max_results = st.selectbox("수집수", [10, 30, 50, 100], index=1)
        with c3: days_filter = st.selectbox("기간", ["1주일", "1개월", "3개월", "전체"], index=1)
        with c4: 
            st.caption("국가 (복수선택)")
            country_options = st.pills("국가", ["🇰🇷", "🇯🇵", "🇺🇸", "🌏"], default=["🇰🇷"], selection_mode="multi", label_visibility="collapsed")
            
        c5, c6, c7 = st.columns([1, 2, 2])
        with c5: 
            st.caption("길이")
            video_durations = st.pills("길이", ["쇼츠", "롱폼"], default=["쇼츠"], selection_mode="multi", label_visibility="collapsed")
        with c6: 
            st.caption("등급 필터")
            filter_grade = st.pills("등급", 
                                    ["🚀 떡상중", "📈 급상승", "👀 주목", "💤 일반"], 
                                    default=["🚀 떡상중", "📈 급상승", "👀 주목"],
                                    selection_mode="multi", label_visibility="collapsed")
        with c7: 
            st.caption("구독자 범위")
            subs_range = st.slider("구독자", 0, 1000000, (0, 1000000), 1000, label_visibility="collapsed")

        st.markdown("<br>", unsafe_allow_html=True)
        search_trigger = st.form_submit_button("🚀 SIGNAL 감지 시작", type="primary", use_container_width=True)

# -------------------------------------------------------------------------
# 2. 로직
# -------------------------------------------------------------------------
if 'df_result' not in st.session_state: st.session_state.df_result = None

today = datetime.now()
if days_filter == "1주일": published_after = (today - timedelta(days=7)).isoformat("T") + "Z"
elif days_filter == "1개월": published_after = (today - timedelta(days=30)).isoformat("T") + "Z"
elif days_filter == "3개월": published_after = (today - timedelta(days=90)).isoformat("T") + "Z"
else: published_after = None

api_duration = "any"
if len(video_durations) == 1:
    if "쇼츠" in video_durations: api_duration = "short"
    elif "롱폼" in video_durations: api_duration = "long"

region_map = {"🇰🇷": "KR", "🇯🇵": "JP", "🇺🇸": "US", "🌏": None}

if search_trigger:
    if not query:
        st.warning("⚠️ 키워드를 입력해주세요!")
    elif not api_key:
        st.error("🔑 API 키가 설정되지 않았습니다.")
    else:
        try:
            youtube = build('youtube', 'v3', developerKey=api_key)
            all_video_ids = []
            
            with st.spinner(f"📡 '{query}' 신호 분석 중..."):
                target_countries = [region_map[c] for c in country_options] if country_options else [None]
                
                for region_code in target_countries:
                    per_country_max = max(10, int(max_results / len(target_countries))) if target_countries else max_results
                    
                    search_request = youtube.search().list(
                        part="snippet", q=query, maxResults=per_country_max, order="viewCount", type="video", 
                        videoDuration=api_duration, publishedAfter=published_after, regionCode=region_code
                    )
                    search_response = search_request.execute()
                    all_video_ids.extend([item['id']['videoId'] for item in search_response['items']])

                all_video_ids = list(set(all_video_ids))

                if not all_video_ids: 
                    st.error("신호 없음 (검색 결과 0건)")
                    st.session_state.df_result = pd.DataFrame()
                else:
                    chunks = [all_video_ids[i:i + 50] for i in range(0, len(all_video_ids), 50)]
                    items = []
                    for chunk in chunks:
                        video_request = youtube.videos().list(part="statistics, snippet, contentDetails", id=','.join(chunk))
                        video_response = video_request.execute()
                        items.extend(video_response['items'])

                    channel_ids = list(set([item['snippet']['channelId'] for item in items]))
                    channel_chunks = [channel_ids[i:i + 50] for i in range(0, len(channel_ids), 50)]
                    subs_map = {}
                    for chunk in channel_chunks:
                        channel_request = youtube.channels().list(part="statistics", id=','.join(chunk))
                        channel_response = channel_request.execute()
                        for item in channel_response['items']:
                            subs_map[item['id']] = int(item['statistics'].get('subscriberCount', 0))

                    raw_data_list = []
                    for item in items:
                        vid = item['id']
                        thumbs = item['snippet']['thumbnails']
                        thumb = thumbs.get('maxres', thumbs.get('standard', thumbs.get('high', thumbs.get('medium'))))['url']
                        
                        view_count = int(item['statistics'].get('viewCount', 0))
                        sub_count = subs_map.get(item['snippet']['channelId'], 0)
                        perf = (view_count / sub_count * 100) if sub_count > 0 else 0
                        
                        if perf >= 1000: grade = "🚀 떡상중 (1000%↑)"
                        elif perf >= 300: grade = "📈 급상승 (300%↑)"
                        elif perf >= 100: grade = "👀 주목 (100%↑)"
                        else: grade = "💤 일반"

                        if not (subs_range[0] <= sub_count <= subs_range[1]): continue
                        
                        grade_simple = grade.split(" (")[0]
                        pass_grade = False
                        for f in filter_grade:
                            if grade_simple in f:
                                pass_grade = True
                                break
                        if not pass_grade: continue

                        raw_date = datetime.strptime(item['snippet']['publishedAt'][:10], "%Y-%m-%d")
                        
                        raw_data_list.append({
                            "raw_perf": perf, 
                            "raw_date": raw_date,
                            "raw_view": view_count,
                            "raw_sub": sub_count,
                            "raw_comment": int(item['statistics'].get('commentCount', 0)),
                            "raw_like": int(item['statistics'].get('likeCount', 0)),
                            "thumbnail": thumb,
                            "title": item['snippet']['title'],
                            "channel": item['snippet']['channelTitle'],
                            "grade": grade,
                            "duration": parse_duration(item['contentDetails']['duration']),
                            "vid": vid
                        })
                    
                    sorted_list = sorted(raw_data_list, key=lambda x: (x['raw_perf'], x['raw_date']), reverse=True)
                    
                    display_data = []
                    for i, row in enumerate(sorted_list):
                        engagement = (row['raw_comment'] / row['raw_view'] * 100) if row['raw_view'] else 0
                        display_data.append({
                            "No": str(i + 1),
                            "썸네일": row['thumbnail'],
                            "채널명": row['channel'],
                            "제목": row['title'],
                            "게시일": row['raw_date'].strftime("%Y-%m-%d"),
                            "구독자": f"{row['raw_sub']:,}", 
                            "조회수": f"{row['raw_view']:,}",
                            "성과도": row['raw_perf'],
                            "등급": row['grade'],
                            "길이": row['duration'],
                            "댓글": f"{row['raw_comment']:,}",
                            "좋아요": f"{row['raw_like']:,}",
                            "참여율": f"{engagement:.2f}%",
                            "이동": f"https://www.youtube.com/watch?v={row['vid']}",
                            "ID": row['vid'],
                            "raw_perf": row['raw_perf'],
                            "raw_view": row['raw_view']
                        })

                    st.session_state.df_result = pd.DataFrame(display_data)

        except Exception as e: st.error(f"에러 발생: {e}")

# -------------------------------------------------------------------------
# 3. 화면 출력
# -------------------------------------------------------------------------
with st.sidebar:
    # ⭐ [요청 반영] 물리적 여백 60px (로고 내리기)
    st.markdown('<div style="height: 60px;"></div>', unsafe_allow_html=True)
    
    # ⭐ [요청 반영] 로고 박스 색상 복구
    st.markdown("""
        <div class="sidebar-logo">
            <h3 style='margin:0; color: white; font-size: 20px; text-shadow: 0 2px 4px rgba(0,0,0,0.5);'>
                📡 SIGNAL PREVIEW
            </h3>
        </div>
    """, unsafe_allow_html=True)
    
    preview_container = st.container()
    
    if st.session_state.df_result is not None and not st.session_state.df_result.empty:
        df = st.session_state.df_result
        st.divider()
        st.markdown("### 📊 전체 요약")
        m1, m2 = st.columns(2)
        m1.metric("총 조회수", f"{df['raw_view'].sum():,}")
        m2.metric("떡상중", f"{len(df[df['등급'].str.contains('떡상중')])}개")
        st.info("📌 리스트에서 영상을 선택하세요.")
    else:
        st.info("검색을 시작해주세요.")

if st.session_state.df_result is not None:
    df = st.session_state.df_result
    st.success(f"신호 포착 완료! {len(df)}건")
    
    max_perf_val = df['raw_perf'].max()
    if max_perf_val == 0 or pd.isna(max_perf_val): max_perf_val = 1000

    selection = st.dataframe(
        df,
        column_order=("No", "썸네일", "채널명", "제목", "게시일", "구독자", "조회수", "성과도", "등급", "길이", "댓글", "좋아요", "참여율", "이동"),
        column_config={
            "No": st.column_config.TextColumn("No", width=60),
            "썸네일": st.column_config.ImageColumn("썸네일", width=105),
            "채널명": st.column_config.TextColumn("채널명", width=180),
            "제목": st.column_config.TextColumn("제목", width=500),
            "게시일": st.column_config.TextColumn("게시일", width=110),
            "구독자": st.column_config.TextColumn("구독자", width=110),
            "조회수": st.column_config.TextColumn("조회수", width=110),
            "성과도": st.column_config.ProgressColumn("성과도", format="%.0f%%", min_value=0, max_value=max_perf_val, width=110),
            "등급": st.column_config.TextColumn("등급", width=110),
            "길이": st.column_config.TextColumn("길이", width=90),
            "댓글": st.column_config.TextColumn("댓글", width=90),
            "좋아요": st.column_config.TextColumn("좋아요", width=90),
            "참여율": st.column_config.TextColumn("참여율", width=90),
            "이동": st.column_config.LinkColumn("이동", display_text="▶", width=60),
            "ID": None, "raw_perf": None, "raw_view": None
        },
        hide_index=True, use_container_width=True, height=1200, 
        on_select="rerun", selection_mode="single-row"
    )

    # 1번 자동 선택
    selected_row = None
    if selection.selection.rows:
        selected_row = df.iloc[selection.selection.rows[0]]
    elif not df.empty:
        selected_row = df.iloc[0]

    if selected_row is not None:
        with preview_container:
            st.markdown(f"#### {selected_row['제목']}")
            st.markdown("<br>", unsafe_allow_html=True)
            
            st.video(f"https://www.youtube.com/watch?v={selected_row['ID']}")
            
            st.markdown("---")
            c_meta1, c_meta2 = st.columns(2)
            with c_meta1: st.caption(f"📺 채널명: {selected_row['채널명']}")
            with c_meta2: st.caption(f"📅 게시날짜: {selected_row['게시일']}")
            
            c_stat1, c_stat2 = st.columns(2)
            with c_stat1: st.metric("성과도", f"{selected_row['raw_perf']:,.0f}%")
            with c_stat2: st.metric("조회수", f"{selected_row['raw_view']:,}")
            
            st.markdown("<br>", unsafe_allow_html=True)
            st.link_button("🔗 유튜브에서 보기 (이동)", f"https://www.youtube.com/watch?v={selected_row['ID']}", use_container_width=True, type="primary")

            st.divider()
            if "떡상중" in selected_row['등급']: st.success("🔥 **떡상중 (1000%↑)**")
            elif "급상승" in selected_row['등급']: st.info("👍 **급상승 (300%↑)**")
            elif "주목" in selected_row['등급']: st.warning("🟢 **주목 (100%↑)**")



