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
# 🌑 [스타일링: PREVIEW 요약줄 + 모바일 대응 + 영상 축소]
# -------------------------------------------------------------------------
st.markdown("""
<style>
    .stApp { background-color: #0E1117; color: #FAFAFA; }

    /* 통일된 높이 */
    div.stSelectbox > div, 
    div.stTextInput > div, 
    div.stFormSubmitButton > button {
        min-height: 38px !important;
    }

    /* Primary 버튼 스타일 */
    button[kind="primary"], div.stButton > button, a[kind="primary"] {
        background: linear-gradient(90deg, #00C6FF 0%, #0072FF 100%) !important;
        color: white !important;
        border: none !important;
        font-weight: bold !important;
    }
    button[kind="primary"]:hover, a[kind="primary"]:hover {
        transform: scale(1.02) !important;
    }

    /* 요약줄 스타일 */
    .summary-bar {
        display: flex;
        flex-wrap: wrap;
        align-items: center;
        gap: 6px;
        padding: 6px 12px;
        margin-bottom: 12px;
        border-radius: 12px;
        background: rgba(30, 41, 59, 0.6);
        border: 1px solid rgba(148, 163, 184, 0.3);
        font-size: 13px;
    }
    .chip {
        padding: 2px 8px;
        border-radius: 999px;
        font-size: 12px;
        border: 1px solid rgba(148, 163, 184, 0.5);
        white-space: nowrap;
    }
    .chip-hot { border-color: #fb7185; }
    .chip-view { border-color: #60a5fa; }
    .chip-eng { border-color: #34d399; }

    /* 영상 크기 축소 */
    .video-wrapper iframe {
        width: 100%;
        height: 260px;
        border-radius: 12px;
    }

    /* 모바일 대응 */
    @media (max-width: 900px) {
        .summary-bar { font-size: 11px; padding: 6px 10px; }
        .video-wrapper iframe { height: 200px; }
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
if 'df_result' not in st.session_state:
    st.session_state.df_result = None
if 'selected_index' not in st.session_state:
    st.session_state.selected_index = 0

api_key = st.secrets.get("YOUTUBE_API_KEY", None)


# -------------------------------------------------------------------------
# 상단 50:50 레이아웃 (PREVIEW 좌 / SEARCH 우)
# -------------------------------------------------------------------------
preview_col, search_col = st.columns(2)


# -------------------------------------------------------------------------
# ▶ 검색 영역 (우측)
# -------------------------------------------------------------------------
with search_col:
    st.markdown("### 🔍 검색 조건")

    with st.form(key='search_form'):
        if not api_key:
            api_key = st.text_input("API 키 입력", type="password")

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
# ▶ 검색 로직
# -------------------------------------------------------------------------
now = datetime.now()

if search_trigger:
    if not query:
        st.warning("⚠️ 키워드를 입력해주세요!")
    elif not api_key:
        st.error("🔑 API 키가 설정되지 않았습니다.")
    else:
        try:
            youtube = build('youtube', 'v3', developerKey=api_key)

            # 기간 필터
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
                # 국가별 검색
                target_countries = [region_map[c] for c in country_options if c != "🌏전체"]
                if "🌏전체" in country_options:
                    target_countries.append(None)
                if not target_countries:
                    target_countries = [None]

                for region_code in target_countries:
                    per_country_max = min(50, max(10, int(max_results / len(target_countries))))

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
                    all_video_ids.extend([item['id']['videoId'] for item in search_res.get('items', [])])

                all_video_ids = list(set(all_video_ids))

                if not all_video_ids:
                    st.error("신호 없음 (검색 결과 0건)")
                    st.session_state.df_result = pd.DataFrame()
                else:
                    # ======================
                    # 1) 비디오 상세
                    # ======================
                    video_items = []
                    chunks = [all_video_ids[i:i+50] for i in range(0, len(all_video_ids), 50)]
                    for c in chunks:
                        res = youtube.videos().list(
                            part="statistics,snippet,contentDetails",
                            id=",".join(c)
                        ).execute()
                        video_items.extend(res.get('items', []))

                    # ======================
                    # 2) 채널 정보 (chunking)
                    # ======================
                    channel_ids = list(set([item['snippet']['channelId'] for item in video_items]))
                    subs_map, video_count_map = {}, {}

                    ch_chunks = [channel_ids[i:i+50] for i in range(0, len(channel_ids), 50)]
                    for cc in ch_chunks:
                        cres = youtube.channels().list(
                            part="statistics",
                            id=",".join(cc)
                        ).execute()
                        for ch in cres.get('items', []):
                            stats = ch.get("statistics", {})
                            subs_map[ch["id"]] = int(stats.get("subscriberCount", 0))
                            video_count_map[ch["id"]] = int(stats.get("videoCount", 0))

                    # ======================
                    # 3) 지표 계산
                    # ======================
                    lst = []
                    for item in video_items:
                        vid = item["id"]
                        snippet = item["snippet"]
                        stats = item.get("statistics", {})
                        channel_id = snippet["channelId"]

                        view = int(stats.get("viewCount", 0))
                        comment = int(stats.get("commentCount", 0))
                        like = int(stats.get("likeCount", 0))
                        subs = subs_map.get(channel_id, 0)
                        perf = (view / subs * 100) if subs else 0

                        # 등급 필터
                        if perf >= 1000: grade = "🚀 떡상중"
                        elif perf >= 300: grade = "📈 급상승"
                        elif perf >= 100: grade = "👀 주목"
                        else: grade = "💤 일반"

                        if not any(g in grade for g in filter_grade):
                            continue

                        # 구독자 필터
                        if not (subs_range[0] <= subs <= subs_range[1]):
                            continue

                        # 날짜
                        raw_date = datetime.strptime(snippet["publishedAt"][:10], "%Y-%m-%d")
                        days = (now - raw_date).days
                        velocity = view / (days if days else 1)

                        thumbnails = snippet["thumbnails"]
                        thumb = thumbnails.get("maxres",
                            thumbnails.get("standard",
                                thumbnails.get("high",
                                    thumbnails.get("medium"))))["url"]

                        lst.append({
                            "raw_perf": perf,
                            "raw_view": view,
                            "raw_comment": comment,
                            "raw_engagement": (comment/view*100) if view else 0,
                            "raw_date": raw_date,
                            "thumbnail": thumb,
                            "title": snippet["title"],
                            "channel": snippet["channelTitle"],
                            "grade": grade,
                            "duration": parse_duration(item["contentDetails"]["duration"]),
                            "vid": vid,
                            "총 영상 수": video_count_map.get(channel_id, 0),
                            "일일 속도": velocity,
                            "게시일": raw_date.strftime("%Y/%m/%d")
                        })

                    lst = sorted(lst, key=lambda x: (x["raw_perf"], x["raw_date"]), reverse=True)

                    display = []
                    for i, r in enumerate(lst):
                        display.append({
                            "No": i+1,
                            "썸네일": r["thumbnail"],
                            "채널명": r["channel"],
                            "제목": r["title"],
                            "게시일": r["게시일"],
                            "총 영상 수": f"{r['총 영상 수']:,}개",
                            "구독자": "",  # 필요시 추가
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
                            "raw_engagement": r["raw_engagement"]
                        })

                    st.session_state.df_result = pd.DataFrame(display)
                    st.session_state.selected_index = 0


        except Exception as e:
            st.error(f"에러 발생: {e}")


# -------------------------------------------------------------------------
# ▶ PREVIEW (좌측)
# -------------------------------------------------------------------------
with preview_col:
    st.markdown("""
    <div class="sidebar-logo">
        <h3 style='margin:0; color: white; font-size: 20px; text-shadow: 0 0 10px rgba(0, 229, 255, 0.6);'>
            🎬 PREVIEW
        </h3>
    </div>
    """, unsafe_allow_html=True)

    df = st.session_state.df_result
    selected_row = None

    if df is not None and not df.empty:
        if 0 <= st.session_state.selected_index < len(df):
            selected_row = df.iloc[st.session_state.selected_index]

    if selected_row is None:
        st.info("표에서 영상을 선택하면 여기에 미리보기가 표시됩니다.")
    else:
        # --------------------------
        # PREVIEW 제목
        # --------------------------
        st.markdown(f"""
            <h4 style='margin:0; color:#00E5FF; line-height:1.3;'>
                {selected_row['제목']}
            </h4>
        """, unsafe_allow_html=True)

               # --------------------------
        # 요약 바 (수정 버전)
        # --------------------------
        channel_name = selected_row["채널명"]
        total_videos = selected_row["총 영상 수"]
        published = selected_row["게시일"]
        perf = f"{selected_row['raw_perf']:,.0f}%"
        views = f"{selected_row['raw_view']:,}"
        engagement = f"{float(selected_row['raw_engagement']):.2f}%"

        summary_html = f"""
        <div class="summary-bar">
            <div style="display:flex; flex-wrap:wrap; gap:6px; align-items:center;">
                <span>📺 <b>{channel_name}</b></span>
                <span>· 총 {total_videos}</span>
                <span>· 📅 {published}</span>
            </div>
            <div style="display:flex; flex-wrap:wrap; gap:6px; margin-left:auto;">
                <span class="chip chip-hot">🔥 {perf}</span>
                <span class="chip chip-view">👁 {views}</span>
                <span class="chip chip-eng">💬 {engagement}</span>
            </div>
        </div>
        """

        st.markdown(summary_html, unsafe_allow_html=True)


        # --------------------------
        # 영상 (축소)
        # --------------------------
        youtube_embed = f"https://www.youtube.com/embed/{selected_row['ID']}"

        st.markdown(f"""
        <div class="video-wrapper">
            <iframe 
                src="{youtube_embed}" 
                frameborder="0"
                allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
                allowfullscreen>
            </iframe>
        </div>
        """, unsafe_allow_html=True)

        st.link_button(
            "🔗 유튜브에서 보기",
            selected_row["이동"],
            type="primary",
            use_container_width=True
        )


# -------------------------------------------------------------------------
# ▶ 테이블 (전체 리스트)
# -------------------------------------------------------------------------
st.markdown("---")
st.markdown("### 📊 전체 영상 리스트")

df = st.session_state.df_result

if df is None or df.empty:
    st.info("검색 결과가 없습니다.")
else:
    selected = st.dataframe(
        df,
        height=600,
        use_container_width=True,
        selection_mode="single-row",
        on_select="rerun",
        hide_index=True
    )

    if selected.selection.rows:
        st.session_state.selected_index = selected.selection.rows[0]
