import streamlit as st
from googleapiclient.discovery import build
from datetime import datetime, timedelta
import isodate
import pandas as pd

# ==========================================
# 🔐 API 키는 Streamlit Cloud의 'Secrets'에서 가져옵니다.
# ==========================================

st.set_page_config(page_title="SIGNAL - Insight", layout="wide", page_icon="📡")

# -------------------------------------------------------------------------
# ⭐ [데이터 정의]
#   - CATEGORY_MAP: 향후 카테고리 필터 기능 추가용(현재는 미사용)
# -------------------------------------------------------------------------
CATEGORY_MAP = {
    "전체": None, "영화/애니": "1", "자동차": "2", "음악": "10", 
    "동물": "15", "스포츠": "17", "여행/이벤트": "19", "게임": "20", 
    "브이로그/인물": "22", "코미디": "23", "엔터테인먼트": "24", 
    "뉴스/정치": "25", "하우투/스타일": "26", "교육": "27", "과학/기술": "28"
}
region_map = {"🔵한국": "KR", "🔴일본": "JP", "🟢미국": "US", "🌏전체": None}

# -------------------------------------------------------------------------
# 🌑 [스타일링: Red Killer Final + 높이 통일]
# -------------------------------------------------------------------------
st.markdown("""
<style>
    /* 1. 전체 배경 */
    .stApp { background-color: #0E1117; color: #FAFAFA; }
    
    /* 2. 사이드바 디자인 */
    section[data-testid="stSidebar"] { 
        min-width: 600px !important; 
        background-color: #1A1C24; 
        text-align: center; 
    }
    [data-testid="stSidebar"] .block-container { 
        padding-top: 5rem !important; 
    }

    /* 3. ⭐ [핵심 수정] 위젯 높이 통일 및 여백 축소 */
    div.stSelectbox > div, 
    div.stTextInput > div, 
    div.stFormSubmitButton > button {
        min-height: 38px !important; /* 높이 통일 */
    }
    
    /* 4. 버튼 및 링크 색상 강제 민트색 적용 */
    button[kind="primary"], 
    div.stButton > button, 
    a[kind="primary"] {
        background: linear-gradient(90deg, #00C6FF 0%, #0072FF 100%) !important;
        color: white !important;
        border: none !important;
        font-weight: bold !important;
    }
    button[kind="primary"]:hover, 
    a[kind="primary"]:hover {
        transform: scale(1.02) !important;
    }

    /* 5. Pills, Slider, Checkbox 색상 강제 민트색 */
    div[data-testid="stPills"] button[aria-pressed="true"] {
        background-color: #00E5FF !important; 
        color: black !important;
    }
    div[data-testid="stSlider"] div[data-baseweb="slider"] div {
        background-color: #00E5FF !important; /* 슬라이더 막대 색상 */
    }
    
    /* 6. 입력창 테두리 색상 */
    input:focus, 
    div[data-baseweb="select"] > div:focus-within {
        border-color: #00E5FF !important;
        box-shadow: 0 0 0 1px #00E5FF !important;
    }

    /* 7. 메트릭 및 로고 스타일 */
    [data-testid="stMetricValue"] { 
        font-size: 24px !important; 
        color: #00E5FF !important; 
        font-weight: 700 !important; 
    }
    .sidebar-logo {
        background: linear-gradient(135deg, #1e3a8a 0%, #00c6ff 100%);
        padding: 12px; 
        border-radius: 8px; 
        margin-bottom: 20px;
        border: 1px solid rgba(255, 255, 255, 0.2);
        box-shadow: 0 4px 15px rgba(0, 198, 255, 0.3);
        width: 90%; 
        margin-left: auto; 
        margin-right: auto;
    }

    /* placeholder 스타일 */
    .stTextInput input::placeholder {
        font-style: italic;
        color: #888 !important; 
    }
</style>
""", unsafe_allow_html=True)

st.title("📡 SIGNAL : Insight")

# -------------------------------------------------------------------------
# 함수 정의
# -------------------------------------------------------------------------
def parse_duration(d: str) -> str:
    """ISO 8601 duration 문자열을 mm:ss 또는 hh:mm:ss로 변환."""
    try:
        dur = isodate.parse_duration(d)
        sec = int(dur.total_seconds())
        m, s = divmod(sec, 60)
        h, m = divmod(m, 60)
        return f"{h}:{m:02}:{s:02}" if h else f"{m}:{s:02}"
    except Exception:
        return d

# -------------------------------------------------------------------------
# 1. 상단 (Top) 검색창
# -------------------------------------------------------------------------
api_key = st.secrets.get("YOUTUBE_API_KEY", None)
if 'df_result' not in st.session_state:
    st.session_state.df_result = None

with st.form(key='search_form'):
    if not api_key:
        api_key = st.text_input("API 키 입력", type="password")

    # ⭐ [1행] 모든 요소를 아래 정렬로 밀착하여 배치
    c1, c2, c3, c4, c5, c6 = st.columns(
        [1.5, 0.5, 0.7, 0.8, 1.5, 1.2], 
        vertical_alignment="bottom"
    )
    
    with c1:
        query = st.text_input("키워드", placeholder="키워드 입력")
    with c2:
        search_trigger = st.form_submit_button("🚀", type="primary", use_container_width=True)
    with c3:
        max_results = st.selectbox("수집", [10, 30, 50, 100], index=1)
    with c4:
        days_filter = st.selectbox("기간", ["1주일", "1개월", "3개월", "전체"], index=1)
    with c5: 
        st.caption("국가")
        country_options = st.pills(
            "국가", 
            ["🔵한국", "🔴일본", "🟢미국", "🌏전체"], 
            default=["🔵한국"], 
            selection_mode="multi", 
            label_visibility="collapsed"
        )
    with c6:
        st.caption("길이")
        video_durations = st.pills(
            "길이", 
            ["쇼츠", "롱폼"], 
            default=["쇼츠"], 
            selection_mode="multi", 
            label_visibility="collapsed"
        )

    # [2행] 등급 | 구독자
    c7, c8 = st.columns([3, 2], vertical_alignment="center")
    with c7: 
        st.caption("등급 필터")
        filter_grade = st.pills(
            "등급", 
            ["🚀 떡상중", "📈 급상승", "👀 주목", "💤 일반"], 
            default=["🚀 떡상중", "📈 급상승", "👀 주목"], 
            selection_mode="multi", 
            label_visibility="collapsed"
        )
    with c8:
        st.caption("구독자 범위")
        subs_range = st.slider(
            "구독자", 0, 1_000_000, (0, 1_000_000), 
            1000, label_visibility="collapsed"
        )

# -------------------------------------------------------------------------
# 2. 로직
# -------------------------------------------------------------------------

# (시간 기준 통일)
now = datetime.now()

# (API Parameter Calculation)
if days_filter == "1주일":
    published_after = (now - timedelta(days=7)).isoformat("T") + "Z"
elif days_filter == "1개월":
    published_after = (now - timedelta(days=30)).isoformat("T") + "Z"
elif days_filter == "3개월":
    published_after = (now - timedelta(days=90)).isoformat("T") + "Z"
else:
    published_after = None

api_duration = "any"
if len(video_durations) == 1:
    if "쇼츠" in video_durations:
        api_duration = "short"
    elif "롱폼" in video_durations:
        api_duration = "long"

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
                # 국가 선택 처리
                target_countries = [region_map[c] for c in country_options if c != "🌏전체"]
                if "🌏전체" in country_options:
                    # 전체를 선택한 경우 글로벌 검색도 포함
                    target_countries.append(None)
                if not target_countries:
                    target_countries = [None]
                
                # 국가별로 검색 수행
                for region_code in target_countries:
                    per_country_max = min(50, max(10, int(max_results / len(target_countries))))
                    
                    search_params = {
                        "part": "snippet",
                        "q": query,
                        "maxResults": per_country_max,
                        "order": "viewCount",
                        "type": "video",
                        "videoDuration": api_duration,
                    }
                    if published_after:
                        search_params["publishedAfter"] = published_after
                    if region_code:
                        search_params["regionCode"] = region_code

                    search_request = youtube.search().list(**search_params)
                    search_response = search_request.execute()
                    all_video_ids.extend(
                        [item['id']['videoId'] for item in search_response.get('items', [])]
                    )

                # 중복 제거
                all_video_ids = list(set(all_video_ids))

                if not all_video_ids:
                    st.error("신호 없음 (검색 결과 0건)")
                    st.session_state.df_result = pd.DataFrame()
                else:
                    # 1) 비디오 상세 정보 조회 (50개씩 chunk)
                    video_items = []
                    video_id_chunks = [
                        all_video_ids[i:i + 50] for i in range(0, len(all_video_ids), 50)
                    ]
                    for chunk in video_id_chunks:
                        video_request = youtube.videos().list(
                            part="statistics,snippet,contentDetails",
                            id=",".join(chunk)
                        )
                        video_response = video_request.execute()
                        video_items.extend(video_response.get('items', []))

                    # 2) 채널 통계 조회 (채널도 50개씩 chunk 처리)
                    channel_ids = list(
                        set([item['snippet']['channelId'] for item in video_items])
                    )
                    subs_map = {}
                    video_count_map = {}

                    channel_id_chunks = [
                        channel_ids[i:i + 50] for i in range(0, len(channel_ids), 50)
                    ]
                    for ch_chunk in channel_id_chunks:
                        channel_response = youtube.channels().list(
                            part="statistics",
                            id=",".join(ch_chunk)
                        ).execute()
                        for ch in channel_response.get('items', []):
                            ch_id = ch['id']
                            stats = ch.get('statistics', {})
                            subs_map[ch_id] = int(stats.get('subscriberCount', 0))
                            video_count_map[ch_id] = int(stats.get('videoCount', 0))

                    # 3) 지표 계산 및 필터링
                    raw_data_list = []
                    for item in video_items:
                        vid = item['id']
                        thumbs = item['snippet']['thumbnails']
                        thumb = thumbs.get(
                            'maxres', 
                            thumbs.get('standard', thumbs.get('high', thumbs.get('medium')))
                        )['url']
                        
                        stats = item.get('statistics', {})
                        view_count = int(stats.get('viewCount', 0))
                        comment_count = int(stats.get('commentCount', 0))
                        like_count = int(stats.get('likeCount', 0))

                        ch_id = item['snippet']['channelId']
                        sub_count = subs_map.get(ch_id, 0)
                        perf = (view_count / sub_count * 100) if sub_count > 0 else 0
                        
                        # 등급판정
                        if perf >= 1000:
                            grade = "🚀 떡상중 (1000%↑)"
                        elif perf >= 300:
                            grade = "📈 급상승 (300%↑)"
                        elif perf >= 100:
                            grade = "👀 주목 (100%↑)"
                        else:
                            grade = "💤 일반"

                        # 구독자 범위 필터
                        if not (subs_range[0] <= sub_count <= subs_range[1]):
                            continue
                        
                        # 등급 필터
                        grade_simple = grade.split(" (")[0]
                        pass_grade = any(grade_simple in f for f in filter_grade)
                        if not pass_grade:
                            continue

                        # 게시일 / 일일 속도
                        raw_date = datetime.strptime(
                            item['snippet']['publishedAt'][:10], "%Y-%m-%d"
                        )
                        days_diff = (now - raw_date).days
                        daily_velocity = view_count / (days_diff if days_diff else 1)
                        
                        raw_data_list.append({
                            "raw_perf": perf,
                            "raw_date": raw_date,
                            "raw_view": view_count,
                            "raw_sub": sub_count,
                            "raw_comment": comment_count,
                            "raw_like": like_count,
                            "thumbnail": thumb,
                            "title": item['snippet']['title'],
                            "channel": item['snippet']['channelTitle'],
                            "grade": grade,
                            "duration": parse_duration(item['contentDetails']['duration']),
                            "vid": vid,
                            "총 영상 수": video_count_map.get(ch_id, 0),
                            "일일 속도": daily_velocity,
                        })
                    
                    # 4) 정렬 (성과도 > 게시일)
                    sorted_list = sorted(
                        raw_data_list,
                        key=lambda x: (x['raw_perf'], x['raw_date']),
                        reverse=True
                    )
                    
                    # 5) 화면 표시용 데이터 변환
                    display_data = []
                    for i, row in enumerate(sorted_list):
                        # 참여도 (댓글 / 조회수 * 100)
                        engagement = (
                            (row['raw_comment'] / row['raw_view'] * 100)
                            if row['raw_view'] else 0
                        )
                        display_data.append({
                            "No": str(i + 1),
                            "썸네일": row['thumbnail'],
                            "채널명": row['channel'],
                            "제목": row['title'],
                            "게시일": row['raw_date'].strftime("%Y/%m/%d"),
                            "총 영상 수": f"{row['총 영상 수']:,}개",
                            "구독자": f"{row['raw_sub']:,}",
                            "조회수": f"{row['raw_view']:,}",
                            "성과도": row['raw_perf'],
                            "등급": row['grade'],
                            "길이": row['duration'],
                            "일일 속도": f"{int(row['일일 속도']):,}회",
                            "이동": f"https://www.youtube.com/watch?v={row['vid']}",
                            "ID": row['vid'],
                            # 내부 계산용 raw 값 (표에서는 숨김)
                            "raw_perf": row['raw_perf'],
                            "raw_view": row['raw_view'],
                            "raw_comment": row['raw_comment'],
                            "raw_like": row['raw_like'],
                            "raw_engagement": engagement,
                        })

                    st.session_state.df_result = pd.DataFrame(display_data)

        except Exception as e:
            st.error(f"에러 발생: {e}")

# -------------------------------------------------------------------------
# 3. 화면 출력
# -------------------------------------------------------------------------
with st.sidebar:
    st.markdown('<div style="height: 60px;"></div>', unsafe_allow_html=True)
    st.markdown("""
        <div class="sidebar-logo">
            <h3 style='margin:0; color: white; font-size: 20px; text-shadow: 0 0 10px rgba(0, 229, 255, 0.6);'>
                📡 SIGNAL PREVIEW
            </h3>
        </div>
    """, unsafe_allow_html=True)
    
    preview_container = st.container()
    
    if st.session_state.df_result is not None and not st.session_state.df_result.empty:
        df = st.session_state.df_result
        st.divider()
        total_views = df['raw_view'].sum()
        s_tier_count = len(df[df['등급'].str.contains('떡상중')])
        
        st.markdown("### 📊 전체 요약")
        m1, m2 = st.columns(2)
        m1.metric("총 조회수", f"{total_views:,}")
        m2.metric("떡상중", f"{s_tier_count}개")
        st.info("📌 리스트에서 영상을 선택하세요.")
    else:
        st.info("검색을 시작해주세요.")

if st.session_state.df_result is not None and not st.session_state.df_result.empty:
    df = st.session_state.df_result
    st.success(f"신호 포착 완료! {len(df)}건")
    
    max_perf_val = df['raw_perf'].max() if len(df) > 0 else 1000
    if max_perf_val == 0 or pd.isna(max_perf_val):
        max_perf_val = 1000

    selection = st.dataframe(
        df,
        column_order=(
            "No", "썸네일", "채널명", "제목", "게시일", 
            "총 영상 수", "구독자", "조회수", 
            "성과도", "등급", "일일 속도", "길이", "이동"
        ),
        column_config={
            "No": st.column_config.TextColumn("No", width=8),
            "썸네일": st.column_config.ImageColumn("썸네일", width=69),
            "채널명": st.column_config.TextColumn("채널명", width=120),
            "제목": st.column_config.TextColumn("제목", width=300),
            "게시일": st.column_config.TextColumn("게시일", width=56),
            "총 영상 수": st.column_config.TextColumn("총 영상 수", width=56), 
            "구독자": st.column_config.TextColumn("구독자", width=64),
            "조회수": st.column_config.TextColumn("조회수", width=64),
            "성과도": st.column_config.ProgressColumn(
                "성과도",
                format="%.0f%%",
                min_value=0,
                max_value=max_perf_val,
                width=80
            ),
            "등급": st.column_config.TextColumn("등급", width=90),
            "일일 속도": st.column_config.TextColumn("일일 속도", width=80),
            "길이": st.column_config.TextColumn("길이", width=60),
            "이동": st.column_config.LinkColumn("이동", display_text="▶", width=40),
            # 내부 계산용 컬럼 숨김
            "ID": None,
            "raw_perf": None,
            "raw_view": None,
            "raw_comment": None,
            "raw_like": None,
            "raw_engagement": None,
        },
        hide_index=True,
        use_container_width=True,
        height=700, 
        on_select="rerun",
        selection_mode="single-row"
    )

    selected_row = None
    if selection.selection.rows:
        selected_row = df.iloc[selection.selection.rows[0]]
    elif not df.empty:
        selected_row = df.iloc[0]

    if selected_row is not None:
        vid_id = selected_row['ID']
        
        with preview_container:
            st.markdown(f"""
                <div style='padding: 10px 0; border-bottom: 1px solid rgba(255,255,255,0.1); margin-bottom: 15px;'>
                    <h4 style='margin:0; color: #00E5FF; text-shadow: 0 0 10px rgba(0, 229, 255, 0.6); line-height: 1.4; font-size: 18px;'>
                        {selected_row['제목']}
                    </h4>
                </div>
            """, unsafe_allow_html=True)
            
            st.video(f"https://www.youtube.com/watch?v={vid_id}")
            
            st.markdown("---")
            c_meta1, c_meta2 = st.columns(2)
            with c_meta1:
                st.caption(f"📺 채널명: {selected_row['채널명']} (총 영상 {selected_row['총 영상 수']})")
            with c_meta2:
                st.caption(f"📅 게시날짜: {selected_row['게시일']}")
            
            # 성과/조회수/참여도 메트릭
            c_stat1, c_stat2, c_stat3 = st.columns(3)
            with c_stat1:
                st.metric("성과도", f"{selected_row['raw_perf']:,.0f}%")
            with c_stat2:
                st.metric("조회수", f"{selected_row['raw_view']:,}")
            with c_stat3:
                try:
                    engagement_val = float(selected_row['raw_engagement'])
                except Exception:
                    engagement_val = 0.0
                st.metric("참여도(댓글/조회수)", f"{engagement_val:.2f}%")
            
            st.markdown("<br>", unsafe_allow_html=True)
            st.link_button(
                "🔗 유튜브에서 보기 (이동)", 
                f"https://www.youtube.com/watch?v={vid_id}", 
                use_container_width=True, 
                type="primary"
            )

            st.divider()
            
            # 등급 뱃지
            if "떡상중" in selected_row['등급']:
                st.success("🔥 **떡상중 (1000%↑)**")
            elif "급상승" in selected_row['등급']:
                st.info("👍 **급상승 (300%↑)**")
            elif "주목" in selected_row['등급']:
                st.warning("🟢 **주목 (100%↑)**")
            else:
                st.caption("💤 **일반**")
