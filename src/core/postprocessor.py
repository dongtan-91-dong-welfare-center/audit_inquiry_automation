# src/core/postprocessor.py

from typing import List, Dict
from src.utils.formatters import FinancialTableFormatter
from src.utils.formatters import LoanTableFormatter

class PostProcessor:
    """
    [데이터 정제 총괄 매니저]
    OCR로 추출된 3차원 리스트 데이터를 받아,
    문서 내의 '대출' 키워드를 기준으로 금융상품과 대출거래 테이블을 분리하고
    각 테이블의 성격에 맞는 알맞은 포매터(Formatter)를 연결해 줍니다.
    """

    def __init__(self):
        # 사용할 각종 포매터들을 준비해 둡니다.
        self.financial_formatter = FinancialTableFormatter()
        self.loan_formatter = LoanTableFormatter()

    def process_data(self, extracted_tables: List[List[List[str]]], bank_name: str = "") -> Dict[str, List[List[str]]]:
        """
        추출된 표 데이터를 순회하며 '대출' 키워드를 기준으로 섹션을 나누고,
        각각 알맞은 정제 파이프라인을 가동합니다.

        Args:
            extracted_rows: OCR에서 추출된 날것의 전체 3차원 리스트 [표[행[칸]]]
            bank_name: 은행명 (제주은행 등 특정 은행의 계좌번호 길이 규칙 적용을 위해 필요)
        
        Returns:
            정제가 완료된 금융상품 표와 대출거래 표를 담은 딕셔너리
        """
        if not extracted_tables:
            return {"financial_table": [], "loan_table": []}

        financial_raw_rows = []
        loan_raw_rows = []
        
        is_loan_section = False  # 대출 섹션 진입 여부를 알리는 스위치

        for table in extracted_tables:
            if not is_loan_section:
                # 1. 스위치 켜기: 아직 금융상품 섹션일 때, 행 어딘가에 '대출'이라는 글자가 등장하면?
                if any('대출' in cell for row in table for cell in row):
                    is_loan_section = True # 해당 테이블은 대출거래 테이블로 확정
            for row in table:
                # 2. 스위치 상태에 따라 바구니에 나누어 담기 (자연스럽게 종류별로 병합됨)
                if is_loan_section:
                    loan_raw_rows.append(row)
                else:
                    financial_raw_rows.append(row)
        """
        TODO: 현재는 '대출' 키워드가 등장하는 순간부터 끝까지를 대출거래 테이블로 간주하는 단순한 로직입니다.
        현재는 파이썬3.14 버전과 가장 최신인 PaddleOcr3.4 버전의 의존성 관리가 어려워 Paddlecor 2.10 버전을 사용하고 있습니다. 
        향후 OCR 엔진이 업그레이드 되어 PP-Structure 모델을 적용한다면 지능적으로 같은 테이블로 인식할 가능성이 있습니다.
        이는 OCR 성능과도 직결되기 때문에 향후 실무에 사용하면서 고도화할 예정입니다.
        """

        # 3. 각각 나누어진 Raw 데이터 덩어리를 포매터에 던져서 최종 정제
        processed_financial = self.financial_formatter.process(financial_raw_rows, bank_name)
        processed_loan = self.loan_formatter.process(loan_raw_rows)

        # 4. 정제 완료된 두 개의 테이블을 딕셔너리로 묶어서 반환
        return {
            "financial_table": processed_financial,
            "loan_table": processed_loan
        }