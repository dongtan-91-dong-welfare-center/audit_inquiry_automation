# tests/unit/test_postprocessor.py

import pytest
from unittest.mock import patch
from src.core.postprocessor import PostProcessor


class TestPostProcessorUnit:
    """PostProcessor의 데이터 분류 및 섹션 분리 로직 검증"""

    @pytest.fixture(autouse=True)
    def setup(self):
        """포매터들의 실제 로직을 실행하지 않도록 Mocking 처리"""
        with patch('src.core.postprocessor.FinancialTableFormatter') as MockFinancial, \
            patch('src.core.postprocessor.LoanTableFormatter') as MockLoan:
            self.processor = PostProcessor()
            self.mock_financial = MockFinancial.return_value
            self.mock_loan = MockLoan.return_value

            # 포매터가 입력받은 리스트를 그대로 반환하도록 기본 설정 (검증 용이성)
            self.mock_financial.process.side_effect = lambda x, name: x
            self.mock_loan.process.side_effect = lambda x: x

    @pytest.mark.unit
    def test_process_data_splitting_logic(self):
        """'대출' 키워드 발견 시점을 기준으로 데이터가 정확히 분리되는지 검증"""
        # Given: 금융상품 표 1개와 대출 키워드가 포함된 표 1개
        extracted_tables = [
            [["예금종류", "계좌번호"], ["보통예금", "111-222"]],  # 표 1 (금융상품)
            [["대출종류", "대출금액"], ["신용대출", "50,000,000"]]  # 표 2 (대출거래 시작)
        ]

        # When
        result = self.processor.process_data(extracted_tables)

        # Then
        # 1. '대출' 키워드 이전의 행들은 financial_table로 가야 함
        assert result["financial_table"] == [["예금종류", "계좌번호"], ["보통예금", "111-222"]]

        # 2. '대출' 키워드가 포함된 행부터 끝까지는 loan_table로 가야 함
        assert result["loan_table"] == [["대출종류", "대출금액"], ["신용대출", "50,000,000"]]

    @pytest.mark.unit
    def test_process_data_no_loan_keyword(self):
        """'대출' 키워드가 없을 때 모든 데이터가 금융상품으로 분류되는지 검증"""
        # Given: 대출 관련 단어가 아예 없는 데이터
        extracted_tables = [[["예금종류", "잔액"], ["정기예금", "100,000"]]]

        # When
        result = self.processor.process_data(extracted_tables)

        # Then: loan_table은 비어있어야 함
        assert len(result["financial_table"]) == 2
        assert len(result["loan_table"]) == 0

    @pytest.mark.unit
    def test_process_data_empty_input(self):
        """빈 데이터 입력 시 에러 없이 기본 구조를 반환하는지 검증"""
        # When
        result = self.processor.process_data([])

        # Then: 기본 딕셔너리 구조 반환 확인
        assert result == {"financial_table": [], "loan_table": []}

    @pytest.mark.unit
    def test_formatter_parameter_passing(self):
        """bank_name이 FinancialTableFormatter로 잘 전달되는지 검증"""
        # Given
        extracted_tables = [[["데이터"]]]
        test_bank = "제주은행"

        # When
        self.processor.process_data(extracted_tables, bank_name=test_bank)

        # Then: 포매터의 process 메서드가 올바른 bank_name과 함께 호출되었는지 확인
        self.mock_financial.process.assert_called_once_with([["데이터"]], test_bank)
