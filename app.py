import streamlit as st
from googleapiclient.discovery import build
from datetime import datetime, timedelta
import isodate
import pandas as pd
from youtube_transcript_api import YouTubeTranscriptApi # ⭐ 자막 추출 라이브러리

# ==========================================
# 🔐 API 키는 Streamlit Cloud의 'Secrets'에서 가져옵니다.
# ==========================================

st.set_page_config(page_title="SIGNAL - Insight", layout="wide", page_icon="📡")

# -------------------------------------------------------------------------
# ⭐ [데이터 정의] 유튜브 카테고리 매핑 테이블
# -------------------------------------------------------------------------
CATEGORY_MAP = {
    "전체": None, "영화/애니": "1", "자동차": "2", "음악": "10", 
    "동물": "15", "스포츠": "17", "여행/이벤트": "19", "게임": "20", 
    "브이로그/인물": "22", "코미디": "23", "엔터테인먼트": "24", 
    "뉴스/정치": "25", "하우투/스타일": "26", "교육": "27", "과학/기술": "28"
}
# -------------------------------------------------------------------------

# 🌑 [스타일링: Red Killer V7]
st.markdown("""
<style>
    /* 전체 테마 및 레이아웃 설정 (이전과 동일) */
    .stApp { background-color: #0E1117; color: #FAFAFA; }
    section[data-testid="stSidebar"] { min-width: 450px !important; background-color: #1A1C24; text-align: center; }
    [data-testid="stSidebar"] .block-container { padding-top: 5rem !important; }
    
    /* 버튼, 슬라이더, Pills 색상 강제 민트색 */
    button[kind="primary"], a[kind="primary"] { background: linear-gradient(90deg, #00C6FF 0%, #0072FF 100%) !important; color: white !important; }
    button[kind="primary"]:hover, a[kind="primary"]:hover { transform: scale(1.02) !important; box-shadow: 0 6px 12px rgba(0, 198, 255, 0.5) !important; }
    div[data-testid="stPills"] button[aria-pressed="true"] { background-color: #00E5FF !important; color: black !important; }
    div[data-testid="stSlider"] div[data-baseweb="slider"] div { background-color: #00E5FF !important; }
    
    /* 기타 스타일 */
    th { background-color: #162447 !important; color: white !important; text-align: center !important; }
    td { vertical-align: middle !important; text-align: center !important; font-size: 13px !important; }
    [data-testid="stMetricValue"] { font-size: 24px !important; color: #00E5FF !important; font-weight: 700 !important; }
</style>
""", unsafe_allow_html=True)

# ⭐ [타이틀]
st.title("📡 SIGNAL : Insight")

# -------------------------------------------------------------------------
# 함수 정의
# -------------------------------------------------------------------------

def get_video_transcript(video_id):
    """자막을 가져오고 오류 처리 (새 기능)"""
    try:
        transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
        
        # 한국어 또는 영어, 없으면 자동 생성된 자막이라도 가져오기 시도
        try:
            transcript = transcript_list.find_transcript(['ko', 'en'])
        except:
            transcript = transcript_list.find_generated_transcript(['ko', 'en'])
            
        full_text = " ".join([t['text'] for t in transcript.fetch()])
        return full_text
    except Exception as e:
        return "⚠️ 자막이 없거나 가져올 수 없는 영상입니다."

def parse_duration(d):
    try:
        dur = isodate.parse_duration(d)
        sec = int(dur.total_seconds())
        m, s = divmod(sec, 60)
        h, m = divmod(m, 60)
        return f"{h}:{m:02}:{s:02}" if h else f"{m}:{s:02}"
    except: return d

# -------------------------------------------------------------------------
# 1. 상단 (Top) 검색창 - [새 필터 추가]
# -------------------------------------------------------------------------
api_key = st.secrets.get("YOUTUBE_API_KEY", None)
if 'df_result' not in st.session_state: st.session_state.df_result = None

with st.form(key='search_form'):
    if not api_key:
        api_key = st.text_input("API 키 입력", type="password")

    # 1행: 키워드(짧게) + 검색버튼 + 수집 + 기간 + 국가
    c1, c2, c3, c4, c5 = st.columns([1.5, 0.5, 0.7, 0.8, 1.5], vertical_alignment="bottom")
    with c1: query = st.text_input("키워드", placeholder="키워드 입력")
    with c2: search_trigger = st.form_submit_button("🚀", type="primary", use_container_width=True)
    with c3: max_results = st.selectbox("수집수", [10, 30, 50, 100], index=1)
    with c4: days_filter = st.selectbox("기간", ["1주일", "1개월", "3개월", "전체"], index=1)
    with c5: 
        st.caption("국가")
        country_options = st.pills("국가", ["🇰🇷", "🇯🇵", "🇺🇸", "🌏"], default=["🇰🇷"], selection_mode="multi", label_visibility="collapsed")

    # 2행: 길이 | 등급 | 카테고리 | 구독자
    c6, c7, c8, c9 = st.columns([1.2, 1.8, 2, 2], vertical_alignment="center")
    
    with c6:
        st.caption("길이")
        video_durations = st.pills("길이", ["쇼츠", "롱폼"], default=["쇼츠"], selection_mode="multi", label_visibility="collapsed")
    with c7: 
        st.caption("등급 필터")
        filter_grade = st.pills("등급", 
                                ["🚀 떡상중", "📈 급상승", "👀 주목", "💤 일반"], 
                                default=["🚀 떡상중", "📈 급상승", "👀 주목"],
                                selection_mode="multi", label_visibility="collapsed")
    with c8:
        # ⭐ [새 기능] 카테고리 필터 추가
        st.caption("주제 (카테고리)")
        category_options = list(CATEGORY_MAP.keys())
        category_name = st.selectbox("카테고리", category_options, index=0, label_visibility="collapsed")
        category_id = CATEGORY_MAP.get(category_name)

    with c9:
        st.caption("구독자 범위")
        subs_range = st.slider("구독자", 0, 1000000, (0, 1000000), 1000, label_visibility="collapsed")

    # 3행: 고급 필터
    st.markdown("<br>", unsafe_allow_html=True)
    age_filter_col, _ = st.columns([1, 4])
    with age_filter_col:
        age_filter = st.checkbox("연령 제한 콘텐츠 제외", value=True, help="유튜브의 연령 제한 콘텐츠(ytRating)를 자동으로 검색 결과에서 제외합니다.")


# -------------------------------------------------------------------------
# 2. 로직 및 API 호출
# -------------------------------------------------------------------------
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
                    per_country_max = min(50, max(10, int(max_results / len(target_countries)))) if target_countries else max_results
                    
                    search_request = youtube.search().list(
                        part="snippet", q=query, maxResults=per_country_max, order="viewCount", type="video", 
                        videoDuration=api_duration, publishedAfter=published_after, regionCode=region_code,
                        videoCategoryId=category_id # ⭐ [필터 적용] 카테고리 ID 적용
                    )
                    search_response = search_request.execute()
                    all_video_ids.extend([item['id']['videoId'] for item in search_response['items']])

                all_video_ids = list(set(all_video_ids))

                if not all_video_ids: 
                    st.error("신호 없음 (검색 결과 0건)")
                    st.session_state.df_result = pd.DataFrame()
                else:
                    # 상세 정보 수집 (contentDetails 포함)
                    video_request = youtube.videos().list(part="statistics, snippet, contentDetails", id=','.join(all_video_ids))
                    video_response = video_request.execute()
                    
                    # 채널 정보 수집 (Total Video Count 포함)
                    channel_ids = list(set([item['snippet']['channelId'] for item in video_response['items']]))
                    channel_chunks = [channel_ids[i:i + 50] for i in range(0, len(channel_ids), 50)]
                    subs_map = {}
                    video_count_map = {}
                    
                    for chunk in channel_chunks:
                        channel_request = youtube.channels().list(part="statistics", id=','.join(chunk))
                        channel_response = youtube.channels().list(part="statistics", id=','.join(chunk)).execute()
                        for item in channel_response['items']:
                            subs_map[item['id']] = int(item['statistics'].get('subscriberCount', 0))
                            video_count_map[item['id']] = int(item['statistics'].get('videoCount', 0)) # ⭐ [새 지표] 총 영상 수

                    raw_data_list = []
                    for item in video_response['items']:
                        # ⭐ [필터] 연령 제한 필터링
                        if age_filter and item['contentDetails'].get('contentRating', {}).get('ytRating') in ['ytAgeRestricted']:
                             continue

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
                            if grade_simple in f: pass_grade = True; break
                        if not pass_grade: continue

                        raw_date = datetime.strptime(item['snippet']['publishedAt'][:10], "%Y-%m-%d")
                        
                        raw_data_list.append({
                            "raw_perf": perf, "raw_date": raw_date, "raw_view": view_count, "raw_sub": sub_count, 
                            "thumbnail": thumb, "title": item['snippet']['title'], "channel": item['snippet']['channelTitle'],
                            "grade": grade, "duration": parse_duration(item['contentDetails']['duration']), "vid": vid,
                            "총 영상 수": video_count_map.get(item['snippet']['channelId'], 0), # ⭐ [새 지표]
                            "일일 속도": view_count / ((datetime.now() - raw_date).days if (datetime.now() - raw_date).days else 1),
                        })
                    
                    sorted_list = sorted(raw_data_list, key=lambda x: (x['raw_perf'], x['raw_date']), reverse=True)
                    
                    display_data = []
                    for i, row in enumerate(sorted_list):
                        display_data.append({
                            "No": str(i + 1), "썸네일": row['thumbnail'], "채널명": row['channel'], "제목": row['title'],
                            "게시일": row['raw_date'].strftime("%Y/%m/%d"), 
                            "총 영상 수": f"{row['총 영상 수']:,}개", # ⭐ [표시]
                            "구독자": f"{row['raw_sub']:,}", "조회수": f"{row['raw_view']:,}",
                            "성과도": row['raw_perf'], "등급": row['grade'], "길이": row['duration'],
                            "일일 속도": f"{int(row['일일 속도']):,}회", # ⭐ [표시]
                            "이동": f"https://www.youtube.com/watch?v={row['vid']}", "ID": row['vid'],
                            "raw_perf": row['raw_perf'], "raw_view": row['raw_view']
                        })

                    st.session_state.df_result = pd.DataFrame(display_data)

        except Exception as e: st.error(f"에러 발생: {e}")

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

if st.session_state.df_result is not None:
    df = st.session_state.df_result
    st.success(f"신호 포착 완료! {len(df)}건")
    
    max_perf_val = df['raw_perf'].max()
    if max_perf_val == 0 or pd.isna(max_perf_val): max_perf_val = 1000

    selection = st.dataframe(
        df,
        column_order=("No", "썸네일", "채널명", "제목", "게시일", "총 영상 수", "구독자", "조회수", "성과도", "등급", "일일 속도", "길이", "이동"),
        column_config={
            "No": st.column_config.TextColumn("No", width=40),
            "썸네일": st.column_config.ImageColumn("썸네일", width=70),
            "채널명": st.column_config.TextColumn("채널명", width=120),
            "제목": st.column_config.TextColumn("제목", width=250),
            "게시일": st.column_config.TextColumn("게시일", width=80),
            "총 영상 수": st.column_config.TextColumn("총 영상 수", width=80), # ⭐ [새 컬럼]
            "구독자": st.column_config.TextColumn("구독자", width=80),
            "조회수": st.column_config.TextColumn("조회수", width=80),
            "성과도": st.column_config.ProgressColumn("성과도", format="%.0f%%", min_value=0, max_value=max_perf_val, width=80),
            "등급": st.column_config.TextColumn("등급", width=90),
            "일일 속도": st.column_config.TextColumn("일일 속도", width=80), # ⭐ [새 컬럼]
            "길이": st.column_config.TextColumn("길이", width=60),
            "이동": st.column_config.LinkColumn("이동", display_text="▶", width=40),
            "ID": None, "raw_perf": None, "raw_view": None
        },
        hide_index=True, use_container_width=True, height=700, 
        on_select="rerun", selection_mode="single-row"
    )

    selected_row = None
    if selection.selection.rows:
        selected_row = df.iloc[selection.selection.rows[0]]
    elif not df.empty:
        selected_row = df.iloc[0]

    if selected_row is not None:
        vid_id = selected_row['ID']
        
        with preview_container:
            # ⭐ [네온 타이틀]
            st.markdown(f"""
                <div style='padding: 10px 0; border-bottom: 1px solid rgba(255,255,255,0.1); margin-bottom: 15px;'>
                    <h4 style='margin:0; color: #00E5FF; text-shadow: 0 0 10px rgba(0, 229, 255, 0.6); line-height: 1.4; font-size: 18px;'>
                        {selected_row['제목']}
                    </h4>
                </div>
            """, unsafe_allow_html=True)
            
            # 영상 플레이어
            st.video(f"https://www.youtube.com/watch?v={vid_id}")
            
            st.markdown("---")
            # ⭐ [새 기능] 일일 속도 표시
            st.markdown(f"### ⏱️ 일일 평균 속도: {selected_row['일일 속도']}회")
            
            # 메타 정보
            c_meta1, c_meta2 = st.columns(2)
            with c_meta1: st.caption(f"📺 채널명: {selected_row['채널명']} (총 영상 {selected_row['총 영상 수']})")
            with c_meta2: st.caption(f"📅 게시날짜: {selected_row['게시일']}")
            
            # 핵심 지표
            c_stat1, c_stat2 = st.columns(2)
            with c_stat1: st.metric("성과도", f"{selected_row['raw_perf']:,.0f}%")
            with c_stat2: st.metric("조회수", f"{selected_row['raw_view']:,}")

            st.divider()
            
            # ⭐ [새 기능] 스크립트 추출
            with st.expander("📜 자막(스크립트) 추출 및 분석"):
                if st.button("텍스트 가져오기", key=f"btn_{vid_id}"):
                    with st.spinner("자막을 찾고 있습니다..."):
                        transcript_text = get_video_transcript(vid_id)
                        st.text_area("내용 복사해서 AI에게 요약시키세요!", transcript_text, height=300)
