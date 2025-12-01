import streamlit as st
from googleapiclient.discovery import build
from datetime import datetime, timedelta
import isodate
import pandas as pd

# ==========================================
# 🔐 API 키는 Streamlit Cloud의 'Secrets'에서 가져옵니다.
# ==========================================

st.set_page_config(page_title="SIGNAL - YouTube Insight", layout="wide", page_icon="📡")

# 🌑 [스타일링: 다크모드 + 민트 포인트]
st.markdown("""
<style>
    /* 전체 테마 */
    .stApp { background-color: #0E1117; color: #FAFAFA; }
    
    /* 사이드바 강제 확장 (700px) & 디자인 */
    section[data-testid="stSidebar"] { min-width: 700px !important; }
    [data-testid="stSidebar"] { 
        background-color: #1A1C24; 
        border-right: 1px solid #333; 
        text-align: center; 
    }
    
    /* 테이블 스타일 */
    th { background-color: #1E3A8A !important; color: white !important; text-align: center !important; }
    td { vertical-align: middle !important; text-align: center !important; font-size: 15px !important; }
    
    /* 링크 스타일 */
    a { text-decoration: none; color: #00E5FF; font-weight: bold; } /* 민트색 링크 */
    a:hover { color: #FFFFFF; text-decoration: underline; }
    
    /* 썸네일 이미지 둥글게 */
    img { border-radius: 6px; }
    
    /* ⭐ [핵심 1] 버튼 색상 변경 (민트/시안 그라데이션) */
    div.stButton > button:first-child {
        background: linear-gradient(90deg, #00E5FF 0%, #2979FF 100%);
        color: white;
        border: none;
        font-weight: bold;
        transition: 0.3s;
    }
    div.stButton > button:first-child:hover {
        transform: scale(1.02);
        box-shadow: 0 0 15px rgba(0, 229, 255, 0.6);
    }
    /* 링크 버튼(유튜브 이동)도 동일하게 적용 */
    a[kind="primary"] {
        background: linear-gradient(90deg, #00E5FF 0%, #2979FF 100%) !important;
        color: white !important;
        border: none !important;
    }

    /* ⭐ [핵심 2] 사이드바 로고 슬림하게 수정 */
    .sidebar-logo {
        background: linear-gradient(90deg, #0D1117 0%, #161B22 100%);
        padding: 12px; /* 패딩 축소 (20 -> 12) */
        border-radius: 8px;
        margin-bottom: 10px;
        text-align: center;
        border: 1px solid #30363D;
        box-shadow: 0 4px 6px rgba(0,0,0,0.3);
    }
    
    /* 메트릭 숫자 색상 (민트색) */
    [data-testid="stMetricValue"] { font-size: 28px !important; color: #00E5FF !important; font-weight: 700 !important; }
    [data-testid="stMetricLabel"] { font-size: 14px !important; color: #AAA !important; }
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
        with c1: query = st.text_input("검색어 (엔터!)", "")
        with c2: max_results = st.selectbox("수집수", [10, 30, 50], index=1)
        with c3: days_filter = st.selectbox("기간", ["1주일", "1개월", "3개월", "전체"], index=1)
        with c4: 
            country_option = st.selectbox("국가", ["🇰🇷 한국", "🇯🇵 일본", "🇺🇸 미국", "🌏 전세계"], index=0)
            region_map = {"🇰🇷 한국": "KR", "🇯🇵 일본": "JP", "🇺🇸 미국": "US", "🌏 전세계": None}
            region_code = region_map[country_option]

        c5, c6, c7 = st.columns([1, 2, 2])
        with c5: video_duration = st.radio("길이", ["쇼츠", "롱폼", "전체"], index=0, horizontal=True)
        with c6: filter_grade = st.multiselect("등급 필터", ["🟣 S-Tier", "🔴 A-Tier", "🟢 B-Tier", "⚪ Normal"], default=["🟣 S-Tier", "🔴 A-Tier", "🟢 B-Tier"])
        with c7: subs_range = st.slider("구독자 범위", 0, 1000000, (0, 1000000), 1000)

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
api_duration = "short" if video_duration == "쇼츠" else ("long" if video_duration == "롱폼" else "any")

if search_trigger:
    if not query:
        st.warning("⚠️ 검색어를 입력해주세요!")
    elif not api_key:
        st.error("🔑 API 키가 설정되지 않았습니다.")
    else:
        try:
            youtube = build('youtube', 'v3', developerKey=api_key)
            with st.spinner(f"📡 '{query}' 신호 분석 중..."):
                search_request = youtube.search().list(
                    part="snippet", q=query, maxResults=max_results, order="viewCount", type="video", 
                    videoDuration=api_duration, publishedAfter=published_after, regionCode=region_code
                )
                search_response = search_request.execute()
                video_ids = [item['id']['videoId'] for item in search_response['items']]

                if not video_ids: st.error("신호 없음 (검색 결과 0건)")
                else:
                    video_request = youtube.videos().list(part="statistics, snippet, contentDetails", id=','.join(video_ids))
                    video_response = video_request.execute()
                    
                    channel_ids = [item['snippet']['channelId'] for item in video_response['items']]
                    channel_request = youtube.channels().list(part="statistics", id=','.join(channel_ids))
                    channel_response = channel_request.execute()
                    subs_map = {item['id']: int(item['statistics'].get('subscriberCount', 0)) for item in channel_response['items']}

                    raw_data_list = []
                    for item in video_response['items']:
                        vid = item['id']
                        thumbs = item['snippet']['thumbnails']
                        thumb = thumbs.get('maxres', thumbs.get('standard', thumbs.get('high', thumbs.get('medium'))))['url']
                        
                        view_count = int(item['statistics'].get('viewCount', 0))
                        sub_count = subs_map.get(item['snippet']['channelId'], 0)
                        perf = (view_count / sub_count * 100) if sub_count > 0 else 0
                        
                        if perf >= 1000: grade = "🟣 S-Tier"
                        elif perf >= 300: grade = "🔴 A-Tier"
                        elif perf >= 100: grade = "🟢 B-Tier"
                        else: grade = "⚪ Normal"

                        if not (subs_range[0] <= sub_count <= subs_range[1]): continue
                        if grade not in filter_grade: continue

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
                            "게시일": row['raw_date'].strftime("%Y/%m/%d"),
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
    # 🎨 1. 사이드바 로고 (슬림 & 높이 맞춤)
    st.markdown("""
        <div class="sidebar-logo">
            <h3 style='margin:0; color: #E0E0E0; font-size: 20px;'>📡 SIGNAL PREVIEW</h3>
        </div>
    """, unsafe_allow_html=True)
    
    if st.session_state.df_result is not None and not st.session_state.df_result.empty:
        df = st.session_state.df_result
        preview_container = st.container()
        
        st.divider()
        st.markdown("### 📊 전체 요약")
        m1, m2 = st.columns(2)
        m1.metric("총 조회수", f"{df['raw_view'].sum():,}")
        m2.metric("S-Tier", f"{len(df[df['등급'].str.contains('S-Tier')])}개")
        st.info("📌 리스트를 선택하면 상세 분석이 표시됩니다.")
    else:
        st.info("검색을 시작해주세요.")
        preview_container = st.empty()

if st.session_state.df_result is not None:
    df = st.session_state.df_result
    st.success(f"신호 포착 완료! {len(df)}건")
    
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
            "성과도": st.column_config.ProgressColumn("성과도", format="%.0f%%", min_value=0, max_value=1000, width=110),
            "등급": st.column_config.TextColumn("등급", width=110),
            "길이": st.column_config.TextColumn("길이", width=90),
            "댓글": st.column_config.TextColumn("댓글", width=90),
            "좋아요": st.column_config.TextColumn("좋아요", width=90),
            "참여율": st.column_config.TextColumn("참여율", width=90),
            "이동": st.column_config.LinkColumn("이동", display_text="▶", width=60),
            "ID": None, "raw_perf": None, "raw_view": None
        },
        hide_index=True, use_container_width=False, height=1200, 
        on_select="rerun", selection_mode="single-row"
    )

    if selection.selection.rows:
        row = df.iloc[selection.selection.rows[0]]
        
        with preview_container:
            # 2. 제목 (여백 추가하여 영상과 분리)
            st.markdown(f"#### {row['제목']}")
            st.markdown("<br>", unsafe_allow_html=True) # 공백 추가
            
            # 3. 영상 플레이어
            st.video(f"https://www.youtube.com/watch?v={row['ID']}")
            
            # ⭐ [핵심 3] 정보창 3단 층별 정리 (깔끔한 정렬)
            st.markdown("---")
            
            # 1층: 소속 정보 (회색톤, 작게)
            c_meta1, c_meta2 = st.columns(2)
            with c_meta1: st.caption(f"📺 {row['채널명']}")
            with c_meta2: st.caption(f"📅 {row['게시일']}")
            
            # 2층: 성적표 (강조된 민트색 숫자)
            c_stat1, c_stat2 = st.columns(2)
            with c_stat1: st.metric("성과도", f"{row['raw_perf']:,.0f}%")
            with c_stat2: st.metric("조회수", f"{row['raw_view']:,}")
            
            # 3층: 액션 버튼 (꽉 차게)
            st.markdown("<br>", unsafe_allow_html=True)
            st.link_button("🔗 유튜브에서 보기 (이동)", f"https://www.youtube.com/watch?v={row['ID']}", use_container_width=True, type="primary")

            # 등급 뱃지 (맨 아래)
            st.divider()
            if "S-Tier" in row['등급']: st.success("🔥 **S-Tier (전설)**")
            elif "A-Tier" in row['등급']: st.info("👍 **A-Tier (초대박)**")
