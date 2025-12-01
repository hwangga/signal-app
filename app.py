# -----------------------------
# ▶ 테이블 렌더링 (전체 리스트)
# -----------------------------

st.markdown("---")
st.markdown("### 📊 전체 영상 리스트")

df = st.session_state.df_result

if df is None or df.empty:
    st.info("검색 결과가 없습니다.")
else:

    # 👍 좋아요 컬럼 생성 (raw_like → 좋아요)
    df["좋아요"] = df["raw_like"].apply(lambda x: f"{x:,}")

    selected = st.dataframe(
        df,
        height=600,
        use_container_width=True,
        selection_mode="single-row",
        on_select="rerun",
        hide_index=True,
        column_order=[
            "No", "썸네일", "채널명", "제목", "게시일",
            "총 영상 수", "조회수", "좋아요", "성과도", 
            "등급", "길이", "일일 속도", "이동"
        ],
        column_config={
            "No": st.column_config.TextColumn("No", width=40),
            "썸네일": st.column_config.ImageColumn("썸네일", width=80),
            "채널명": st.column_config.TextColumn("채널명", width=130),
            "제목": st.column_config.TextColumn("제목", width=300),
            "게시일": st.column_config.TextColumn("게시일", width=80),
            "총 영상 수": st.column_config.TextColumn("총 영상 수", width=80),
            "조회수": st.column_config.TextColumn("조회수", width=90),
            "좋아요": st.column_config.TextColumn("좋아요", width=90),
            "성과도": st.column_config.ProgressColumn(
                "성과도", format="%.0f%%", min_value=0, 
                max_value=df["raw_perf"].max(), width=110
            ),
            "등급": st.column_config.TextColumn("등급", width=90),
            "길이": st.column_config.TextColumn("길이", width=60),
            "일일 속도": st.column_config.TextColumn("일일 속도", width=90),
            "이동": st.column_config.LinkColumn("이동", display_text="▶", width=50),

            # 👇 내부 RAW 값 숨김
            "ID": None,
            "raw_view": None,
            "raw_perf": None,
            "raw_comment": None,
            "raw_like": None,
            "raw_engagement": None
        }
    )

    if selected.selection.rows:
        st.session_state.selected_index = selected.selection.rows[0]
