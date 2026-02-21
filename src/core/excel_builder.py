# src/core/excel_builder.py

import pandas as pd
import io

class ExcelBuilder:
    """
    [출력 담당자]
    최종 병합된 데이터를 다운로드 가능한 엑셀 파일(.xlsx)로 생성합니다.
    """
    def generate_excel_bytes(self, final_df, company_name):
        """
        DataFrame을 엑셀 파일 형태의 바이트 스트림으로 변환합니다.
        """
        # TODO: io.BytesIO()를 사용해 메모리 버퍼 생성
        # TODO: pd.ExcelWriter를 사용하여 final_df를 버퍼에 작성 (엔진: openpyxl 등)
        
        # TODO: (선택) 금액 컬럼 콤마(,) 서식 지정, 헤더 셀 배경색 등 엑셀 스타일링 적용
        
        # return 바이트 데이터 (Streamlit st.download_button의 data 파라미터로 전달용)
        pass