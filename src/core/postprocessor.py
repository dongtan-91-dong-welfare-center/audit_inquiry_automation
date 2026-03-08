# src/core/postprocessor.py

from typing import List
from src.utils.formatters import FinancialTableFormatter

class PostProcessor:
    """
    [데이터 정제 총괄 매니저]
    OCR로 추출된 2차원 리스트 데이터를 받아,
    테이블의 성격(예: 금융상품, 차입금 등)에 맞는 알맞은 포매터(Formatter)를 연결해 줍니다.
    """

    def __init__(self):
        # 사용할 각종 포매터들을 준비해 둡니다.
        self.financial_formatter = FinancialTableFormatter()
        # self.loan_formatter = LoanTableFormatter()  <- 나중에 0004번 파일용으로 추가될 부분

    def process_data(self, extracted_rows: List[List[str]], table_type: str = "financial") -> List[List[str]]:
        """
        테이블 종류에 맞는 정제 파이프라인을 가동합니다.
        
        Args:
            extracted_rows: OCR에서 추출된 날것의 2차원 리스트
            table_type: 식별된 테이블의 종류 (기본값은 'financial'로 임시 고정)
        """
        if not extracted_rows:
            return []

        # 1. 예·적금 (금융상품) 테이블인 경우
        if table_type == "financial":
            return self.financial_formatter.process(extracted_rows)
            
        # 2. 대출/차입금 테이블인 경우 (예시)
        # elif table_type == "loan":
        #     return self.loan_formatter.process(extracted_rows)
            
        # 3. 알 수 없는 테이블인 경우 원본 그대로 반환
        else:
            return extracted_rows