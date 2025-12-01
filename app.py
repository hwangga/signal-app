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
# -------------------------------------------------------------------------
CATEGORY_MAP = {
    "전체": None, "영화/애니": "1", "자동차": "2", "음악": "10",
    "동물": "15", "스포츠": "17", "여행/이벤트": "19", "게임": "20",
    "브이로그/인물": "22", "코미디": "23", "엔터테인먼트": "24",
    "뉴스/정치": "25", "하우투/스타일": "26", "교육": "27", "과학/기술": "28"
}
region_map = {"🔵한국": "KR", "🔴일본": "JP", "🟢미국": "US", "🌏전체": None}

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

    /* 사이드바 폭 */
    section[data-testid="stSidebar"] {
        min-width: 700px !important;
        max-width: 700px !important;
        background-color: #111827;
        border-right: 1px solid rgba(148, 163, 184, 0.3);
    }
    section[data-testid="stSidebar"] .block-container {
        padding-top: 0.8rem !important;
    }

    /* 입력/버튼 높이 통일 */
    div.stSelectbox > div,
    div.stTextInput > div,
    div.stFormSubmitButton > button {
        min-height: 40px !important;
    }
    input[type="text"] {
        min-height: 40px !important;
    }

    /* 검색 버튼 스타일 (pill에는 영향 X) */
    button[kind="primary"],
    button[data-testid="baseButton-primary"],
    div.stButton > button {
        background: linear-gradient(90deg, #00C6FF 0%, #0072FF 100%) !important;
        color: white !important;
        border: none !important;
        font-weight: 600 !important;
    }
    button[kind="primary"]:hover,
    button[data-testid="baseButton-primary"]:hover,
    div.stButton > button:hover {
        transform: scale(1.02) !important;
    }

    /* Pills 기본 모양 (비선택) */
    div[data-testid="stPills"] button {
        border-radius: 999px !important;
        background-color: #020617 !important;
        border: 1px solid rgba(148, 163, 184, 0.5) !important;
        color: #e5e7eb !important;
        font-size: 12px !important;
        padding: 2px 12px !important;
        opacity: 0.6;
    }

    /* Pills 선택 상태 (확실히 밝게) */
    div[data-testid="stPills"] button[aria-pressed="true"] {
        background: linear-gradient(90deg, #00E5FF, #22D3EE) !important;
        color: #020617 !important;
        font-weight: 700 !important;
        border: 1px solid #22D3EE !important;
        box-shadow: 0 0 10px rgba(34, 211, 238, 0.8) !important;
        opacity: 1;
    }

    /* 슬라이더 색 */
    div[data-baseweb="slider"] > div {
        background-color: rgba(15, 23, 42, 0.9) !important;  /* 트랙 */
    }
    div[data-baseweb="slider"] div[role="slider"] {
        background-color: #00E5FF !important;
        border: 2px solid #e0faff !important;
    }

    /* 검색 카드 스타일 */
    section[data-testid="stSidebar"] form[data-testid="stForm"] {
        padding: 12px 16px 18px 16px !important;
        border-radius: 16px !important;
        border: 1px solid rgba(148, 163, 184, 0.4) !important;
        background: radial-gradient(circle at top left, rgba(56,189,248,0.18), transparent 55%),
                    radial-gradient(circle at bottom right, rgba(59,130,246,0.20), transparent 55%),
                    #020617;
    }

    /* PREVIEW 요약줄 */
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

    /* 영상 미리보기 */
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
# 함수 정의
# -------------------------------------------------------------------------
def parse_duration(d: str) -> str:
    try:
        dur = isodate.parse_duration(d)
        sec = int(dur.total_seconds())
        m, s = divmod(sec, 60)
        h, m = divmod(m, 60)
        return f"{h}:{m:02}:{s:02}" if h else f"{m}:{s:02}"
    except Exception:
        return d

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
            search_trigger = st.form_submit_button("🚀", use_container_width=True, type="primary")

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

    # ---------------- 검색 로직 ----------------
    now = datetime.now()

    if "search_trigger" in locals() and search_trigger:
        if not query:
            st.warning("⚠️ 키워드를 입력해주세요!")
        elif not api_key:
            st.error("🔑 API 키가 설정되지 않았습니다.")
        else:
            try:
                youtube = build("youtube", "v3", developerKey=api_key)

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
                    api_duration = "short" if "쇼츠" in video_durations else "long"

                all_video_ids = []

                with st.spinner(f"📡 '{query}' 신호 분석 중..."):
                    target_countries = [
                        region_map[c] for c in country_options if c != "🌏전체"
                    ]
                    if "🌏전체" in country_options:
                        target_countries.append(None)
                    if not target_countries:
                        target_countries = [None]

                    for region_code in target_countries:
                        per_country_max = min(
                            50, max(10, int(max_results / len(target_countries)))
                        )

                        params = {
                            "part": "snippet",
                            "q": query,
                            "maxResults": per_country_max,
                            "order": "viewCount",
                            "type": "video",
                            "videoDuration": api_duration,
                        }
                        if published_after:
                            params["publishedAfter"] = published_after
                        if region_code:
                            params["regionCode"] = region_code

                        search_res = youtube.search().list(**params).execute()
                        all_video_ids.extend(
                            [item["id"]["videoId"] for item in search_res.get("items", [])]
                        )

                    all_video_ids = list(set(all_video_ids))

                    if not all_video_ids:
                        st.error("신호 없음 (검색 결과 0건)")
                        st.session_state.df_result = pd.DataFrame()
                    else:
                        video_items = []
                        chunks = [
                            all_video_ids[i: i + 50]
                            for i in range(0, len(all_video_ids), 50)
                        ]
                        for c in chunks:
                            res = youtube.videos().list(
                                part="statistics,snippet,contentDetails",
                                id=",".join(c),
                            ).execute()
                            video_items.extend(res.get("items", []))

                        channel_ids = list(
                            set([item["snippet"]["channelId"] for item in video_items])
                        )
                        subs_map, video_count_map = {}, {}

                        ch_chunks = [
                            channel_ids[i: i + 50]
                            for i in range(0, len(channel_ids), 50)
                        ]
                        for cc in ch_chunks:
                            cres = youtube.channels().list(
                                part="statistics", id=",".join(cc)
                            ).execute()
                            for ch in cres.get("items", []):
                                stats = ch.get("statistics", {})
                                subs_map[ch["id"]] = int(stats.get("subscriberCount", 0))
                                video_count_map[ch["id"]] = int(stats.get("videoCount", 0))

                        lst = []
                        for item in video_items:
                            vid = item["id"]
                            snippet = item["snippet"]
                            stats = item.get("statistics", {})
                            channel_id = snippet["channelId"]

                            view = int(stats.get("viewCount", 0))
                            comment = int(stats.get("commentCount", 0))
                            like_count = int(stats.get("likeCount", 0))
                            subs = subs_map.get(channel_id, 0)
                            perf = (view / subs * 100) if subs else 0

                            if perf >= 1000:
                                grade = "🚀 떡상중"
                            elif perf >= 300:
                                grade = "📈 급상승"
                            elif perf >= 100:
                                grade = "👀 주목"
                            else:
                                grade = "💤 일반"

                            if not any(g in grade for g in filter_grade):
                                continue

                            if not (subs_range[0] <= subs <= subs_range[1]):
                                continue

                            raw_date = datetime.strptime(
                                snippet["publishedAt"][:10], "%Y-%m-%d"
                            )
                            days = (now - raw_date).days
                            velocity = view / (days if days else 1)

                            thumbnails = snippet["thumbnails"]
                            thumb = thumbnails.get(
                                "maxres",
                                thumbnails.get(
                                    "standard",
                                    thumbnails.get("high", thumbnails.get("medium")),
                                ),
                            )["url"]

                            lst.append(
                                {
                                    "raw_perf": perf,
                                    "raw_view": view,
                                    "raw_comment": comment,
                                    "raw_like": like_count,
                                    "raw_engagement": (comment / view * 100)
                                    if view
                                    else 0,
                                    "raw_date": raw_date,
                                    "thumbnail": thumb,
                                    "title": snippet["title"],
                                    "channel": snippet["channelTitle"],
                                    "grade": grade,
                                    "duration": parse_duration(
                                        item["contentDetails"]["duration"]
                                    ),
                                    "vid": vid,
                                    "총 영상 수": video_count_map.get(channel_id, 0),
                                    "일일 속도": velocity,
                                    "게시일": raw_date.strftime("%Y/%m/%d"),
                                }
                            )

                        lst = sorted(
                            lst, key=lambda x: (x["raw_perf"], x["raw_date"]), reverse=True
                        )

                        display = []
                        for i, r in enumerate(lst):
                            display.append(
                                {
                                    "No": i + 1,
                                    "썸네일": r["thumbnail"],
                                    "채널명": r["channel"],
                                    "제목": r["title"],
                                    "게시일": r["게시일"],
                                    "총 영상 수": f"{r['총 영상 수']:,}개",
                                    "조회수": f"{r['raw_view']:,}",
                                    "성과도": r["raw_perf"],
                                    "등급": r["grade"],
                                    "길이": r["duration"],
                                    "일일 속도": f"{int(r['일일 속도']):,}회",
                                    "이동": f"https://www.youtube.com/watch?v={r['vid']}",
                                    "ID": r["vid"],
                                    "raw_view": r["raw_view"],
                                    "raw_perf": r["raw_perf"],
                                    "raw_comment": r["raw_comment"],
                                    "raw_like": r["raw_like"],
                                    "raw_engagement": r["raw_engagement"],
                                }
                            )

                        st.session_state.df_result = pd.DataFrame(display)
                        st.session_state.selected_index = 0

            except Exception as e:
                st.error(f"에러 발생: {e}")

    # ---------------- PREVIEW 렌더링 ----------------
    with preview_container:
        df = st.session_state.df_result
        selected_row = None

        if df is not None and not df.empty:
            idx = st.session_state.get("selected_index", 0)
            if idx is None or idx >= len(df):
                idx = 0
                st.session_state.selected_index = 0
            selected_row = df.iloc[idx]

        if selected_row is None:
            st.info("테이블에서 영상을 선택하거나 검색을 실행하면 여기 미리보기가 표시됩니다.")
        else:
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

            channel_name = selected_row["채널명"]
            total_videos = selected_row["총 영상 수"]
            published = selected_row["게시일"]
            perf_str = f"{selected_row['raw_perf']:,.0f}%"
            views_str = f"{selected_row['raw_view']:,}"
            eng_str = f"{float(selected_row['raw_engagement']):.2f}%"
            likes_str = f"{int(selected_row['raw_like']):,}"
            url = selected_row["이동"]

            summary_html = f"""
            <div class="summary-bar">
                <div class="summary-left">
                    <span>📺 <b>{channel_name}</b></span>
                    <span>· 총 {total_videos}</span>
                    <span>· 📅 {published}</span>
                </div>
                <div class="summary-right">
                    <span class="chip chip-hot">🔥 {perf_str}</span>
                    <span class="chip chip-view">👁 {views_str}</span>
                    <span class="chip chip-like">👍 {likes_str}</span>
                    <span class="chip chip-eng">💬 {eng_str}</span>
                    <a class="summary-link" href="{url}" target="_blank">유튜브에서 보기</a>
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
    if "좋아요" not in df.columns and "raw_like" in df.columns:
        df["좋아요"] = df["raw_like"].apply(lambda x: f"{int(x):,}")

    max_perf = df["raw_perf"].max() if len(df) > 0 else 1000
    if max_perf == 0 or pd.isna(max_perf):
        max_perf = 1000

    selected = st.dataframe(
        df,
        height=1100,  # 🔥 50개 가까이까지 넉넉히 보이도록 높이 확대
        use_container_width=True,
        selection_mode="single-row",
        on_select="rerun",
        hide_index=True,
        column_order=[
            "No",
            "썸네일",
            "채널명",
            "제목",
            "게시일",
            "총 영상 수",
            "조회수",
            "좋아요",
            "성과도",
            "등급",
            "길이",
            "일일 속도",
            "이동",
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
            "이동": st.column_config.LinkColumn(
                "이동", display_text="▶", width=50
            ),
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
