import streamlit as st
from ui.admin import render_admin_login_sidebar


def render_sidebar(reviewer: str, done_cases: set, total: int) -> None:
    with st.sidebar:
        cur_idx = st.session_state.case_idx

        st.markdown(f"**{reviewer}**")
        st.divider()

        # 현재 케이스 번호
        st.markdown(
            f"<div style='text-align:center; font-size:1.5rem; font-weight:700; "
            f"color:#1a3a5c; padding:8px 0;'>Case {cur_idx + 1:03d} / {total}</div>",
            unsafe_allow_html=True,
        )

        # 이전 / 다음 버튼
        col_prev, col_next = st.columns(2)
        with col_prev:
            if st.button("← 이전", disabled=(cur_idx == 0), use_container_width=True):
                st.session_state.case_idx -= 1
                st.rerun()
        with col_next:
            if st.button("다음 →", disabled=(cur_idx >= total - 1), use_container_width=True):
                st.session_state.case_idx += 1
                st.rerun()

        st.divider()

        # 케이스 직접 이동
        st.markdown("**케이스 이동**")
        jump_val = st.number_input(
            "케이스 번호",
            min_value=1, max_value=total,
            value=cur_idx + 1,
            step=1,
            label_visibility="collapsed",
            key="sidebar_jump",
        )
        if st.button("이동", use_container_width=True):
            st.session_state.case_idx = int(jump_val) - 1
            st.rerun()

        st.divider()

        # 전체 진행률
        n_done = len(done_cases)
        pct = n_done / total if total else 0
        st.markdown("**전체 진행률**")
        st.progress(pct)
        st.markdown(
            f"<div style='text-align:center; color:#555; font-size:0.88rem;'>"
            f"완료: {n_done} / {total} ({pct * 100:.0f}%)</div>",
            unsafe_allow_html=True,
        )

        st.divider()

        # 케이스별 완료 현황 (Sheets 기록 기준)
        with st.expander("케이스 목록", expanded=False):
            cells = []
            for i in range(total):
                is_done = i in done_cases
                is_cur  = i == cur_idx
                mark = "✅" if is_done else "○"
                bg   = "#dbeafe" if is_cur else ("#d4edda" if is_done else "transparent")
                fw   = "bold"   if is_cur else "normal"
                cells.append(
                    f"<span style='display:inline-block;min-width:38px;"
                    f"text-align:center;font-size:0.7rem;padding:2px 3px;"
                    f"margin:1px;border-radius:4px;background:{bg};"
                    f"font-weight:{fw};line-height:1.5'>"
                    f"{mark}<br>"
                    f"<span style='font-size:0.65rem;color:#444'>{i + 1}</span>"
                    f"</span>"
                )
            st.markdown(
                "<div style='line-height:1'>" + "".join(cells) + "</div>",
                unsafe_allow_html=True,
            )

        render_admin_login_sidebar()
