# src/core/postprocessor.py

import pandas as pd
# TODO: src.utils.formatters에서 데이터 정제 함수들 임포트

class DataPostprocessor:
    """
    [데이터 정제 담당자]
    OCR로 추출된 원시 데이터를 DataFrame으로 만들고, 여러 데이터를 하나로 병합합니다.
    """
    def to_dataframe(self, raw_table_data):
        """
        개별 표 데이터를 pandas DataFrame으로 변환하고 1차 정제를 수행합니다.
        """
        # TODO: 추출된 데이터를 DataFrame 구조로 매핑
        # TODO: 완전히 비어있는 행/열(결측치) 제거
        # TODO: utils.formatters를 활용해 특정 컬럼의 데이터 형식 맞추기 (예: 이자율 포맷 변환)
        # return df
        pass

    def merge_dataframes(self, df_list):
        """
        여러 은행/조회처에서 추출된 DataFrame 리스트를 하나의 마스터 테이블로 병합합니다.
        """
        # TODO: 각 데이터프레임의 컬럼명을 하나로 통일 (예: '계좌 번호', '계좌번호' -> '계좌번호')
        # TODO: pd.concat을 사용해 행 방향(아래쪽)으로 병합
        # return merged_df
        pass