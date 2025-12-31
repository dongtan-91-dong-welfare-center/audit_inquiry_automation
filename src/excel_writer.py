"""
엑셀 생성기(Excel Writer): 최종 결과물 제작 모듈

[모듈 개요]
앞선 단계(Extractor)에서 추출한 표 데이터들을 모아서,
사용자에게 익숙한 '엑셀 파일(.xlsx)' 형태로 포장해주는 역할을 합니다.

[핵심 기능]
- Req-141 (원클릭 원엑셀 생성): 여러 개의 표를 하나의 엑셀 파일 안에 시트별로 정리해서 저장합니다.
- 사용자는 이 결과물을 열어서 바로 감사 조서 작업에 활용할 수 있습니다.
"""

from typing import List
import pandas as pd


def write_tables_to_excel(tables: List[pd.DataFrame], output_path: str) -> None:
    """
    추출된 데이터(표) 목록을 하나의 엑셀 파일로 저장합니다.

    [동작 방식]
    1. 엑셀 파일을 생성할 준비를 합니다.
    2. 추출된 표의 개수만큼 반복하며 시트(Sheet)를 만듭니다. (예: table_1, table_2...)
    3. 각 시트에 데이터를 채워 넣고 저장합니다.

    Args:
        tables (List[pd.DataFrame]): 추출된 표 데이터들의 리스트
        output_path (str): 파일을 저장할 경로 (예: result/final_result.xlsx)

    Returns:
        None: 파일 생성에 성공하면 아무것도 반환하지 않습니다.
    """

    # [유효성 검사] 저장할 표가 하나도 없다면 엑셀 파일을 만들지 않고 종료합니다.
    # 빈 파일을 만들면 사용자가 혼란스러워할 수 있기 때문입니다.
    if not tables:
        return

    # 엑셀 파일 작성 도구(Writer)를 엽니다. 엔진은 openpyxl을 사용합니다.
    # ('with' 문법을 사용하면 저장이 끝난 후 파일을 자동으로 안전하게 닫아줍니다.)
    with pd.ExcelWriter(output_path, engine="openpyxl") as writer:

        # 리스트에 있는 표들을 하나씩 꺼내서 순서대로 저장합니다.
        # idx는 1부터 시작합니다. (table_1, table_2, ...)
        for idx, df in enumerate(tables, start=1):
            sheet_name = f"table_{idx}"

            # [데이터 쓰기]
            # 시트 이름이 너무 길거나 특수문자가 있으면 엑셀에서 에러가 날 수 있으므로,
            # 추후 필요하다면 여기서 이름을 다듬는 로직(Sanitization)을 추가할 수 있습니다.

            # index=False: 판다스가 내부적으로 사용하는 행 번호(0, 1, 2...)는
            # 사용자에게 불필요한 정보이므로 엑셀에는 기록하지 않습니다.
            df.to_excel(writer, sheet_name=sheet_name, index=False)