import streamlit as st

_CSS = """
<style>
.stApp { background-color: #f5f7fa; }

#fixed-header {
    position: fixed;
    top: 0; left: 0; right: 0;
    z-index: 9999;
    background: #1a3a5c;
    color: #ffffff;
    padding: 8px 24px;
    display: flex;
    align-items: center;
    gap: 20px;
    font-family: 'Segoe UI', sans-serif;
    font-size: 13px;
    box-shadow: 0 2px 6px rgba(0,0,0,0.3);
    flex-wrap: wrap;
}
#fixed-header .hdr-item  { display: flex; flex-direction: column; align-items: flex-start; }
#fixed-header .hdr-label { font-size: 10px; color: #a8c4e0; text-transform: uppercase; letter-spacing: 0.5px; }
#fixed-header .hdr-value { font-size: 14px; font-weight: 600; color: #ffffff; }
#fixed-header .hdr-divider { width: 1px; height: 36px; background: #2d5a8a; }
#fixed-header .vital-normal   { color: #7ecfff; font-weight: 600; }
#fixed-header .vital-abnormal { color: #ff6b6b; font-weight: 700; }

.acuity-badge { display: inline-block; padding: 2px 10px; border-radius: 12px;
                font-weight: 700; font-size: 13px; color: #fff; }
.acuity-1 { background: #c0392b; }
.acuity-2 { background: #e67e22; }
.acuity-3 { background: #f1c40f; color: #333; }
.acuity-4 { background: #27ae60; }
.acuity-5 { background: #2980b9; }

.main-content-offset { margin-top: 90px; }

.info-card {
    background: #ffffff;
    border: 1px solid #d6e4f0;
    border-radius: 6px;
    padding: 16px 20px;
    margin-bottom: 12px;
}
.info-card h4 {
    color: #1a3a5c; font-size: 13px; font-weight: 700;
    text-transform: uppercase; letter-spacing: 0.5px;
    margin: 0 0 10px 0;
    border-bottom: 2px solid #d6e4f0; padding-bottom: 6px;
}

.progress-container {
    background: #ffffff; border: 1px solid #d6e4f0;
    border-radius: 6px; padding: 10px 16px; margin-bottom: 12px;
}

.stTabs [data-baseweb="tab-list"] { gap: 4px; background: #ffffff;
                                     border-bottom: 2px solid #1a3a5c; }
.stTabs [data-baseweb="tab"] { background: #eef4fb; color: #1a3a5c;
                                border-radius: 6px 6px 0 0; font-weight: 600; padding: 8px 24px; }
.stTabs [aria-selected="true"] { background: #1a3a5c !important; color: #ffffff !important; }

.annotation-panel {
    background: #ffffff; border: 2px solid #1a3a5c;
    border-radius: 8px; padding: 16px; position: sticky; top: 90px;
}
.annotation-panel h3 {
    color: #1a3a5c; font-size: 14px; font-weight: 700;
    margin-bottom: 12px; border-bottom: 2px solid #1a3a5c; padding-bottom: 6px;
}

div[data-testid="stButton"] button[kind="primary"] {
    background: #1a3a5c; border: none; color: white; font-weight: 700;
}

/* ─── Darwin EMR 스타일 Lab Results 테이블 ───────────────────────────── */
.darwin-lab-table {
    width: 100%;
    border-collapse: collapse;
    font-size: 0.83rem;
    font-family: 'Segoe UI', sans-serif;
}
.darwin-lab-table thead tr th {
    background: #1a3a5c;
    color: #ffffff;
    padding: 7px 10px;
    text-align: left;
    font-weight: 600;
    font-size: 0.76rem;
    letter-spacing: 0.3px;
    white-space: nowrap;
}
.darwin-lab-table tbody tr td {
    padding: 5px 10px;
    border-bottom: 1px solid #f0f3f7;
    vertical-align: middle;
    color: #2c3e50;
}
.darwin-lab-table tbody tr:hover td { background: #f5f9ff; }
.darwin-lab-table tbody tr.group-sep td { border-top: 2px solid #c8d6e5; }

.lab-high   { color: #c0392b; font-weight: 700; }
.lab-low    { color: #1a6fa8; font-weight: 700; }
.lab-normal { color: #2c3e50; }
.lab-unit   { color: #888; }
.lab-range  { color: #999; }
.lab-time   { color: #777; font-size: 0.78rem; white-space: nowrap; }

/* ─── Lab 보기 모드 토글 버튼 ───────────────────────────────────────────── */
:root { --lab-toggle-color: #1a3a5c; }

/* 마커 바로 다음 stHorizontalBlock 안 버튼 공통 */
div[data-testid="stMarkdown"]:has(span[class^="lab-toggle-"])
  + div[data-testid="stHorizontalBlock"] button {
    border: 1.5px solid var(--lab-toggle-color) !important;
    background: transparent !important;
    color: var(--lab-toggle-color) !important;
    border-radius: 6px !important;
    font-weight: 600 !important;
    font-size: 0.82rem !important;
    padding: 0.25rem 0 !important;
}

/* ─── Darwin EMR 스타일 피벗(시계열) 테이블 ────────────────────────────── */
.darwin-pivot-wrap {
    overflow-x: auto;
    max-height: 540px;
    overflow-y: auto;
}
.darwin-pivot-table {
    border-collapse: collapse;
    font-size: 0.82rem;
    font-family: 'Segoe UI', sans-serif;
    white-space: nowrap;
}
.darwin-pivot-table thead tr th {
    background: #1a3a5c;
    color: #ffffff;
    padding: 6px 12px;
    font-weight: 600;
    font-size: 0.76rem;
    text-align: center;
    border-right: 1px solid #2d5a8a;
    position: sticky;
    top: 0;
    z-index: 2;
}
.darwin-pivot-table thead tr th:first-child {
    text-align: left;
    position: sticky;
    left: 0;
    z-index: 3;
}
.darwin-pivot-table tbody tr td {
    padding: 5px 12px;
    border-bottom: 1px solid #f0f3f7;
    border-right: 1px solid #f0f3f7;
    text-align: center;
    color: #2c3e50;
}
.darwin-pivot-table tbody tr td:first-child {
    text-align: left;
    background: #f8fafc;
    position: sticky;
    left: 0;
    z-index: 1;
    border-right: 2px solid #c8d6e5;
    font-size: 0.8rem;
    min-width: 200px;
    max-width: 260px;
    white-space: normal;
    word-break: break-word;
}
.darwin-pivot-table tbody tr:hover td { background: #f0f6ff; }
.darwin-pivot-table tbody tr:hover td:first-child { background: #e8f0fb; }

/* ─── Annotation 칩 버튼: 색상 변수 & 기본(미선택) 스타일 ──────────────── */
:root {
    --annot-yes-color: #1a3a5c;   /* 선택됨: 네이비 */
}

/* 마커 span 바로 다음 stButton 안 버튼 — 기본(미선택) */
div[data-testid="stMarkdown"]:has(span[class^="annot-chip-"])
  + div[data-testid="stButton"] > button {
    border: 1.5px solid #c8d6e5 !important;
    background: #ffffff !important;
    color: #2c3e50 !important;
    border-radius: 8px !important;
    font-weight: 600 !important;
    font-size: 0.88rem !important;
    text-align: left !important;
    padding: 0.5rem 1rem !important;
    transition: background-color 0.15s, color 0.15s, border-color 0.15s !important;
    margin-bottom: 4px !important;
}
</style>
"""


def inject_css() -> None:
    st.markdown(_CSS, unsafe_allow_html=True)
