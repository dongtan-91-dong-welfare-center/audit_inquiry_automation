import streamlit as st
import pandas as pd
from io import BytesIO

st.set_page_config(layout="wide", page_title="금융거래조회서 키인 자동화")

# 설정
st.sidebar.title("설정")
conf_use_correction = st.sidebar.checkbox(
    "유사 문자 자동 보정",
    value=True
)

# 메인 화면
st.title("📄 금융거래조회서 키인 자동화")

# 파일 업로드
uploaded_files = st.file_uploader(
    "조회서 PDF 파일(들)을 업로드하세요",
    type="pdf",
    accept_multiple_files=True
)

# 처리 시작
if st.button("엑셀 변환 시작", type="primary", disabled=(not uploaded_files)):

    if uploaded_files:
        st.toast(f"{len(uploaded_files)}개 파일 처리 시작...")

        # (향후 구현) 이 곳에서 파일들을 반복하며 핵심 로직 호출

        # (임시) 지금은 더미 데이터로 엑셀 생성
        dummy_data = {"계정과목": ["현금"], "금액": [1000]}
        df = pd.DataFrame(dummy_data)

        try:
            # 엑셀 생성
            # (임시) 엑셀 파일 생성 로직
            output_buffer = BytesIO()
            df.to_excel(output_buffer, index=False, engine="openpyxl")
            excel_bytes = output_buffer.getvalue()

            st.success("처리 완료! 아래 버튼으로 다운로드하세요.")

            # 결과 다운로드
            st.download_button(
                label="✅ 최종 원엑셀 다운로드",
                data=excel_bytes,
                file_name="financial_report_output.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

        except Exception as e:
            # 오류 표시
            st.error(f"처리 중 오류 발생: {e}")