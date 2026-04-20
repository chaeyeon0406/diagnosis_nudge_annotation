import pandas as pd
import streamlit as st
from utils.storage import save_annotation, load_annotations

DISEASES = [
    ("Aortic Dissection",     "aortic_dissection",     "대동맥 박리"),
    ("Myocardial Infarction", "myocardial_infarction",  "심근경색"),
    ("Stroke",                "stroke",                 "뇌졸중"),
    ("Meningitis",            "meningitis",              "뇌수막염"),
    ("Sepsis",                "sepsis",                  "패혈증"),
]


# ── 세션 동기화 ───────────────────────────────────────────────────────────────

def _sync_state(idx: int, timepoint: str, existing_ann: pd.DataFrame) -> None:
    """케이스 또는 timepoint가 바뀔 때만 session_state를 저장된 값으로 초기화."""
    sentinel_key = f"_annot_idx_{timepoint}"
    if st.session_state.get(sentinel_key) == idx:
        return

    # 해당 case + timepoint 행 검색
    existing_row = pd.DataFrame()
    if (not existing_ann.empty
            and "case_index" in existing_ann.columns
            and "timepoint" in existing_ann.columns):
        existing_row = existing_ann[
            (existing_ann["case_index"] == idx) &
            (existing_ann["timepoint"] == timepoint)
        ]

    for _, col, _ in DISEASES:
        saved = False
        if not existing_row.empty:
            val = existing_row.iloc[0].get(col)
            if val and not (isinstance(val, float) and pd.isna(val)):
                saved = str(val).strip() == "Yes"
        st.session_state[f"annot_{timepoint}_{col}"] = saved

    st.session_state[sentinel_key] = idx


# ── 클릭 콜백 ────────────────────────────────────────────────────────────────

def _toggle(col: str, timepoint: str) -> None:
    key = f"annot_{timepoint}_{col}"
    st.session_state[key] = not st.session_state.get(key, False)


# ── 칩 버튼 렌더링 ────────────────────────────────────────────────────────────

def _chip(col: str, label_en: str, label_ko: str, timepoint: str) -> None:
    selected = st.session_state.get(f"annot_{timepoint}_{col}", False)
    marker   = f"annot-chip-{timepoint}-{col}".replace("_", "-")

    selected_css = f"""
<style>
div[data-testid="stMarkdown"]:has(span.{marker})
  + div[data-testid="stButton"] > button {{
    background-color: var(--annot-yes-color) !important;
    color: #ffffff !important;
    border-color: var(--annot-yes-color) !important;
}}
</style>""" if selected else ""

    st.markdown(
        f'{selected_css}<span class="{marker}"></span>',
        unsafe_allow_html=True,
    )

    label = f"✓  {label_en}  ({label_ko})" if selected else f"○  {label_en}  ({label_ko})"
    st.button(
        label,
        key=f"chip_{timepoint}_{col}",
        use_container_width=True,
        on_click=_toggle,
        args=(col, timepoint),
    )


# ── Public ────────────────────────────────────────────────────────────────────

def render_annotation_panel(reviewer: str, idx: int, stay_id, total: int,
                            timepoint: str, existing_ann: pd.DataFrame) -> None:
    """
    timepoint: "T0" | "T1" | "Tall"
    existing_ann: load_annotations(reviewer) 결과 DataFrame (app.py에서 전달)
    """
    _sync_state(idx, timepoint, existing_ann)

    # 저장 여부 확인 (T1/Tall 버튼 활성화 조건)
    def _is_saved(tp: str) -> bool:
        if (existing_ann.empty
                or "case_index" not in existing_ann.columns
                or "timepoint" not in existing_ann.columns):
            return False
        return bool(
            ((existing_ann["case_index"] == idx) &
             (existing_ann["timepoint"] == tp)).any()
        )

    t0_saved   = _is_saved("T0")
    t1_saved   = _is_saved("T1")

    # 저장된 메모 로드
    memo_saved = ""
    if (not existing_ann.empty
            and "case_index" in existing_ann.columns
            and "timepoint" in existing_ann.columns):
        row = existing_ann[
            (existing_ann["case_index"] == idx) &
            (existing_ann["timepoint"] == timepoint)
        ]
        if not row.empty:
            raw = row.iloc[0].get("memo", "")
            if raw is None or raw == "None" or (isinstance(raw, float) and pd.isna(raw)):
                memo_saved = ""
            else:
                memo_saved = str(raw)

    st.markdown(f"### {timepoint} Annotation")
    st.caption("해당하는 감별진단을 선택하세요 (복수 선택 가능)")

    for label_en, col, label_ko in DISEASES:
        _chip(col, label_en, label_ko, timepoint)

    st.markdown("<br>", unsafe_allow_html=True)

    memo = st.text_area(
        "메모 (선택)", value=memo_saved, height=80,
        key=f"memo_{timepoint}_{idx}", placeholder="모호한 케이스 메모...",
    )

    def _collect_answers():
        return {
            eng: ("Yes" if st.session_state.get(f"annot_{timepoint}_{col}") else "No")
            for eng, col, _ in DISEASES
        }

    def _save_and_refresh_cache(tp: str) -> bool:
        ok = save_annotation(reviewer, idx, stay_id, tp, _collect_answers(), memo)
        if ok:
            st.session_state["cached_ann"] = load_annotations(reviewer)
        return ok

    if timepoint == "T0":
        if st.button(
            "저장", type="primary",
            use_container_width=True, key=f"save_T0_{idx}",
        ):
            _save_and_refresh_cache("T0")
            st.rerun()

    elif timepoint == "T1":
        c_prev, c_save = st.columns(2)
        with c_prev:
            if st.button(
                "◀ 이전", disabled=(idx == 0),
                use_container_width=True, key=f"prev_T1_{idx}",
            ):
                st.session_state.case_idx = max(0, idx - 1)
                st.rerun()
        with c_save:
            if st.button(
                "저장", type="primary",
                use_container_width=True, key=f"save_T1_{idx}",
                disabled=not t0_saved,
                help=None if t0_saved else "T0 먼저 저장하세요",
            ):
                _save_and_refresh_cache("T1")
                st.rerun()

    else:  # Tall
        tall_can_save = t0_saved and t1_saved
        c_prev, c_save = st.columns(2)
        with c_prev:
            if st.button(
                "◀ 이전", disabled=(idx == 0),
                use_container_width=True, key=f"prev_Tall_{idx}",
            ):
                st.session_state.case_idx = max(0, idx - 1)
                st.rerun()
        with c_save:
            help_msg = (
                None if tall_can_save else
                ("T0 먼저 저장하세요" if not t0_saved else "T1 먼저 저장하세요")
            )
            if st.button(
                "저장", type="primary",
                use_container_width=True, key=f"save_Tall_{idx}",
                disabled=not tall_can_save,
                help=help_msg,
            ):
                ok = _save_and_refresh_cache("Tall")
                if ok and idx < total - 1:
                    st.session_state.case_idx = idx + 1
                st.rerun()
