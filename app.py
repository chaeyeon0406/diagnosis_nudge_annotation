import streamlit as st
import pandas as pd

st.set_page_config(
    page_title="ED Annotation Tool",
    layout="wide",
    initial_sidebar_state="expanded",
)

from utils.data import load_data
from utils.storage import load_annotations, done_cases_from_df, ANNOTATION_COLS
from ui.styles import inject_css
from ui.header import render_header, render_progress
from ui.sidebar import render_sidebar
from ui.tabs import render_tabs
from ui.admin import render_admin_page, render_admin_login_sidebar

# ── CSS ──────────────────────────────────────────────────────────────────────
inject_css()

# ── 세션 초기화 ───────────────────────────────────────────────────────────────
st.session_state.setdefault("started", False)
st.session_state.setdefault("reviewer", "김민하 교수님")
st.session_state.setdefault("case_idx", 0)
st.session_state.setdefault("is_admin", False)
st.session_state.setdefault("cached_ann", None)   # Sheets 1회 로드 캐시

# ── 데이터 로드 (캐시됨, 빠름) ────────────────────────────────────────────────
t0, t1, tall = load_data()
TOTAL = len(t0)

# ── 관리자 화면 ──────────────────────────────────────────────────────────────
if st.session_state.get("is_admin"):
    render_admin_login_sidebar()
    render_admin_page()
    st.stop()

# ── 시작 화면 ─────────────────────────────────────────────────────────────────
if not st.session_state.started:
    col = st.columns([1, 2, 1])[1]
    with col:
        st.markdown("""
        <div style="background:#1a3a5c;border-radius:12px;padding:40px 32px;
                    text-align:center;color:#fff;margin-top:80px;">
            <h1 style="color:#fff;margin-bottom:4px;">ED Case Annotation</h1>
            <p style="color:#a8c4e0;font-size:14px;">
                MIMIC-IV-ED · 응급의학과 감별진단 Annotation
            </p>
        </div>
        """, unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)
        reviewer = st.radio("Reviewer 선택", ["김민하 교수님", "맹승진 교수님"],
                            horizontal=True, key="reviewer_select")
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("▶  Annotation 시작", type="primary", use_container_width=True):
            st.session_state.reviewer = reviewer
            st.session_state.started  = True

            # ── Sheets 1회 로드 ─────────────────────────────────────────────
            with st.spinner("이전 기록 불러오는 중..."):
                ann = load_annotations(reviewer)
            st.session_state["cached_ann"] = ann

            # ── 재개 케이스 계산 ─────────────────────────────────────────────
            done = done_cases_from_df(ann)
            if done and len(done) < TOTAL:
                # 완료된 케이스 중 최대 index + 1 부터 시작
                st.session_state.case_idx = min(max(done) + 1, TOTAL - 1)
            else:
                # 아무것도 없거나 전체 완료 → Case 1
                st.session_state.case_idx = 0

            st.rerun()
    st.stop()

# ── 메인 앱 ──────────────────────────────────────────────────────────────────
reviewer = st.session_state.reviewer
idx      = st.session_state.case_idx

# 캐시된 annotation 사용 (없으면 빈 DataFrame)
existing_ann = st.session_state.get("cached_ann")
if existing_ann is None:
    existing_ann = pd.DataFrame(columns=ANNOTATION_COLS)

done_cases = done_cases_from_df(existing_ann)

row_t0   = t0.iloc[idx]
row_t1   = t1.iloc[idx]
row_tall = tall.iloc[idx]
stay_id  = row_t0["stay_id"]

# ── 사이드바 ──────────────────────────────────────────────────────────────────
render_sidebar(reviewer, done_cases, TOTAL)

# ── 고정 헤더 + 진행 바 ───────────────────────────────────────────────────────
render_header(row_t0, idx, TOTAL)
render_progress(done_cases, TOTAL)

# ── 메인 레이아웃 ─────────────────────────────────────────────────────────────
render_tabs(row_t0, row_t1, row_tall, reviewer, idx, stay_id, TOTAL, existing_ann)
