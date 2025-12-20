"""
탐지(Detection) 모듈: 추출 기능을 감싸는 껍데기(Wrapper)

[모듈 개요]
이 모듈은 독자적인 로직을 가지고 있지 않습니다.
핵심 엔진인 'extractor.py'의 기능을 가져와서,
'detect_tables'(표 감지)라는 좀 더 일반적인 이름으로 포장해주는 역할을 합니다.

[왜 필요한가요?]
1. 의미 전달: 'PDF에서 추출한다'는 구체적인 행위보다 '표를 감지한다'는 추상적인 표현이 필요할 때 사용합니다.
2. 테스트 용이성: 테스트 코드에서 이 함수를 호출하여 표가 잘 찾아지는지 확인합니다.
"""

from typing import List
import pandas as pd

# 실제 일꾼인 extractor 모듈에서 함수를 데려옵니다.
from .extractor import extract_tables_from_pdf


def detect_tables(pdf_path: str) -> List[pd.DataFrame]:
    """
    지정된 PDF 파일에서 표를 찾아서 반환합니다.

    [동작 방식]
    직접 일을 하지 않고, extractor.py의 extract_tables_from_pdf 함수에게
    일을 그대로 토스(Pass)합니다.

    Args:
        pdf_path (str): 분석할 PDF 파일의 경로

    Returns:
        List[pd.DataFrame]: 찾아낸 표들의 리스트
    """
    return extract_tables_from_pdf(pdf_path)