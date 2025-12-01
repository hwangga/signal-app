import streamlit as st
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from datetime import datetime, timedelta
import isodate
import pandas as pd
from typing import Optional, List, Dict, Tuple

# ==========================================
# 🔐 API 키는 Streamlit Cloud의 'Secrets'에서 가져옵니다.
# ==========================================
st.set_page_config(page_title="SIGNAL - Insight", layout="wide", page_icon="📡")

# -------------------------------------------------------------------------
# ⭐ [데이터 정의]
# -------------------------------------------------------------------------
REGION_MAP = {"🔵한국": "KR", "🔴일본": "JP", "🟢미국": "US", "🌏전체": None}
GRADE_THRESHOLDS = {
    "🚀 떡상중": 1000,
    "📈 급상승": 300,
    "👀 주목": 100,
    "💤 일반": 0
}

# -------------------------------------------------------------------------
# 🌑 [스타일링]
# -------------------------------------------------------------------------
st.markdown("""
<style>
    .stApp { background-color: #0E1117; color: #FAFAFA; }

    .block-container {
        padding-top: 0.8rem !important;
    }

    h1 {
        margin-top: 0.2rem !important;
        margin-bottom: 0.8rem !important;
    }

    section[data-testid="stSidebar"] {
        min-width: 700px !important;
        max-width: 700px !important;
        background-color: #111827;
        border-right: 1px solid rgba(148, 163, 184, 0.3);
    }
    section[data-testid="stSidebar"] .block-container {
        padding-top: 0.8rem !important;
    }

    div.stSelectbox > div,
    div.stTextInput > div,
    div.stFormSubmitButton > button {
        min-height: 40px !important;
    }
    input[type="text"] {
        min-height: 40px !important;
    }

    button, 
    button[data-testid="baseButton-primary"],
    button[data-testid="baseButton-secondary"],
    div.stButton > button {
        background: linear-gradient(90deg, #00C6FF 0%, #0072FF 100%) !important;
        color: white !important;
        border: none !important;
        font-weight: 600 !important;
    }
    button:hover, 
    button[data-testid="baseButton-primary"]:hover,
    button[data-testid="baseButton-secondary"]:hover,
    div.stButton > button:hover {
        transform: scale(1.02) !important;
    }

    div[data-testid="stPills"] button {
        border-radius: 999px !important;
        border: 1px solid rgba(150, 200, 255, 0.3) !important;
        background-color: rgba(15, 23, 42, 0.9) !important;
        color: #e5e7eb !important;
        font-size: 12px !important;
        padding: 2px 12px !important;
    }

    div[data-testid="stPills"] button[aria-pressed="true"] {
        background: linear-gradient(90deg, #00E5FF, #22D3EE) !important;
        color: #020617 !important;
        font-weight: 600 !important;
        border: 1px solid #a5f3fc !important;
        box-shadow: 0 0 8px rgba(45, 212, 191, 0.6) !important;
    }

    div[data-baseweb="slider"] * {
        background-color: rgba(56, 189, 248, 0.4) !important;
    }
    div[data-baseweb="slider"] div[role="slider"] {
        background-color: #00E5FF !important;
        border: 2px solid #e0faff !important;
    }

    section[data-testid="stSidebar"] form[data-testid="stForm"] {
        padding: 12px 16px 18px 16px !important;
        border-radius: 16px !important;
        border: 1px solid rgba(148, 163, 184, 0.4) !important;
        background: radial-gradient(circle at top left, rgba(56,189,248,0.18), transparent 55%),
                    radial-gradient(circle at bottom right, rgba(59,130,246,0.20), transparent 55%),
                    #020617;
    }

    .summary-bar {
        display: flex;
        flex-wrap: wrap;
        align-items: center;
        gap: 6px;
        padding: 6px 10px;
        margin: 4px 0 8px 0;
        border-radius: 12px;
        background: rgba(30, 41, 59, 0.85);
        border: 1px solid rgba(148, 163, 184, 0.5);
        font-size: 12px;
    }
    .summary-left {
        display: flex;
        flex-wrap: wrap;
        gap: 6px;
        align-items: center;
    }
    .summary-right {
        display: flex;
        flex-wrap: wrap;
        gap: 4px;
        align-items: center;
        margin-left: auto;
    }
    .chip {
        padding: 2px 8px;
        border-radius: 999px;
        font-size: 11px;
        border: 1px solid rgba(148, 163, 184, 0.6);
        white-space: nowrap;
    }
    .chip-hot { border-color: #fb7185; }
    .chip-view { border-color: #60a5fa; }
    .chip-eng { border-color: #34d399; }
    .chip-like { border-color: #facc15; }

    .summary-link {
        padding: 2px 10px;
        border-radius: 999px;
        font-size: 11px;
        text-decoration: none;
        border: 1px solid rgba(59, 130, 246, 0.9);
        background: rgba(37, 99, 235, 0.2);
        color: #BFDBFE;
        white-space: nowrap;
    }
    .summary-link:hover {
        background: rgba(59, 130, 246, 0.4);
    }

    .video-wrapper iframe {
        width: 100%;
        height: 500px;
        border-radius: 10px;
    }

    @media (max-width: 900px) {
        section[data-testid="stSidebar"] {
            min-width: 320px !important;
            max-width: 100% !important;
        }
        .summary-bar { font-size: 11px; padding: 6px 8px; }
        .summary-right { margin-left: 0; }
        .video-wrapper iframe { height: 220px; }
    }
</style>
""", unsafe_allow_html=True)

st.title("📡 SIGNAL : Insight")

# -------------------------------------------------------------------------
# 🔧 유틸리티 함수
# -------------------------------------------------------------------------
def parse_duration(duration_str: str) -> str:
    """ISO 8601 duration 문자열을 mm:ss 또는 hh:mm:ss로 변환."""
    try:
        dur = isodate.parse_duration(duration_str)
        total_seconds = int(dur.total_seconds())
        hours, remainder = divmod(total_seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        
        if hours > 0:
            return f"{hours}:{minutes:02}:{seconds:02}"
        return f"{minutes}:{seconds:02}"
    except Exception:
        return duration_str


def get_thumbnail_url(thumbnails: Dict) -> str:
    """썸네일 딕셔너리에서 최고 해상도 URL 추출."""
    priority = ["maxres", "standard", "high", "medium", "default"]
    for quality in priority:
        if quality in thumbnails:
            return thumbnails[quality]["url"]
    return ""


def calculate_grade(performance: float) -> str:
    """성과도에 따른 등급 계산."""
    for grade, threshold in GRADE_THRESHOLDS.items():
        if performance >= threshold:
            return grade
    return "💤 일반"


def format_number(num: int) -> str:
    """숫자를 쉼표로 포맷팅."""
    return f"{num:,}"


def get_published_after(days_filter: str) -> Optional[str]:
    """기간 필터에 따른 publishedAfter 값 반환."""
    now = datetime.now()
    
    days_map = {
        "1주일": 7,
        "1개월": 30,
        "3개월": 90,
        "전체": None
    }
    
    days = days_map.get(days_filter)
    if days is None:
        return None
    
    return (now - timedelta(days=days)).isoformat("T") + "Z"


# -------------------------------------------------------------------------
# 📊 데이터 처리 함수
# -------------------------------------------------------------------------
def fetch_channel_statistics(youtube, channel_ids: List[str]) -> Tuple[Dict[str, int], Dict[str, int]]:
    """채널 통계 정보 일괄 조회."""
    subs_map = {}
    video_count_map = {}
    
    # 50개씩 청크로 나누어 요청
    for i in range(0, len(channel_ids), 50):
        chunk = channel_ids[i:i + 50]
        try:
            response = youtube.channels().list(
                part="statistics",
                id=",".join(chunk)
            ).execute()
            
            for item in response.get("items", []):
                ch_id = item["id"]
                stats = item.get("statistics", {})
                subs_map[ch_id] = int(stats.get("subscriberCount", 0))
                video_count_map[ch_id] = int(stats.get("videoCount", 0))
        except HttpError as e:
            st.warning(f"채널 정보 조회 실패 (일부): {e}")
    
    return subs_map, video_count_map


def process_video_data(
    video_items: List[Dict],
    subs_map: Dict[str, int],
    video_count_map: Dict[str, int],
    filter_grade: List[str],
    subs_range: Tuple[int, int]
) -> List[Dict]:
    """비디오 데이터 처리 및 필터링."""
    now = datetime.now()
    processed = []
    
    for item in video_items:
        try:
            vid = item["id"]
            snippet = item["snippet"]
            stats = item.get("statistics", {})
            channel_id = snippet["channelId"]
            
            # 기본 통계
            view_count = int(stats.get("viewCount", 0))
            comment_count = int(stats.get("commentCount", 0))
            like_count = int(stats.get("likeCount", 0))
            subscriber_count = subs_map.get(channel_id, 0)
            
            # 성과도 계산 (division by zero 방지)
            performance = (view_count / subscriber_count * 100) if subscriber_count > 0 else 0
            
            # 등급 계산
            grade = calculate_grade(performance)
            
            # 등급 필터링
            if not any(g in grade for g in filter_grade):
                continue
            
            # 구독자 범위 필터링
            if not (subs_range[0] <= subscriber_count <= subs_range[1]):
                continue
            
            # 게시일 및 일일 속도 계산
            published_at = datetime.strptime(snippet["publishedAt"][:10], "%Y-%m-%d")
            days_since = max((now - published_at).days, 1)  # 0일 방지
            daily_velocity = view_count / days_since
            
            # 참여도 계산
            engagement = (comment_count / view_count * 100) if view_count > 0 else 0
            
            processed.append({
                "vid": vid,
                "thumbnail": get_thumbnail_url(snippet["thumbnails"]),
                "title": snippet["title"],
                "channel": snippet["channelTitle"],
                "grade": grade,
                "duration": parse_duration(item["contentDetails"]["duration"]),
                "published_date": published_at,
                "total_videos": video_count_map.get(channel_id, 0),
                "view_count": view_count,
                "like_count": like_count,
                "comment_count": comment_count,
                "performance": performance,
                "engagement": engagement,
                "daily_velocity": daily_velocity,
            })
        except Exception as e:
            st.warning(f"영상 처리 중 오류 (ID: {item.get('id', 'unknown')}): {e}")
            continue
    
    # 성과도와 날짜 기준으로 정렬
    return sorted(processed, key=lambda x: (x["performance"], x["published_date"]), reverse=True)


def create_display_dataframe(processed_data: List[Dict]) -> pd.DataFrame:
    """표시용 데이터프레임 생성."""
    display_data = []
    
    for i, item in enumerate(processed_data):
        display_data.append({
            "No": i + 1,
            "썸네일": item["thumbnail"],
            "채널명": item["channel"],
            "제목": item["title"],
            "게시일": item["published_date"].strftime("%Y/%m/%d"),
            "총 영상 수": f"{item['total_videos']:,}개",
            "조회수": format_number(item["view_count"]),
            "좋아요": format_number(item["like_count"]),
            "성과도": item["performance"],
            "등급": item["grade"],
            "길이": item["duration"],
            "일일 속도": f"{int(item['daily_velocity']):,}회",
            "이동": f"https://www.youtube.com/watch?v={item['vid']}",
            "ID": item["vid"],
            # 내부 계산용 RAW 값
            "raw_view": item["view_count"],
            "raw_perf": item["performance"],
            "raw_comment": item["comment_count"],
            "raw_like": item["like_count"],
            "raw_engagement": item["engagement"],
        })
    
    return pd.DataFrame(display_data)


# -------------------------------------------------------------------------
# 🔍 검색 함수
# -------------------------------------------------------------------------
def search_videos(
    api_key: str,
    query: str,
    max_results: int,
    days_filter: str,
    video_durations: List[str],
    country_options: List[str],
    filter_grade: List[str],
    subs_range: Tuple[int, int]
) -> Optional[pd.DataFrame]:
    """YouTube API를 사용하여 영상 검색 및 데이터 수집."""
    
    if not query.strip():
        st.warning("⚠️ 키워드를 입력해주세요!")
        return None
    
    try:
        youtube = build("youtube", "v3", developerKey=api_key)
        
        # 기간 필터
        published_after = get_published_after(days_filter)
        
        # 길이 필터
        api_duration = "any"
        if len(video_durations) == 1:
            api_duration = "short" if "쇼츠" in video_durations else "long"
        
        # 국가 필터
        target_regions = [REGION_MAP[c] for c in country_options if c != "🌏전체"]
        if "🌏전체" in country_options or not target_regions:
            target_regions = [None]
        
        all_video_ids = []
        
        with st.spinner(f"📡 '{query}' 신호 분석 중..."):
            # 단계 1: 검색
            progress_text = st.empty()
            progress_text.text("1/3 단계: 영상 검색 중...")
            
            for region_code in target_regions:
                per_region_max = min(50, max(10, max_results // len(target_regions)))
                
                params = {
                    "part": "snippet",
                    "q": query,
                    "maxResults": per_region_max,
                    "order": "viewCount",
                    "type": "video",
                    "videoDuration": api_duration,
                }
                
                if published_after:
                    params["publishedAfter"] = published_after
                if region_code:
                    params["regionCode"] = region_code
                
                try:
                    search_response = youtube.search().list(**params).execute()
                    video_ids = [item["id"]["videoId"] for item in search_response.get("items", [])]
                    all_video_ids.extend(video_ids)
                except HttpError as e:
                    if e.resp.status == 403:
                        st.error("🔑 API 쿼터가 초과되었습니다. 내일 다시 시도해주세요.")
                        return None
                    else:
                        st.error(f"검색 실패: {e}")
                        return None
            
            # 중복 제거
            all_video_ids = list(set(all_video_ids))
            
            if not all_video_ids:
                st.error("🔍 검색 결과가 없습니다. 다른 키워드를 시도해보세요.")
                return None
            
            progress_text.text(f"2/3 단계: {len(all_video_ids)}개 영상 정보 수집 중...")
            
            # 단계 2: 비디오 상세 정보
            video_items = []
            for i in range(0, len(all_video_ids), 50):
                chunk = all_video_ids[i:i + 50]
                try:
                    response = youtube.videos().list(
                        part="statistics,snippet,contentDetails",
                        id=",".join(chunk)
                    ).execute()
                    video_items.extend(response.get("items", []))
                except HttpError as e:
                    st.warning(f"일부 영상 정보 조회 실패: {e}")
            
            if not video_items:
                st.error("영상 상세 정보를 가져올 수 없습니다.")
                return None
            
            progress_text.text("3/3 단계: 채널 정보 수집 및 분석 중...")
            
            # 단계 3: 채널 정보
            channel_ids = list(set([item["snippet"]["channelId"] for item in video_items]))
            subs_map, video_count_map = fetch_channel_statistics(youtube, channel_ids)
            
            # 데이터 처리
            processed = process_video_data(
                video_items, subs_map, video_count_map, filter_grade, subs_range
            )
            
            progress_text.empty()
            
            if not processed:
                st.warning("⚠️ 필터 조건에 맞는 영상이 없습니다.")
                return pd.DataFrame()
            
            return create_display_dataframe(processed)
    
    except HttpError as e:
        if e.resp.status == 403:
            st.error("🔑 API 키가 유효하지 않거나 쿼터가 초과되었습니다.")
        elif e.resp.status == 400:
            st.error("❌ 잘못된 요청입니다. 검색 조건을 확인해주세요.")
        else:
            st.error(f"API 오류: {e}")
        return None
    except Exception as e:
        st.error(f"예상치 못한 오류 발생: {e}")
        return None


# -------------------------------------------------------------------------
# 상태 초기화
# -------------------------------------------------------------------------
if "df_result" not in st.session_state:
    st.session_state.df_result = None
if "selected_index" not in st.session_state:
    st.session_state.selected_index = 0

api_key = st.secrets.get("YOUTUBE_API_KEY", None)

# -------------------------------------------------------------------------
# ▶ 사이드바 (PREVIEW + 검색폼)
# -------------------------------------------------------------------------
with st.sidebar:
    preview_container = st.container()
    st.markdown("---")
    
    st.markdown("### 🔍 검색 조건")
    
    with st.form(key="search_form"):
        if not api_key:
            api_key = st.text_input("API 키 입력", type="password")
        
        # 1행: 키워드 + 버튼
        c1, c2 = st.columns([4, 1])
        with c1:
            query = st.text_input("키워드", placeholder="키워드 입력")
        with c2:
            search_button = st.form_submit_button("🚀", use_container_width=True)
        
        # 2행: 수집 / 기간
        c3, c4 = st.columns(2)
        with c3:
            max_results = st.selectbox("수집", [10, 30, 50, 100], index=1)
        with c4:
            days_filter = st.selectbox("기간", ["1주일", "1개월", "3개월", "전체"], index=1)
        
        st.caption("국가")
        country_options = st.pills(
            "국가",
            ["🔵한국", "🔴일본", "🟢미국", "🌏전체"],
            default=["🔵한국"],
            selection_mode="multi",
            label_visibility="collapsed",
        )
        
        st.caption("길이")
        video_durations = st.pills(
            "길이",
            ["쇼츠", "롱폼"],
            default=["쇼츠"],
            selection_mode="multi",
            label_visibility="collapsed",
        )
        
        st.caption("등급 필터")
        filter_grade = st.pills(
            "등급",
            ["🚀 떡상중", "📈 급상승", "👀 주목", "💤 일반"],
            default=["🚀 떡상중", "📈 급상승", "👀 주목"],
            selection_mode="multi",
            label_visibility="collapsed",
        )
        
        st.caption("구독자 범위")
        subs_range = st.slider(
            "구독자",
            0,
            1_000_000,
            (0, 1_000_000),
            1000,
            label_visibility="collapsed",
        )
    
    # 검색 실행
    if search_button:
        if not api_key:
            st.error("🔑 API 키가 설정되지 않았습니다.")
        else:
            result_df = search_videos(
                api_key, query, max_results, days_filter,
                video_durations, country_options, filter_grade, subs_range
            )
            
            if result_df is not None:
                st.session_state.df_result = result_df
                st.session_state.selected_index = 0
                st.success(f"✅ {len(result_df)}개 영상을 찾았습니다!")
    
    # PREVIEW 렌더링
    with preview_container:
        df = st.session_state.df_result
        
        if df is None or df.empty:
            st.info("테이블에서 영상을 선택하거나 검색을 실행하면 여기 미리보기가 표시됩니다.")
        else:
            idx = st.session_state.get("selected_index", 0)
            if idx >= len(df):
                idx = 0
                st.session_state.selected_index = 0
            
            selected_row = df.iloc[idx]
            
            st.markdown(
                f"""
                <h2 style="
                    margin: 4px 0 12px 0;
                    color: #7DF9FF;
                    line-height: 1.4;
                    font-weight: 700;
                    text-align: center;
                    text-shadow:
                        0 0 6px rgba(56, 189, 248, 0.9),
                        0 0 14px rgba(56, 189, 248, 0.8),
                        0 0 24px rgba(56, 189, 248, 0.7);
                ">
                    {selected_row['제목']}
                </h2>
                """,
                unsafe_allow_html=True,
            )
            
            summary_html = f"""
            <div class="summary-bar">
                <div class="summary-left">
                    <span>📺 <b>{selected_row['채널명']}</b></span>
                    <span>· 총 {selected_row['총 영상 수']}</span>
                    <span>· 📅 {selected_row['게시일']}</span>
                </div>
                <div class="summary-right">
                    <span class="chip chip-hot">🔥 {selected_row['raw_perf']:,.0f}%</span>
                    <span class="chip chip-view">👁 {selected_row['조회수']}</span>
                    <span class="chip chip-like">👍 {selected_row['좋아요']}</span>
                    <span class="chip chip-eng">💬 {float(selected_row['raw_engagement']):.2f}%</span>
                    <a class="summary-link" href="{selected_row['이동']}" target="_blank">유튜브에서 보기</a>
                </div>
            </div>
            """
            st.markdown(summary_html, unsafe_allow_html=True)
            
            youtube_embed = f"https://www.youtube.com/embed/{selected_row['ID']}"
            st.markdown(
                f"""
                <div class="video-wrapper">
                    <iframe
                        src="{youtube_embed}"
                        frameborder="0"
                        allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
                        allowfullscreen>
                    </iframe>
                </div>
                """,
                unsafe_allow_html=True,
            )

# -------------------------------------------------------------------------
# ▶ 메인 영역: 테이블
# -------------------------------------------------------------------------
df = st.session_state.df_result

st.markdown("### 📊 전체 영상 리스트")

if df is None or df.empty:
    st.info("검색 결과가 없습니다. 사이드바에서 검색을 실행해주세요.")
else:
    max_perf = df["raw_perf"].max() if len(df) > 0 and not df["raw_perf"].isna().all() else 1000
    if max_perf == 0:
        max_perf = 1000
    
    selected = st.dataframe(
        df,
        height=700,
        use_container_width=True,
        selection_mode="single-row",
        on_select="rerun",
        hide_index=True,
        column_order=[
            "No", "썸네일", "채널명", "제목", "게시일", "총 영상 수",
            "조회수", "좋아요", "성과도", "등급", "길이", "일일 속도", "이동"
        ],
        column_config={
            "No": st.column_config.TextColumn("No", width=40),
            "썸네일": st.column_config.ImageColumn("썸네일", width=80),
            "채널명": st.column_config.TextColumn("채널명", width=140),
            "제목": st.column_config.TextColumn("제목", width=320),
            "게시일": st.column_config.TextColumn("게시일", width=90),
            "총 영상 수": st.column_config.TextColumn("총 영상 수", width=90),
            "조회수": st.column_config.TextColumn("조회수", width=100),
            "좋아요": st.column_config.TextColumn("좋아요", width=90),
            "성과도": st.column_config.ProgressColumn(
                "성과도",
                format="%.0f%%",
                min_value=0,
                max_value=max_perf,
                width=110,
            ),
            "등급": st.column_config.TextColumn("등급", width=90),
            "길이": st.column_config.TextColumn("길이", width=70),
            "일일 속도": st.column_config.TextColumn("일일 속도", width=110),
            "이동": st.column_config.LinkColumn("이동", display_text="▶", width=50),
            # 내부 컬럼 숨김
            "ID": None,
            "raw_view": None,
            "raw_perf": None,
            "raw_comment": None,
            "raw_like": None,
            "raw_engagement": None,
        },
    )
    
    if selected.selection.rows:
        st.session_state.selected_index = selected.selection.rows[0]
