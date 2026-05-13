import pandas as pd
import streamlit as st
from utils.storage import load_annotations, SHEET_TAB_MAP, _get_spreadsheet, ANNOTATION_COLS

_ADMIN_PW = "admin1234"

DISEASE_COLS = [
    ("Aortic Dissection",     "aortic_dissection"),
    ("Myocardial Infarction", "myocardial_infarction"),
    ("Stroke Syndrome",       "stroke"),
    ("Meningitis",            "meningitis"),
    ("Sepsis",                "sepsis"),
]
REVIEWERS = list(SHEET_TAB_MAP.keys())   # ["김민하 교수님", "맹승진 교수님", "장한솔 교수님"]
REVIEWER_LABELS = ["A", "B", "C"]


# ── 인증 UI ──────────────────────────────────────────────────────────────────

def render_admin_login_sidebar() -> None:
    """사이드바 맨 하단 — 관리자 버튼 + 비밀번호 입력."""
    with st.sidebar:
        st.divider()
        if st.session_state.get("is_admin"):
            col1, col2 = st.columns(2)
            with col1:
                st.markdown(
                    "<span style='color:#1a3a5c;font-size:0.85rem;font-weight:600'>"
                    "🔐 관리자 모드</span>",
                    unsafe_allow_html=True,
                )
            with col2:
                if st.button("로그아웃", use_container_width=True, key="admin_logout"):
                    st.session_state["is_admin"] = False
                    st.session_state.pop("_admin_pw_visible", None)
                    st.rerun()
        else:
            if st.button("🔐 관리자 모드", use_container_width=True, key="admin_btn"):
                st.session_state["_admin_pw_visible"] = True

            if st.session_state.get("_admin_pw_visible"):
                pw = st.text_input("비밀번호", type="password", key="admin_pw_input")
                if st.button("확인", use_container_width=True, key="admin_pw_confirm"):
                    if pw == _ADMIN_PW:
                        st.session_state["is_admin"] = True
                        st.session_state.pop("_admin_pw_visible", None)
                        st.rerun()
                    else:
                        st.error("비밀번호가 틀렸습니다.")


# ── 데이터 준비 ───────────────────────────────────────────────────────────────

def _load_all() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Reviewer A / B / C annotation 데이터 반환."""
    ann_a = load_annotations(REVIEWERS[0])
    ann_b = load_annotations(REVIEWERS[1])
    ann_c = load_annotations(REVIEWERS[2])
    return ann_a, ann_b, ann_c


def _completion_stats(ann: pd.DataFrame) -> dict:
    """T0 완료 수 / T1 완료 수 / 둘 다 완료 수."""
    if ann.empty or "timepoint" not in ann.columns or "case_index" not in ann.columns:
        return {"t0": 0, "t1": 0, "both": 0}
    t0 = set(ann[ann["timepoint"] == "T0"]["case_index"].dropna().astype(int))
    t1 = set(ann[ann["timepoint"] == "T1"]["case_index"].dropna().astype(int))
    return {"t0": len(t0), "t1": len(t1), "both": len(t0 & t1)}


def _build_compare_df(ann_a: pd.DataFrame, ann_b: pd.DataFrame, ann_c: pd.DataFrame) -> pd.DataFrame:
    """case_index × timepoint × 질환 기준 비교 DataFrame 생성."""
    rows = []

    for ann, rev_key in [(ann_a, "A"), (ann_b, "B"), (ann_c, "C")]:
        if ann.empty or "timepoint" not in ann.columns:
            continue
        for _, row in ann.iterrows():
            ci = row.get("case_index")
            tp = row.get("timepoint")
            if pd.isna(ci) or tp not in ("T0", "T1"):
                continue
            for eng, col in DISEASE_COLS:
                val = row.get(col, "")
                rows.append({
                    "case_index": int(ci),
                    "timepoint":  tp,
                    "disease":    eng,
                    "reviewer":   rev_key,
                    "answer":     str(val).strip() if val else "",
                })

    if not rows:
        return pd.DataFrame()

    long = pd.DataFrame(rows)
    pivot = long.pivot_table(
        index=["case_index", "timepoint", "disease"],
        columns="reviewer",
        values="answer",
        aggfunc="first",
    ).reset_index()
    pivot.columns.name = None

    for col in ("A", "B", "C"):
        if col not in pivot.columns:
            pivot[col] = ""

    pivot = pivot.rename(columns={"A": "Reviewer A", "B": "Reviewer B", "C": "Reviewer C"})

    def _agree(r):
        vals = [v for v in [r["Reviewer A"], r["Reviewer B"], r["Reviewer C"]] if v != ""]
        if len(vals) < 2:
            return "—"
        return "✅" if len(set(vals)) == 1 else "❌"

    pivot["일치"] = pivot.apply(_agree, axis=1)
    return pivot.sort_values(["case_index", "timepoint", "disease"]).reset_index(drop=True)


def _kappa_table(compare: pd.DataFrame) -> pd.DataFrame:
    """질환 × 시점별 Cohen's Kappa 계산 (A-B, A-C, B-C 쌍별)."""
    try:
        from sklearn.metrics import cohen_kappa_score
    except ImportError:
        return pd.DataFrame({"오류": ["scikit-learn이 설치되지 않았습니다."]})

    pairs = [
        ("Reviewer A", "Reviewer B", "A-B"),
        ("Reviewer A", "Reviewer C", "A-C"),
        ("Reviewer B", "Reviewer C", "B-C"),
    ]
    results = []
    for eng, _ in DISEASE_COLS:
        sub = compare[compare["disease"] == eng].copy()
        row = {"질환": eng}
        for tp in ("T0", "T1", "Tall"):
            s = sub[sub["timepoint"] == tp].copy()
            for r1, r2, label in pairs:
                if r1 not in s.columns or r2 not in s.columns:
                    row[f"{tp} ({label})"] = None
                    continue
                s2 = s[(s[r1].isin(("Yes", "No"))) & (s[r2].isin(("Yes", "No")))]
                if len(s2) < 2:
                    row[f"{tp} ({label})"] = None
                else:
                    try:
                        k = cohen_kappa_score(s2[r1], s2[r2])
                        row[f"{tp} ({label})"] = round(k, 3)
                    except Exception:
                        row[f"{tp} ({label})"] = None
        results.append(row)
    return pd.DataFrame(results)


def _kappa_color(val):
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return ""
    if val >= 0.80:
        return "background-color: #d4edda; color: #155724"
    if val >= 0.60:
        return "background-color: #fff3cd; color: #856404"
    return "background-color: #f8d7da; color: #721c24"


# ── 관리자 화면 렌더 ──────────────────────────────────────────────────────────

def render_admin_page() -> None:
    if not st.session_state.get("is_admin"):
        st.error("접근 권한이 없습니다.")
        st.stop()

    st.markdown("## 🔐 관리자 페이지")
    st.caption("Reviewer A/B/C 응답 현황 및 일치도 분석")

    with st.spinner("Google Sheets에서 데이터 불러오는 중..."):
        ann_a, ann_b, ann_c = _load_all()

    compare = _build_compare_df(ann_a, ann_b, ann_c)

    # ── 섹션 1: 전체 진행 현황 ────────────────────────────────────────────────
    st.markdown("### 1. 전체 진행 현황")
    col1, col2, col3 = st.columns(3)
    for col, reviewer, ann in [
        (col1, REVIEWERS[0], ann_a),
        (col2, REVIEWERS[1], ann_b),
        (col3, REVIEWERS[2], ann_c),
    ]:
        stats = _completion_stats(ann)
        with col:
            st.markdown(
                f"<div style='background:#f0f4f8;border-radius:8px;padding:16px 20px'>"
                f"<b>{reviewer}</b><br>"
                f"T0 완료: <b>{stats['t0']}건</b> &nbsp;|&nbsp; "
                f"T1 완료: <b>{stats['t1']}건</b><br>"
                f"둘 다 완료: <b>{stats['both']}건</b>"
                f"</div>",
                unsafe_allow_html=True,
            )

    st.markdown("<br>", unsafe_allow_html=True)

    if compare.empty:
        st.info("아직 reviewer 데이터가 없습니다.")
        return

    # ── 섹션 2: 케이스별 A/B/C 비교 테이블 ───────────────────────────────────
    st.markdown("### 2. 케이스별 A/B/C 비교")

    def _row_style(row):
        if row["일치"] == "❌":
            return ["background-color: #fdecea"] * len(row)
        return [""] * len(row)

    display_cols = ["case_index", "timepoint", "disease", "Reviewer A", "Reviewer B", "Reviewer C", "일치"]
    st.dataframe(
        compare[display_cols].style.apply(_row_style, axis=1),
        use_container_width=True,
        hide_index=True,
        height=400,
    )

    # ── 섹션 3: Cohen's Kappa ─────────────────────────────────────────────────
    st.markdown("### 3. Cohen's Kappa (질환 × 시점 × 쌍)")
    st.caption("≥ 0.80 높음 (초록) / 0.60–0.79 보통 (노랑) / < 0.60 낮음 (빨강)")

    kappa_df = _kappa_table(compare)
    if "오류" in kappa_df.columns:
        st.warning(kappa_df["오류"].iloc[0])
    else:
        kappa_cols = [c for c in kappa_df.columns if c != "질환"]
        styled = kappa_df.style.applymap(_kappa_color, subset=kappa_cols)
        st.dataframe(styled, use_container_width=True, hide_index=True)

    # ── 섹션 4: 불일치 케이스 목록 ───────────────────────────────────────────
    st.markdown("### 4. 불일치 케이스 목록")
    discord = compare[compare["일치"] == "❌"][
        ["case_index", "timepoint", "disease", "Reviewer A", "Reviewer B", "Reviewer C"]
    ].reset_index(drop=True)

    if discord.empty:
        st.success("불일치 케이스 없음")
    else:
        st.dataframe(discord, use_container_width=True, hide_index=True)

        if st.button("📤 Google Sheets Discordant 탭에 내보내기", type="primary"):
            _export_discordant(discord)


def _export_discordant(discord: pd.DataFrame) -> None:
    try:
        ss = _get_spreadsheet()
        try:
            ws = ss.worksheet("Discordant")
        except Exception:
            ws = ss.add_worksheet(title="Discordant", rows=1000, cols=20)

        header = ["case_index", "timepoint", "disease", "Reviewer A", "Reviewer B", "Reviewer C"]
        data = [header] + discord.values.tolist()
        ws.clear()
        ws.update("A1", data)
        st.success(f"Discordant 탭에 {len(discord)}건 내보내기 완료.")
    except Exception as e:
        st.error(f"내보내기 실패: {e}")
