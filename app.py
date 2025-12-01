import streamlit as st
from googleapiclient.discovery import build
from datetime import datetime, timedelta
import isodate
import pandas as pd

# ==========================================
# 🔐 API 키는 Streamlit Cloud의 'Secrets'에서 가져옵니다.
# ==========================================

st.set_page_config(page_title="SIGNAL - YouTube Hunter", layout="wide", page_icon="📡")

# 🌑 [스타일링: 딥 블루 & 레드 포인트 테마]
st.markdown("""
<style>
    /* 전체 배경 (더 깊은 어둠) */
    .stApp { background-color: #0a0e14; color: #e6e6e6; }

    /* =========================================
       ⭐ [왼쪽 사이드바] 딥 블루 그라데이션
    ========================================= */
    section[data-testid="stSidebar"] {
        min-width: 400px !important; /* 너비 적절히 조정 */
        background: linear-gradient(180deg, #0d1b2a 0%, #1b263b 100%); /* 깊은 바다색 */
        border-right: 1px solid #30475e;
    }
    
    /* 사이드바 내부 텍스트 색상 */
    [data-testid="stSidebar"] label, [data-testid="stSidebar"] .stMarkdown {
        color: #b0c4de !important; /* 밝은 회청색 */
    }

    /* =========================================
       ⭐ [검색 버튼] 강렬한 레드 포인트
    ========================================= */
    div.stButton > button:first-child[kind="primary"] {
        background: linear-gradient(90deg, #d90429 0%, #ef233c 100%); /* 강렬한 레드 */
        color: white;
        border: none;
        font-weight: bold;
        padding: 12px 24px;
        font-size: 16px;
        transition: 0.3s;
        box-shadow: 0 4px 15px rgba(217, 4, 41, 0.4);
    }
    div.stButton > button:first-child[kind="primary"]:hover {
        transform: scale(1.02);
        box-shadow: 0 6px 20px rgba(217, 4, 41, 0.6);
    }

    /* 필터 옵션 (라디오/멀티셀렉트) 차분하게 */
    .stRadio > div, .stMultiSelect > div {
        color: #b0c4de;
    }

    /* =========================================
       ⭐ [오른쪽 프리뷰 패널] 통일감 있는 디자인
    ========================================= */
    /* 헤더 박스 스타일 */
    .preview-header-box {
        background: linear-gradient(180deg, #0d1b2a 0%, #1b263b 100%); /* 왼쪽과 동일한 톤 */
        padding: 20px;
        border-radius: 12px 12px 0 0; /* 위쪽만 둥글게 */
        text-align: center;
        border: 1px solid #30475e;
        border-bottom: none;
        box-shadow: 0 -4px 10px rgba(0,0,0,0.2);
    }
    /* 내용 컨테이너 스타일 (헤더와 이어지는 느낌) */
    .preview-content-box {
        background-color: #121a26; /* 헤더보다 약간 어둡게 */
        padding: 20px;
        border-radius: 0 0 12px 12px; /* 아래쪽만 둥글게 */
        border: 1px solid #30475e;
        border-top: none;
        min-height: 600px; /* 최소 높이 확보로 균형 맞춤 */
    }

    /* =========================================
       공통 요소 스타일
    ========================================= */
    /* 테이블 스타일 */
    th { background-color: #162447 !important; color: #e6e6e6 !important; text-align: center !important; border-bottom: 2px solid #30475e !important;}
    td { vertical-align: middle !important; text-align: center !important; font-size: 15px !important; background-color: #0a0e14 !important; border-bottom: 1px solid #1f2a40 !important;}
    
    /* 링크 스타일 */
    a { text-decoration: none; color: #4cc9f0; font-weight: bold; } /* 밝은 하늘색 링크 */
    a:hover { color: #FFFFFF; text-decoration: underline; }
    
    /* 썸네일 이미지 둥글게 */
    img { border-radius: 8px; }

    /* 메트릭 숫자 색상 (밝은 하늘색 포인트) */
    [data-testid="stMetricValue"] { font-size: 28px !important; color: #4cc9f0 !important; font-weight: 700 !important; }
    [data-testid="stMetricLabel"] { font-size: 14px !important; color: #AAA !important; }
</style>
""", unsafe_allow_html=True)

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
# 레이아웃 구성 (사이드바 + 메인 패널)
# -------------------------------------------------------------------------
sidebar_col, main_col = st.columns([1, 3]) # 비율 조정

# =========================================================================
# 1. 왼쪽 사이드바 (검색 옵션)
# =========================================================================
with sidebar_col:
    with st.sidebar: # st.sidebar 컨텍스트 사용
        st.title("📡 SIGNAL Hunter")
        st.markdown("---")
        
        api_key = st.secrets.get("YOUTUBE_API_KEY", None)
        if not api_key:
            api_key = st.text_input("API 키 입력 (로컬 테스트용)", type="password")

        with st.form(key='search_form'):
            # ⭐ [텍스트 변경] 검색어 -> 키워드
            query = st.text_input("키워드", "")
            
            st.markdown("<br>", unsafe_allow_html=True) # 간격

            # 수집 설정
            st.subheader("⚙️ 수집 설정")
            c1, c2 = st.columns(2)
            with c1: max_results = st.selectbox("수집수", [10, 30, 50, 100], index=1)
            with c2: days_filter = st.selectbox("기간", ["1주일", "1개월", "3개월", "전체"], index=1)

            # 필터 설정
            st.markdown("<br>", unsafe_allow_html=True)
            st.subheader("🌪️ 필터 설정")
            
            country_option = st.selectbox("국가", ["🇰🇷 한국", "🇯🇵 일본", "🇺🇸 미국", "🌏 전세계"], index=0)
            region_map = {"🇰🇷 한국": "KR", "🇯🇵 일본": "JP", "🇺🇸 미국": "US", "🌏 전세계": None}
            region_code = region_map[country_option]
            
            video_duration = st.radio("영상 길이", ["쇼츠(1분 미만)", "롱폼(1분 이상)", "전체"], index=0)
            
            st.markdown("---")
            st.markdown("**🎯 등급 필터**")
            filter_grade = st.multiselect("등급 선택", ["🟣 S-Tier (전설)", "🔴 A-Tier (초대박)", "🟢 B-Tier (우수)", "⚪ Normal (일반)"], default=["🟣 S-Tier (전설)", "🔴 A-Tier (초대박)", "🟢 B-Tier (우수)"])
            
            st.markdown("**👥 구독자 범위**")
            subs_range = st.slider("범위 선택", 0, 2000000, (0, 1000000), 10000, help="너무 큰 대형 채널을 거를 때 유용합니다.")

            st.markdown("<br>", unsafe_allow_html=True)
            # ⭐ [레드 버튼]
            search_trigger = st.form_submit_button("🚀 SIGNAL 감지 시작", type="primary", use_container_width=True)


# =========================================================================
# 2. 메인 패널 (리스트 + 프리뷰)
# =========================================================================

# 로직 처리
if 'df_result' not in st.session_state: st.session_state.df_result = None

today = datetime.now()
if days_filter == "1주일": published_after = (today - timedelta(days=7)).isoformat("T") + "Z"
elif days_filter == "1개월": published_after = (today - timedelta(days=30)).isoformat("T") + "Z"
elif days_filter == "3개월": published_after = (today - timedelta(days=90)).isoformat("T") + "Z"
else: published_after = None

if video_duration == "쇼츠(1분 미만)": api_duration = "short"
elif video_duration == "롱폼(1분 이상)": api_duration = "long"
else: api_duration = "any"

if search_trigger:
    if not query:
        st.warning("⚠️ 키워드를 입력해주세요!")
    elif not api_key:
        st.error("🔑 API 키가 설정되지 않았습니다.")
    else:
        try:
            youtube = build('youtube', 'v3', developerKey=api_key)
            with st.spinner(f"📡 '{query}' 신호 분석 중..."):
                # 100개 수집을 위한 반복 처리
                video_ids = []
                next_page_token = None
                target_results = max_results
                
                while len(video_ids) < target_results:
                    current_max = min(50, target_results - len(video_ids))
                    search_request = youtube.search().list(
                        part="snippet", q=query, maxResults=current_max, order="viewCount", type="video", 
                        videoDuration=api_duration, publishedAfter=published_after, regionCode=region_code,
                        pageToken=next_page_token
                    )
                    search_response = search_request.execute()
                    video_ids.extend([item['id']['videoId'] for item in search_response['items']])
                    next_page_token = search_response.get('nextPageToken')
                    if not next_page_token or len(video_ids) >= target_results: break

                if not video_ids: st.error("신호 없음 (검색 결과 0건)")
                else:
                    # 상세 정보 수집
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
                        
                        if perf >= 1000: grade = "🟣 S-Tier (전설)"
                        elif perf >= 300: grade = "🔴 A-Tier (초대박)"
                        elif perf >= 100: grade = "🟢 B-Tier (우수)"
                        else: grade = "⚪ Normal (일반)"

                        if not (subs_range[0] <= sub_count <= subs_range[1]): continue
                        grade_simple = grade.split(' ')[0] + ' ' + grade.split(' ')[1]
                        if grade_simple not in filter_grade: continue

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

# 화면 출력 (리스트 & 프리뷰)
with main_col:
    # 레이아웃 분할 (리스트 7 : 프리뷰 3)
    col_list, col_preview = st.columns([7, 3])
    
    # 1. 리스트 출력 영역
    with col_list:
        if st.session_state.df_result is not None:
            df = st.session_state.df_result
            st.success(f"✅ 신호 포착 완료! {len(df)}건 발견")
            
            selection = st.dataframe(
                df,
                column_order=("No", "썸네일", "채널명", "제목", "게시일", "구독자", "조회수", "성과도", "등급", "길이", "참여율"),
                column_config={
                    "No": st.column_config.TextColumn("No", width=40),
                    "썸네일": st.column_config.ImageColumn("썸네일", width=80),
                    "채널명": st.column_config.TextColumn("채널명", width=120),
                    "제목": st.column_config.TextColumn("제목", width=300),
                    "게시일": st.column_config.TextColumn("게시일", width=90),
                    "구독자": st.column_config.TextColumn("구독자", width=80),
                    "조회수": st.column_config.TextColumn("조회수", width=90),
                    "성과도": st.column_config.ProgressColumn("성과도", format="%.0f%%", min_value=0, max_value=1000, width=100),
                    "등급": st.column_config.TextColumn("등급", width=120),
                    "길이": st.column_config.TextColumn("길이", width=70),
                    "참여율": st.column_config.TextColumn("참여율", width=70),
                    "ID": None, "raw_perf": None, "raw_view": None, "댓글": None, "좋아요": None, "이동": None
                },
                hide_index=True, use_container_width=True, height=800, 
                on_select="rerun", selection_mode="single-row"
            )
        else:
            st.info("👈 왼쪽 사이드바에서 키워드를 입력하고 검색을 시작하세요.")
            selection = None

    # 2. 오른쪽 프리뷰 패널 영역 (통일된 디자인 적용)
    with col_preview:
        # ⭐ [디자인 통일] 헤더 박스
        st.markdown("""
            <div class="preview-header-box">
                <h3 style='margin:0; color: #E0E0E0; font-size: 22px;'>👁️ SIGNAL PREVIEW</h3>
            </div>
        """, unsafe_allow_html=True)
        
        # 내용 박스 시작
        preview_placeholder = st.container()

        with preview_placeholder:
            # ⭐ [디자인 통일] 내용 컨테이너 스타일 적용
            st.markdown('<div class="preview-content-box">', unsafe_allow_html=True)

            if selection and selection.selection.rows:
                row = df.iloc[selection.selection.rows[0]]
                
                # 1. 영상 플레이어
                st.video(f"https://www.youtube.com/watch?v={row['ID']}")
                
                # 2. 제목
                st.markdown(f"#### {row['제목']}")
                
                # 3. 정보창 (3단 층별 정리)
                st.markdown("---")
                
                # 1층: 소속 정보
                c_meta1, c_meta2 = st.columns(2)
                with c_meta1: st.caption(f"📺 {row['채널명']}")
                with c_meta2: st.caption(f"📅 {row['게시일']}")
                
                # 2층: 성적표 (강조된 하늘색 숫자)
                c_stat1, c_stat2 = st.columns(2)
                with c_stat1: st.metric("성과도", f"{row['raw_perf']:,.0f}%")
                with c_stat2: st.metric("조회수", f"{row['raw_view']:,}")
                
                # 3층: 액션 버튼
                st.markdown("<br>", unsafe_allow_html=True)
                st.link_button("🔗 유튜브에서 보기", f"https://www.youtube.com/watch?v={row['ID']}", use_container_width=True, type="primary")

                # 등급 뱃지
                st.divider()
                if "S-Tier" in row['등급']: st.success("🔥 **S-Tier (전설의 떡상)**")
                elif "A-Tier" in row['등급']: st.info("👍 **A-Tier (초대박 신호)**")
                elif "B-Tier" in row['등급']: st.warning("🟢 **B-Tier (우수 신호)**")
            
            elif st.session_state.df_result is not None:
                # 리스트는 있지만 선택 안 했을 때 (요약 정보)
                st.info("📌 리스트에서 영상을 선택하면 상세 정보가 표시됩니다.")
                st.markdown("---")
                st.metric("총 포착 수", f"{len(df)}건")
                st.metric("S-Tier 발견", f"{len(df[df['등급'].str.contains('S-Tier')])}개")

            else:
                # 초기 상태
                st.write("검색 대기 중...")

            st.markdown('</div>', unsafe_allow_html=True) # 내용 박스 끝
