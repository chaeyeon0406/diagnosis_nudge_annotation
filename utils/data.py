import json
import pandas as pd
import streamlit as st
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent

# MIMIC-IV ED 체온은 화씨(°F) 저장 → 표시 시 섭씨(°C)로 변환
VITAL_RANGES = {
    "heartrate":   (60,   100),
    "resprate":    (12,   20),
    "o2sat":       (95,   100),
    "sbp":         (90,   140),
    "dbp":         (60,   90),
    "temperature": (36.1, 37.5),  # °C 기준 (비교 전 f_to_c() 적용)
}


def f_to_c(val) -> float | None:
    """화씨 → 섭씨 변환. 변환 불가 시 None 반환."""
    try:
        return (float(val) - 32) * 5 / 9
    except (TypeError, ValueError):
        return None

LAB_DISPLAY_COLS = ["charttime", "label", "valuenum", "valueuom",
                    "ref_range_lower", "ref_range_upper", "flag"]


def _download_csv_from_drive(file_id: str) -> pd.DataFrame:
    """Google Drive 파일 ID로 CSV를 다운로드해서 DataFrame으로 반환."""
    import io
    from google.oauth2.service_account import Credentials
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaIoBaseDownload

    scopes = ["https://www.googleapis.com/auth/drive.readonly"]
    creds = Credentials.from_service_account_info(
        dict(st.secrets["gcp_service_account"]), scopes=scopes
    )
    service = build("drive", "v3", credentials=creds)

    buf = io.BytesIO()
    request = service.files().get_media(fileId=file_id)
    downloader = MediaIoBaseDownload(buf, request)
    done = False
    while not done:
        _, done = downloader.next_chunk()
    buf.seek(0)
    return pd.read_csv(buf)


@st.cache_data(show_spinner="데이터 로딩 중...")
def load_data():
    drive = st.secrets["drive"]
    # T1/Tall radiology 파일이 기존 데이터 + radiology 컬럼을 모두 포함
    t0   = _download_csv_from_drive(drive["T0_file_id"])
    t1   = _download_csv_from_drive(drive["T1_radiology_file_id"])
    tall = _download_csv_from_drive(drive["Tall_radiology_file_id"])

    for df in (t0, t1, tall):
        if "target_disease" in df.columns:
            df.drop(columns=["target_disease"], inplace=True)
    return t0, t1, tall



def is_abnormal(key: str, val) -> bool:
    try:
        v = f_to_c(val) if key == "temperature" else float(val)
    except (TypeError, ValueError):
        return False
    if v is None:
        return False
    lo, hi = VITAL_RANGES.get(key, (None, None))
    return lo is not None and not (lo <= v <= hi)


def fmt_vital(key: str, val, unit: str = "") -> str:
    """temperature는 °F → °C 변환 후 표시."""
    try:
        display_val = f_to_c(val) if key == "temperature" else float(val)
        if display_val is None:
            raise ValueError
        display = f"{display_val:.1f}" if key == "temperature" else f"{display_val:.0f}"
    except (TypeError, ValueError):
        return '<span class="vital-normal">—</span>'
    cls = "vital-abnormal" if is_abnormal(key, val) else "vital-normal"
    return f'<span class="{cls}">{display}{unit}</span>'


def acuity_badge(acuity) -> str:
    try:
        lvl = int(float(acuity))
    except (TypeError, ValueError):
        return "—"
    labels = {1: "1-RESUS", 2: "2-EMER", 3: "3-URGENT", 4: "4-LESS", 5: "5-NON"}
    return f'<span class="acuity-badge acuity-{lvl}">{labels.get(lvl, lvl)}</span>'


def parse_json_col(val) -> list:
    if val is None or (isinstance(val, float) and pd.isna(val)) or val == "":
        return []
    try:
        return json.loads(str(val).replace("NaN", "null"))
    except Exception:
        return []


def resolve_age(row) -> tuple:
    """(age_int_or_None, display_str_or_None)"""
    for col in ("anchor_age", "age", "Age", "age_at_ed"):
        if col in row.index:
            try:
                v = int(float(row[col]))
                return v, f"{v}세"
            except (TypeError, ValueError):
                pass
    return None, None
