import pandas as pd
import streamlit as st
from utils.data import fmt_vital, acuity_badge, is_abnormal, resolve_age


def render_header(row: pd.Series, idx: int, total: int) -> None:
    _, age_display = resolve_age(row)
    gender_str = "남" if str(row.get("gender", "")).upper() == "M" else "여"

    cc = str(row.get("chiefcomplaint", "—"))
    if len(cc) > 40:
        cc = cc[:40] + "…"

    transport  = str(row.get("arrival_transport", "—"))
    acuity_val = row.get("acuity", "—")

    hr   = row.get("heartrate")
    bp_s = row.get("sbp")
    bp_d = row.get("dbp")
    rr   = row.get("resprate")
    o2   = row.get("o2sat")
    bt   = row.get("temperature")
    pain = row.get("pain")
    pain_str = str(pain) if not (isinstance(pain, float) and pd.isna(pain)) else "—"

    bp_abn = is_abnormal("sbp", bp_s) or is_abnormal("dbp", bp_d)
    bp_cls = "vital-abnormal" if bp_abn else "vital-normal"
    try:
        bp_display = f'<span class="{bp_cls}">{float(bp_s):.0f}/{float(bp_d):.0f}</span>'
    except (TypeError, ValueError):
        bp_display = "—"

    age_part = f"{age_display} / " if age_display else ""

    html = f"""
<div id="fixed-header">
  <div class="hdr-item">
    <span class="hdr-label">Case</span>
    <span class="hdr-value">{idx + 1} / {total}</span>
  </div>
  <div class="hdr-divider"></div>
  <div class="hdr-item">
    <span class="hdr-label">나이 / 성별</span>
    <span class="hdr-value">{age_part}{gender_str}</span>
  </div>
  <div class="hdr-divider"></div>
  <div class="hdr-item">
    <span class="hdr-label">Chief Complaint</span>
    <span class="hdr-value">{cc}</span>
  </div>
  <div class="hdr-divider"></div>
  <div class="hdr-item">
    <span class="hdr-label">Acuity</span>
    <span class="hdr-value">{acuity_badge(acuity_val)}</span>
  </div>
  <div class="hdr-divider"></div>
  <div class="hdr-item">
    <span class="hdr-label">내원경로</span>
    <span class="hdr-value">{transport}</span>
  </div>
  <div class="hdr-divider"></div>
  <div class="hdr-item"><span class="hdr-label">HR</span>
    <span class="hdr-value">{fmt_vital('heartrate', hr, '/min')}</span></div>
  <div class="hdr-item"><span class="hdr-label">BP</span>
    <span class="hdr-value">{bp_display}</span></div>
  <div class="hdr-item"><span class="hdr-label">RR</span>
    <span class="hdr-value">{fmt_vital('resprate', rr, '/min')}</span></div>
  <div class="hdr-item"><span class="hdr-label">O₂Sat</span>
    <span class="hdr-value">{fmt_vital('o2sat', o2, '%')}</span></div>
  <div class="hdr-item"><span class="hdr-label">BT</span>
    <span class="hdr-value">{fmt_vital('temperature', bt, '°C')}</span></div>
  <div class="hdr-item"><span class="hdr-label">Pain</span>
    <span class="hdr-value">{pain_str}</span></div>
</div>
<div class="main-content-offset"></div>
"""
    st.markdown(html, unsafe_allow_html=True)


def render_progress(done_cases: set, total: int) -> None:
    n = len(done_cases)
    pct = n / total if total else 0
    st.markdown(f"""
<div class="progress-container">
  <span style="font-size:13px;color:#1a3a5c;font-weight:600;">
    진행 현황: {n} / {total} 완료 ({pct * 100:.1f}%)
  </span>
</div>
""", unsafe_allow_html=True)
    st.progress(pct)
