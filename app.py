import streamlit as st
from googleapiclient.discovery import build
from datetime import datetime, timedelta
import isodate
import pandas as pd

# ==========================================
# 🔐 API 키는 Streamlit Cloud의 'Secrets'에서 가져옵니다.
# 로컬에서 테스트할 때는 왼쪽 사이드바에 직접 입력하세요.
# ==========================================

st.set_page_config(page_title="SIGNAL - YouTube Insight", layout="wide", page_icon="📡")

# 🌑 [스타일링]
st.markdown("""
<style>
    .stApp { background-color: #0E1117; color: #FAFAFA; }
    [data-testid="stSidebar"] { background-color: #212529; border-right: 1px solid #333; }
    th { background-color: #1E3A8A !important; color: white !important; text-align: center !important; }
    td { vertical-align: middle !important; text-align: center !important; }
    a { text-decoration: none; color: #4FC3F7; font-weight: bold; }
    a:hover { color: #FFFF00; text-decoration: underline; }
    [data-testid="stForm"] { border: 1px solid #444; padding: 20px; border-radius: 10px; background-color: #1a1c24; }
</style>
""", unsafe_allow_html=True)

st.title("📡 SIGNAL : YouTube Hunter")

# 1. 상단 (Top) 검색창
api_key = st.secrets.get("YOUTUBE_API_KEY", None) # 클라우드에선 여기서 키를 가져옴

with st.expander("🔎 검색 옵션 (펼치기)", expanded=True):
    with st.form(key='search_form'):
        # API 키가 없으면 입력창 보여주기
        if not api_key:
            col_key, _ = st.columns([1, 3])
            with col_key:
                manual_key = st.text_input("API 키 입력", type="password")
                if manual_key: api_key = manual_key

        c1, c2, c3, c4 = st.columns([2, 1, 1, 1])
        with c1: query = st.text_input("검색어 (엔터!)", "삶의질 상승템")
        with c2: max_results = st.number_input("수집수", 10, 50, 50)
        with c3: days_filter = st.selectbox("기간", ["1주일", "1개월", "3개월", "전체"], index=1)
        with c4: order_mode = st.selectbox("정렬", ["viewCount", "date"], format_func=lambda x: "조회수순" if x=="viewCount" else "최신순")

        c5, c6, c7 = st.columns([1, 2, 2])
        with c5: video_duration = st.radio("길이", ["쇼츠", "롱폼", "전체"], index=0, horizontal=True)
        with c6: filter_grade = st.multiselect("등급", ["🟣 초대박", "🔴 대박", "🟢 우수", "⚪ 보통"], default=["🟣 초대박", "🔴 대박", "🟢 우수"])
        with c7: subs_range = st.slider("구독자", 0, 1000000, (0, 1000000), 1000)

        search_trigger = st.form_submit_button("🚀 SIGNAL 감지 시작", type="primary", use_container_width=True)

# 2. 로직
if 'df_result' not in st.session_state: st.session_state.df_result = None

def parse_duration(d):
    try:
        dur = isodate.parse_duration(d)
        sec = int(dur.total_seconds())
        m, s = divmod(sec, 60)
        h, m = divmod(m, 60)
        return f"{h}:{m:02}:{s:02}" if h else f"{m}:{s:02}"
    except: return d

today = datetime.now()
if days_filter == "1주일": published_after = (today - timedelta(days=7)).isoformat("T") + "Z"
elif days_filter == "1개월": published_after = (today - timedelta(days=30)).isoformat("T") + "Z"
elif days_filter == "3개월": published_after = (today - timedelta(days=90)).isoformat("T") + "Z"
else: published_after = None
api_duration = "short" if video_duration == "쇼츠" else ("long" if video_duration == "롱폼" else "any")

if search_trigger and api_key:
    try:
        youtube = build('youtube', 'v3', developerKey=api_key)
        with st.spinner(f"📡 '{query}' 신호 분석 중..."):
            search_request = youtube.search().list(part="snippet", q=query, maxResults=max_results, order=order_mode, type="video", videoDuration=api_duration, publishedAfter=published_after, regionCode="KR")
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

                data_list = []
                for item in video_response['items']:
                    vid = item['id']
                    thumbs = item['snippet']['thumbnails']
                    thumb = thumbs.get('maxres', thumbs.get('standard', thumbs.get('high', thumbs.get('medium'))))['url']
                    
                    view_count = int(item['statistics'].get('viewCount', 0))
                    sub_count = subs_map.get(item['snippet']['channelId'], 0)
                    perf = (view_count / sub_count * 100) if sub_count > 0 else 0
                    
                    if perf >= 1000: grade = "🟣 초대박"
                    elif perf >= 300: grade = "🔴 대박"
                    elif perf >= 100: grade = "🟢 우수"
                    else: grade = "⚪ 보통"

                    if not (subs_range[0] <= sub_count <= subs_range[1]): continue
                    if grade not in filter_grade: continue

                    raw_date = datetime.strptime(item['snippet']['publishedAt'][:10], "%Y-%m-%d")
                    data_list.append({
                        "raw_perf": perf, "raw_date": raw_date,
                        "썸네일": thumb, "제목": item['snippet']['title'], "채널명": item['snippet']['channelTitle'],
                        "게시일": raw_date.strftime("%Y/%m/%d"), "구독자": sub_count, "조회수": view_count,
                        "성과도": perf, "등급": grade, "길이": parse_duration(item['contentDetails']['duration']),
                        "댓글": int(item['statistics'].get('commentCount', 0)),
                        "좋아요": int(item['statistics'].get('likeCount', 0)),
                        "참여율": (int(item['statistics'].get('commentCount', 0)) / view_count * 100) if view_count else 0,
                        "ID": vid
                    })
                
                # 정렬: 성과도 > 최신순
                sorted_list = sorted(data_list, key=lambda x: (x['raw_perf'], x['raw_date']), reverse=True)
                for i, row in enumerate(sorted_list): row['No'] = i + 1
                st.session_state.df_result = pd.DataFrame(sorted_list)
    except Exception as e: st.error(f"에러: {e}")

# 3. 화면 출력
with st.sidebar:
    st.header("🎞️ SIGNAL PREVIEW")
    st.info("리스트에서 행을 클릭하세요.")
    preview_container = st.container()

if st.session_state.df_result is not None:
    df = st.session_state.df_result
    st.success(f"신호 포착 완료! {len(df)}건")
    
    selection = st.dataframe(
        df,
        column_order=("No", "썸네일", "채널명", "제목", "게시일", "구독자", "조회수", "성과도", "등급", "길이", "댓글", "좋아요", "참여율", "이동"),
        column_config={
            "No": st.column_config.NumberColumn("No", width=50),
            "썸네일": st.column_config.ImageColumn("썸네일", width=80),
            "채널명": st.column_config.TextColumn("채널명", width=120),
            "제목": st.column_config.TextColumn("제목", width=350),
            "게시일": st.column_config.TextColumn("게시일", width=100),
            "구독자": st.column_config.NumberColumn("구독자", format="%d", width=100),
            "조회수": st.column_config.NumberColumn("조회수", format="%d", width=100),
            "성과도": st.column_config.ProgressColumn("성과도", format="%d%%", min_value=0, max_value=1000, width=120),
            "등급": st.column_config.TextColumn("등급", width=100),
            "길이": st.column_config.TextColumn("길이", width=80),
            "댓글": st.column_config.NumberColumn("댓글", format="%d", width=80),
            "좋아요": st.column_config.NumberColumn("좋아요", format="%d", width=80),
            "참여율": st.column_config.NumberColumn("참여율", format="%.2f%%", width=80),
            "이동": st.column_config.LinkColumn("이동", display_text="▶", width=60),
            "ID": None, "raw_perf": None, "raw_date": None
        },
        hide_index=True, use_container_width=False, height=800, on_select="rerun", selection_mode="single-row"
    )

    if selection.selection.rows:
        row = df.iloc[selection.selection.rows[0]]
        with preview_container:
            st.image(row['썸네일'], use_container_width=True)
            st.markdown(f"### [{row['제목']}](https://www.youtube.com/watch?v={row['ID']})")
            c1, c2 = st.columns(2)
            c1.metric("성과도", f"{row['성과도']:.0f}%")
            c2.metric("조회수", f"{row['조회수']:,}")
            st.divider()
            if "초대박" in row['등급']: st.success("🔥 강력한 떡상 신호!")
            st.markdown(f"**채널:** {row['채널명']}")
            st.link_button("📺 영상 보러가기", f"https://www.youtube.com/watch?v={row['ID']}", type="primary")