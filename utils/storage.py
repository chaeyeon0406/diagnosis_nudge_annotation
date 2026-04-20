# ──────────────────────────────────────────────────────────────────────────────
# Google Sheets 연동 저장 모듈
#
# [Streamlit Cloud 배포 시 secrets.toml 설정 방법]
#
# .streamlit/secrets.toml 파일에 아래 내용 추가:
#
#   [gcp_service_account]
#   type = "service_account"
#   project_id = "your-project-id"
#   private_key_id = "key-id"
#   private_key = "-----BEGIN RSA PRIVATE KEY-----\n...\n-----END RSA PRIVATE KEY-----\n"
#   client_email = "your-sa@your-project.iam.gserviceaccount.com"
#   client_id = "123456789"
#   auth_uri = "https://accounts.google.com/o/oauth2/auth"
#   token_uri = "https://oauth2.googleapis.com/token"
#   auth_provider_x509_cert_url = "https://www.googleapis.com/oauth2/v1/certs"
#   client_x509_cert_url = "https://www.googleapis.com/robot/v1/metadata/x509/..."
#
#   [sheets]
#   url = "https://docs.google.com/spreadsheets/d/YOUR_SHEET_ID/edit"
#
# Google Sheets 준비:
#   1. 스프레드시트에 "Reviewer_A", "Reviewer_B" 탭 생성
#   2. 각 탭 1행에 헤더 입력:
#      case_index | stay_id | reviewer | timepoint | timestamp |
#      aortic_dissection | myocardial_infarction | stroke | meningitis | sepsis | memo
#   3. 서비스 계정 이메일에 스프레드시트 편집 권한 부여
# ──────────────────────────────────────────────────────────────────────────────

import datetime
import pandas as pd
import streamlit as st

ANNOTATION_COLS = [
    "case_index", "stay_id", "reviewer", "timepoint", "timestamp",
    "aortic_dissection", "myocardial_infarction", "stroke",
    "meningitis", "sepsis", "memo",
]

DISEASE_COL_MAP = {
    "Aortic Dissection":     "aortic_dissection",
    "Myocardial Infarction": "myocardial_infarction",
    "Stroke":                "stroke",
    "Meningitis":            "meningitis",
    "Sepsis":                "sepsis",
}

# reviewer 이름 → 시트 탭 이름 매핑
SHEET_TAB_MAP = {
    "김민하 교수님": "Reviewer A (김민하)",
    "맹승진 교수님": "Reviewer B (맹승진)",
}


# ── Google Sheets 연결 (캐싱) ─────────────────────────────────────────────────

@st.cache_resource
def _get_spreadsheet():
    """gspread 연결 객체를 캐싱해서 재인증 비용 제거."""
    import gspread
    from google.oauth2.service_account import Credentials

    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
    ]
    creds = Credentials.from_service_account_info(
        dict(st.secrets["gcp_service_account"]),
        scopes=scopes,
    )
    gc = gspread.authorize(creds)
    return gc.open_by_url(st.secrets["sheets"]["url"])


def _get_worksheet(reviewer: str):
    tab_name = SHEET_TAB_MAP.get(reviewer, reviewer)
    try:
        return _get_spreadsheet().worksheet(tab_name)
    except Exception:
        # 캐시된 연결이 끊겼을 가능성 → 캐시 초기화 후 재연결
        _get_spreadsheet.clear()
        return _get_spreadsheet().worksheet(tab_name)


# ── 데이터 읽기 ───────────────────────────────────────────────────────────────

def load_annotations(reviewer: str) -> pd.DataFrame:
    """해당 reviewer 탭의 전체 데이터를 DataFrame으로 반환."""
    try:
        ws = _get_worksheet(reviewer)
        records = ws.get_all_records(default_blank=None)
        if not records:
            return pd.DataFrame(columns=ANNOTATION_COLS)
        df = pd.DataFrame(records)
        if "case_index" in df.columns:
            df["case_index"] = pd.to_numeric(df["case_index"], errors="coerce")
        return df
    except Exception as e:
        st.error(f"Google Sheets 읽기 실패: {e}")
        return pd.DataFrame(columns=ANNOTATION_COLS)


def done_cases_from_df(ann: pd.DataFrame) -> set:
    """이미 로드된 DataFrame에서 T0+T1+Tall 모두 완료된 case_index 집합 반환."""
    if ann.empty or "case_index" not in ann.columns or "timepoint" not in ann.columns:
        return set()
    t0   = set(ann[ann["timepoint"] == "T0"  ]["case_index"].dropna().astype(int).tolist())
    t1   = set(ann[ann["timepoint"] == "T1"  ]["case_index"].dropna().astype(int).tolist())
    tall = set(ann[ann["timepoint"] == "Tall"]["case_index"].dropna().astype(int).tolist())
    return t0 & t1 & tall


def get_done_cases(reviewer: str) -> set:
    """Sheets에서 직접 읽어 완료 케이스 집합 반환 (admin 등 외부 호출용)."""
    return done_cases_from_df(load_annotations(reviewer))


# ── 데이터 저장 ───────────────────────────────────────────────────────────────

def save_annotation(reviewer: str, case_idx: int, stay_id,
                    timepoint: str, answers: dict, memo: str) -> bool:
    """
    저장 성공 → True, 실패 → False.
    같은 case_index + timepoint 조합이 이미 있으면 해당 행을 덮어씀.
    """
    new_row = {
        "case_index": case_idx,
        "stay_id":    stay_id,
        "reviewer":   reviewer,
        "timepoint":  timepoint,
        "timestamp":  datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "memo":       (memo or "").strip(),
        **{DISEASE_COL_MAP[k]: v for k, v in answers.items() if k in DISEASE_COL_MAP},
    }
    row_values = [str(new_row.get(col, "")) for col in ANNOTATION_COLS]

    try:
        ws = _get_worksheet(reviewer)
        existing = ws.get_all_values()  # [[헤더행], [데이터행], ...]

        # 시트가 완전히 비어 있으면 헤더부터 추가
        if len(existing) < 1:
            ws.append_row(ANNOTATION_COLS)
            ws.append_row(row_values)
            st.success(f"{timepoint} 저장되었습니다.")
            return True

        header = existing[0]

        # 헤더가 없거나 최신 스키마가 아니면 헤더 행 교체
        if header != ANNOTATION_COLS:
            ws.update("A1", [ANNOTATION_COLS])
            header = ANNOTATION_COLS

        # case_index / timepoint 열 위치
        try:
            ci_col = header.index("case_index")   # 0-based
            tp_col = header.index("timepoint")    # 0-based
        except ValueError:
            ws.insert_row(ANNOTATION_COLS, index=1)
            ws.append_row(row_values)
            st.success(f"{timepoint} 저장되었습니다.")
            return True

        # case_index + timepoint 일치 행 탐색 (2행부터, 1-based row index는 i+1)
        target_row = None
        for i, row in enumerate(existing[1:], start=2):
            if (len(row) > ci_col and str(row[ci_col]) == str(case_idx) and
                    len(row) > tp_col and str(row[tp_col]) == timepoint):
                target_row = i
                break

        if target_row:
            col_letter_end = _col_letter(len(ANNOTATION_COLS))
            ws.update(
                f"A{target_row}:{col_letter_end}{target_row}",
                [row_values],
            )
        else:
            ws.append_row(row_values)

        st.success(f"{timepoint} 저장되었습니다.")
        return True

    except Exception as e:
        st.error(f"저장 실패: {e}")
        return False


def _col_letter(n: int) -> str:
    """1-based 컬럼 번호 → 스프레드시트 열 문자 (A, B, …, Z, AA, …)"""
    result = ""
    while n > 0:
        n, remainder = divmod(n - 1, 26)
        result = chr(65 + remainder) + result
    return result
