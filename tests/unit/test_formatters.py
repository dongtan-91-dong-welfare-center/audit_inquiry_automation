# tests/unit/test_formatters.py

import pytest
from src.utils.formatters import FinancialTableFormatter, LoanTableFormatter


class TestFinancialTableFormatterUnit:
    """FinancialTableFormatter (금융상품) 로직 검증"""

    @pytest.mark.unit
    def test_header_skipping(self):
        # Given: 통화 기호가 없는 헤더 2줄과 통화 기호(KRW)가 있는 데이터 1줄
        raw_data = [
            ["금융상품의 종류", "계좌번호", "잔액"],  # 스킵되어야 함
            ["(예금, 적금 등)", "(신규일)", "(원)"],  # 스킵되어야 함
            ["보통예금", "111-222-3333", "50000", "KRW", "00", "230101", "240101", "없음"]  # 처리되어야 함
        ]

        # When
        result = FinancialTableFormatter.process(raw_data)

        # Then: 헤더는 버려지고 실제 데이터 1줄만 8칸 구조로 반환되어야 함
        assert len(result) == 1
        assert result[0][0] == "보통예금"
        assert result[0][3] == "KRW"

    @pytest.mark.unit
    @pytest.mark.parametrize("bank_name, raw_row, expected_product, expected_account", [
        # 1. 일반 은행 (최대 14자리): 1234567890123 (13자리) -> 전부 계좌번호로 흡수, 앞의 '예금'만 금융상품의 종류
        ("국민은행", ["예금", "123", "456", "7890123", "10000", "KRW", "00"], "예금", "123-456-7890123"),

        # 2. 제주은행 (최대 10자리): 1234567890123 (13자리) -> 뒤에서 10자리만 계좌번호, 앞의 '123'은 금융상품의 종류로 밀려남
        ("제주은행", ["예금", "123", "456", "7890123", "10000", "KRW", "00"], "예금123", "456-7890123"),

        # 3. 노이즈 및 기호 혼입 케이스: 불필요한 공백, 연속된 하이픈, 콜론 등 제거 확인
        ("신한은행", ["정기", "예금", "111", ":222--", "-3333", "10000", "KRW", "00"], "정기예금", "111-222-3333")
    ])
    def test_merge_split_cells_and_bank_digits(self, bank_name, raw_row, expected_product, expected_account):
        result = FinancialTableFormatter.process([raw_row], bank_name=bank_name)

        assert len(result) == 1
        assert result[0][0] == expected_product
        assert result[0][1] == expected_account

    @pytest.mark.unit
    def test_formatting_and_column_consistency(self):
        # Given: 콤마 없는 금액, 마침표 없는 이자율, 마침표 없는 날짜, 그리고 7칸밖에 없는 짧은 데이터
        raw_row = ["정기예금", "111-222", "5000000", "KRW", "35", "230510", "240510"]

        # When
        result = FinancialTableFormatter.process([raw_row])

        # Then
        assert len(result[0]) == 8  # 무조건 8칸으로 패딩(Padding)되어야 함
        assert result[0][2] == "5,000,000"  # 금액 콤마 부활
        assert result[0][4] == "3.5%"  # 이자율 소수점 및 % 부활 ('35' -> '3.5%')
        assert result[0][5] == "23.05.10"  # 날짜 마침표 부활
        assert result[0][7] == ""  # 부족했던 8번째 칸은 빈 문자열로 채워짐
