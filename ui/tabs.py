import math
from datetime import datetime
import pandas as pd
import streamlit as st
from utils.data import is_abnormal, parse_json_col, resolve_age, f_to_c
from ui.annotation_panel import render_annotation_panel

_VITALS_TABLE = [
    ("심박수 (HR)",        "heartrate",   "/min",  "60–100"),
    ("수축기혈압 (SBP)",   "sbp",         "mmHg",  "90–140"),
    ("이완기혈압 (DBP)",   "dbp",         "mmHg",  "60–90"),
    ("호흡수 (RR)",        "resprate",    "/min",  "12–20"),
    ("산소포화도 (O₂Sat)", "o2sat",       "%",     "95–100"),
    ("체온 (BT)",          "temperature", "°C",    "36.1–37.5"),
    ("통증 (Pain)",        "pain",        "/10",   "—"),
]


# ── 공통 유틸 ─────────────────────────────────────────────────────────────────

def _card_open(title: str) -> None:
    st.markdown(f'<div class="info-card"><h4>{title}</h4>', unsafe_allow_html=True)


def _card_close() -> None:
    st.markdown('</div>', unsafe_allow_html=True)


def _fmt_num(val) -> str:
    try:
        f = float(val)
        if math.isnan(f):
            return "-"
        return str(int(f)) if f == int(f) else f"{f:.2f}".rstrip("0").rstrip(".")
    except (TypeError, ValueError):
        return "-"


def _safe_float(val) -> float | None:
    try:
        f = float(val)
        return None if math.isnan(f) else f
    except (TypeError, ValueError):
        return None


def _fmt_time_header(ct: str) -> str:
    """'2138-02-19 16:11:00' → '02-19<br>16:11'"""
    try:
        dt = datetime.strptime(ct, "%Y-%m-%d %H:%M:%S")
        return dt.strftime("%m-%d<br>%H:%M")
    except ValueError:
        return ct


def _cell_html(vnum_f: float | None,
               lo_f: float | None, hi_f: float | None) -> str:
    if vnum_f is None:
        return '<span style="color:#ccc">-</span>'
    v_str = _fmt_num(vnum_f)
    if hi_f is not None and vnum_f > hi_f:
        return f'<span class="lab-high">▲{v_str}</span>'
    if lo_f is not None and vnum_f < lo_f:
        return f'<span class="lab-low">▼{v_str}</span>'
    return f'<span class="lab-normal">{v_str}</span>'


# ── 활력징후 테이블 ───────────────────────────────────────────────────────────

def _render_vitals_df(row: pd.Series) -> None:
    raw_orig  = []   # 원본값 (temperature는 °F) → is_abnormal 판별용
    disp_vals = []   # 표시용 문자열

    for _, key, *_ in _VITALS_TABLE:
        val = row.get(key)
        raw_orig.append(val)
        # 표시: temperature만 °C 변환, 나머지는 그대로 str
        try:
            if key == "temperature" and val is not None:
                disp_vals.append(str(round(f_to_c(val), 1)))
            elif val is None or (isinstance(val, float) and pd.isna(val)):
                disp_vals.append("-")
            else:
                disp_vals.append(str(val))
        except (TypeError, ValueError):
            disp_vals.append("-")

    df = pd.DataFrame({
        "항목":     [label for label, *_ in _VITALS_TABLE],
        "값":       disp_vals,          # 전부 str → ArrowInvalid 없음
        "단위":     [unit for _, _, unit, _ in _VITALS_TABLE],
        "정상범위": [ref  for _, _, _, ref  in _VITALS_TABLE],
    })
    key_list = [key for _, key, *_ in _VITALS_TABLE]

    def _highlight(row_s: pd.Series) -> list:
        i = df.index.get_loc(row_s.name)
        key = key_list[i]
        orig = raw_orig[i]
        try:
            if orig is not None and is_abnormal(key, orig):
                return ["color: #c0392b; font-weight: bold"] * len(row_s)
        except (TypeError, ValueError):
            pass
        return [""] * len(row_s)

    st.dataframe(df.style.apply(_highlight, axis=1),
                 use_container_width=True, hide_index=True)


# ── 활력징후 시계열 ───────────────────────────────────────────────────────────

def _render_history_df(json_val) -> None:
    records = parse_json_col(json_val)
    if not records:
        st.markdown("<p style='color:#999'>데이터 없음</p>", unsafe_allow_html=True)
        return
    df = pd.DataFrame(records)
    if "charttime" in df.columns:
        df = df.sort_values("charttime")
    if "temperature" in df.columns:
        df["temperature (°C)"] = df["temperature"].apply(
            lambda v: round(f_to_c(v), 1) if v is not None else None
        )
        df = df.drop(columns=["temperature"])
    # 숫자/문자 혼재 컬럼(pain 등) → ArrowInvalid 방지
    df = df.astype(str).replace("nan", "-")
    st.dataframe(df, use_container_width=True, hide_index=True)


# ── Lab: 목록 보기 ────────────────────────────────────────────────────────────

def _render_labs_list(df: pd.DataFrame) -> None:
    rows_html = []
    prev_time = None

    for _, r in df.iterrows():
        charttime = str(r.get("charttime", "")) if r.get("charttime") else ""
        label     = str(r.get("label", "—"))
        unit      = str(r.get("valueuom", "")) if r.get("valueuom") else ""

        vnum_f = _safe_float(r.get("valuenum"))
        lo_f   = _safe_float(r.get("ref_range_lower"))
        hi_f   = _safe_float(r.get("ref_range_upper"))

        result  = _cell_html(vnum_f, lo_f, hi_f)
        min_str = _fmt_num(lo_f) if lo_f is not None else "-"
        max_str = _fmt_num(hi_f) if hi_f is not None else "-"

        sep = ' class="group-sep"' if (prev_time is not None and charttime != prev_time) else ""
        rows_html.append(f"""
<tr{sep}>
  <td>{label}</td>
  <td>{result}</td>
  <td class="lab-unit">{unit}</td>
  <td class="lab-range">{min_str}</td>
  <td class="lab-range">{max_str}</td>
  <td class="lab-time">{charttime}</td>
</tr>""")
        prev_time = charttime

    html = f"""
<div style="overflow-x:auto;">
<table class="darwin-lab-table">
  <thead>
    <tr>
      <th>검사명</th><th>결과</th><th>단위</th>
      <th>Min</th><th>Max</th><th>검사일시</th>
    </tr>
  </thead>
  <tbody>{''.join(rows_html)}</tbody>
</table>
</div>"""
    st.markdown(html, unsafe_allow_html=True)


# ── Lab: 시계열(피벗) 보기 ────────────────────────────────────────────────────

def _render_labs_pivot(df: pd.DataFrame) -> None:
    meta: dict[str, dict] = {}
    for _, r in df.iterrows():
        lbl = str(r.get("label", "—"))
        if lbl not in meta:
            meta[lbl] = {
                "unit": str(r.get("valueuom", "")) if r.get("valueuom") else "",
                "lo":   _safe_float(r.get("ref_range_lower")),
                "hi":   _safe_float(r.get("ref_range_upper")),
            }
        else:
            if meta[lbl]["lo"] is None:
                meta[lbl]["lo"] = _safe_float(r.get("ref_range_lower"))
            if meta[lbl]["hi"] is None:
                meta[lbl]["hi"] = _safe_float(r.get("ref_range_upper"))

    all_labels = df["label"].unique()
    all_times  = sorted(df["charttime"].unique())

    pivot = (
        df.groupby(["label", "charttime"])["valuenum"]
        .first()
        .unstack("charttime")
        .reindex(index=all_labels, columns=all_times)
    )
    pivot.index.name = None
    pivot.columns.name = None

    times = list(pivot.columns)

    th_time = "".join(
        f"<th style='text-align:center'>{_fmt_time_header(t)}</th>"
        for t in times
    )

    rows_html = []
    for lbl, row_s in pivot.iterrows():
        m    = meta.get(str(lbl), {"unit": "", "lo": None, "hi": None})
        unit = f" <span style='color:#999;font-size:0.75rem'>({m['unit']})</span>" if m["unit"] else ""
        cells = ""
        for t in times:
            vnum_f = _safe_float(row_s.get(t))
            cells += f"<td>{_cell_html(vnum_f, m['lo'], m['hi'])}</td>"
        rows_html.append(f"<tr><td>{lbl}{unit}</td>{cells}</tr>")

    html = f"""
<div class="darwin-pivot-wrap">
<table class="darwin-pivot-table">
  <thead>
    <tr>
      <th>검사명</th>{th_time}
    </tr>
  </thead>
  <tbody>{''.join(rows_html)}</tbody>
</table>
</div>"""
    st.markdown(html, unsafe_allow_html=True)


# ── Lab + Imaging 병합 목록 ───────────────────────────────────────────────────

def _render_merged_list(lab_df: pd.DataFrame, rad_records: list) -> None:
    """Lab + Radiology를 charttime 기준 하나의 표에 시간순 병합.
    Imaging 행은 <details><summary> 네이티브 토글로 리포트 펼치기/접기.
    """
    import html as _html

    events = []
    for _, r in lab_df.iterrows():
        events.append({"type": "lab", "charttime": str(r.get("charttime", "")), "row": r})
    for rec in rad_records:
        events.append({"type": "rad", "charttime": str(rec.get("charttime", "")), "rec": rec})
    events.sort(key=lambda e: e["charttime"])

    rows_html = []
    prev_time: str | None = None

    for ev in events:
        charttime = ev["charttime"]
        sep = ' class="group-sep"' if (prev_time is not None and charttime != prev_time) else ""

        if ev["type"] == "lab":
            r       = ev["row"]
            label   = str(r.get("label", "—"))
            unit    = str(r.get("valueuom", "")) if r.get("valueuom") else ""
            vnum_f  = _safe_float(r.get("valuenum"))
            lo_f    = _safe_float(r.get("ref_range_lower"))
            hi_f    = _safe_float(r.get("ref_range_upper"))
            result  = _cell_html(vnum_f, lo_f, hi_f)
            min_str = _fmt_num(lo_f) if lo_f is not None else "-"
            max_str = _fmt_num(hi_f) if hi_f is not None else "-"
            rows_html.append(f"""
<tr{sep}>
  <td>{label}</td><td>{result}</td><td class="lab-unit">{unit}</td>
  <td class="lab-range">{min_str}</td><td class="lab-range">{max_str}</td>
  <td class="lab-time">{charttime}</td>
</tr>""")

        else:  # radiology
            rec       = ev["rec"]
            exam_name = _html.escape(str(rec.get("exam_name", "영상검사")))
            report    = _html.escape(str(rec.get("full_report", "리포트 없음")))
            rows_html.append(f"""
<tr{sep} style="background:#eef3f9;">
  <td colspan="5">
    <details>
      <summary style="cursor:pointer;color:#1a3a5c;font-weight:600;
                      list-style:none;padding:2px 0;">
        🩻 {exam_name}
      </summary>
      <pre style="white-space:pre-wrap;font-size:0.73rem;color:#333;
                  margin:6px 0 2px;padding:8px;background:#fff;
                  border-radius:4px;border:1px solid #d0dcea;">{report}</pre>
    </details>
  </td>
  <td class="lab-time">{charttime}</td>
</tr>""")

        prev_time = charttime

    html = f"""
<div style="overflow-x:auto;">
<table class="darwin-lab-table">
  <thead>
    <tr>
      <th>검사명</th><th>결과</th><th>단위</th>
      <th>Min</th><th>Max</th><th>검사일시</th>
    </tr>
  </thead>
  <tbody>{''.join(rows_html)}</tbody>
</table>
</div>"""
    st.markdown(html, unsafe_allow_html=True)


# ── Lab: 모드 토글 + 렌더 ─────────────────────────────────────────────────────

def _set_lab_view(section_key: str, mode: str) -> None:
    st.session_state[f"lab_view_{section_key}"] = mode


def _render_labs_with_toggle(lab_json, section_key: str, rad_json=None) -> None:
    lab_records = parse_json_col(lab_json)
    rad_records = parse_json_col(rad_json) if rad_json else []

    if not lab_records and not rad_records:
        st.markdown("<p style='color:#999'>데이터 없음</p>", unsafe_allow_html=True)
        return

    lab_df = pd.DataFrame(lab_records)
    if "charttime" in lab_df.columns:
        lab_df = lab_df.sort_values("charttime").reset_index(drop=True)

    state_key = f"lab_view_{section_key}"
    st.session_state.setdefault(state_key, "list")
    mode = st.session_state[state_key]

    marker = f"lab-toggle-{section_key}"
    list_css = (
        f"div[data-testid='stMarkdown']:has(span.{marker})"
        f" + div[data-testid='stHorizontalBlock']"
        f" div[data-testid='stColumn']:first-child button"
        "{ background: var(--lab-toggle-color) !important; color: #fff !important; }"
    ) if mode == "list" else ""
    pivot_css = (
        f"div[data-testid='stMarkdown']:has(span.{marker})"
        f" + div[data-testid='stHorizontalBlock']"
        f" div[data-testid='stColumn']:last-child button"
        "{ background: var(--lab-toggle-color) !important; color: #fff !important; }"
    ) if mode == "pivot" else ""

    count_str = f"Lab {len(lab_df)}건"
    if rad_records:
        count_str += f" · 영상 {len(rad_records)}건"

    combined_css = f"<style>{list_css}{pivot_css}</style>" if (list_css or pivot_css) else ""
    st.markdown(
        f'{combined_css}<span class="{marker}"></span>'
        f'<span style="font-size:0.8rem; color:#666;">{count_str}</span>',
        unsafe_allow_html=True,
    )

    col_list, col_pivot, *_ = st.columns([1, 1, 6])
    with col_list:
        st.button("목록 보기", key=f"btn_list_{section_key}",
                  use_container_width=True,
                  on_click=_set_lab_view, args=(section_key, "list"))
    with col_pivot:
        st.button("시계열 보기", key=f"btn_pivot_{section_key}",
                  use_container_width=True,
                  on_click=_set_lab_view, args=(section_key, "pivot"))

    if mode == "list":
        _render_merged_list(lab_df, rad_records)
    else:
        _render_labs_pivot(lab_df)   # 피벗은 lab만 (imaging은 수치 없음)


# ── T0 expander (T1/Tall 탭 공통) ────────────────────────────────────────────

def _t0_summary_expander(row_t0: pd.Series) -> None:
    _, age_display = resolve_age(row_t0)
    gender_str = "남" if str(row_t0.get("gender", "")).upper() == "M" else "여"
    with st.expander("▼ T0 기본 정보 보기", expanded=False):
        c1, c2, c3, c4 = st.columns(4)
        if age_display:
            c1.metric("나이", age_display)
        c2.metric("성별", gender_str)
        c3.metric("내원경로", str(row_t0.get("arrival_transport", "—")))
        c4.metric("Acuity", str(row_t0.get("acuity", "—")))
        st.markdown(f"**Chief Complaint:** {row_t0.get('chiefcomplaint', '—')}")
        meds = row_t0.get("home_medications", "")
        if meds and not (isinstance(meds, float) and pd.isna(meds)):
            st.markdown(f"**Medications:** {meds}")


# ── Public ────────────────────────────────────────────────────────────────────

def render_tabs(row_t0: pd.Series, row_t1: pd.Series, row_tall: pd.Series,
                reviewer: str, idx: int, stay_id, total: int,
                existing_ann: pd.DataFrame) -> None:
    _, age_display = resolve_age(row_t0)
    gender_str = "남" if str(row_t0.get("gender", "")).upper() == "M" else "여"
    transport  = str(row_t0.get("arrival_transport", "—"))
    acuity_val = str(row_t0.get("acuity", "—"))

    tab_t0, tab_t1, tab_tall = st.tabs(["T0  (Triage)", "T1  (1시간)", "Tall  (전체)"])

    # ── T0 ──────────────────────────────────────
    with tab_t0:
        col_data, col_ann = st.columns([3, 1])
        with col_data:
            _card_open("기본 정보")
            cols = st.columns(4)
            if age_display:
                cols[0].metric("나이", age_display)
            cols[1].metric("성별", gender_str)
            cols[2].metric("내원경로", transport)
            cols[3].metric("Acuity", acuity_val)
            _card_close()

            _card_open("Chief Complaint")
            st.markdown(
                f"<p style='font-size:16px;font-weight:600;color:#1a3a5c;margin:0'>"
                f"{row_t0.get('chiefcomplaint', '—')}</p>",
                unsafe_allow_html=True,
            )
            _card_close()

            _card_open("초기 활력징후 (Triage)")
            _render_vitals_df(row_t0)
            _card_close()

            _card_open("Home Medications")
            meds = row_t0.get("home_medications", "")
            if not meds or (isinstance(meds, float) and pd.isna(meds)):
                st.markdown("<p style='color:#999'>정보 없음</p>", unsafe_allow_html=True)
            else:
                med_list = [m.strip() for m in str(meds).split(",")]
                med_cols = st.columns(3)
                for i, med in enumerate(med_list):
                    med_cols[i % 3].markdown(f"• {med}")
            _card_close()

        with col_ann:
            render_annotation_panel(reviewer, idx, stay_id, total, "T0", existing_ann)

    # ── T1 ──────────────────────────────────────
    with tab_t1:
        col_data, col_ann = st.columns([3, 1])
        with col_data:
            _t0_summary_expander(row_t0)

            _card_open("활력징후 시계열 (T1)")
            _render_history_df(row_t1.get("vitals_t1_history"))
            _card_close()

            _card_open("검사 결과 (T1)")
            _render_labs_with_toggle(
                row_t1.get("labs_t1_history"), "t1",
                row_t1.get("radiology_t1_history"),
            )
            _card_close()

        with col_ann:
            render_annotation_panel(reviewer, idx, stay_id, total, "T1", existing_ann)

    # ── Tall ─────────────────────────────────────
    with tab_tall:
        col_data, col_ann = st.columns([3, 1])
        with col_data:
            _t0_summary_expander(row_t0)

            _card_open("활력징후 시계열 (Tall - 전체)")
            _render_history_df(row_tall.get("vitals_tall_history"))
            _card_close()

            _card_open("검사 결과 (Tall - 전체)")
            _render_labs_with_toggle(
                row_tall.get("labs_tall_history"), "tall",
                row_tall.get("radiology_tall_history"),
            )
            _card_close()

        with col_ann:
            render_annotation_panel(reviewer, idx, stay_id, total, "Tall", existing_ann)
