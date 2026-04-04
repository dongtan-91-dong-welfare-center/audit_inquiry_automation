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

class TestLoanTableFormatterUnit:
    """LoanTableFormatter (대출거래) 로직 검증"""

    @pytest.mark.unit
    def test_filter_valid_data(self):
        # '%' 기호가 없는 헤더나 노이즈는 버려져야 함
        raw_data = [
            ["대출과목", "대출금액", "이율", "만기일"],
            ["신용대출", "50,000,000", "5.5%", "24.12.31"]  # 이 줄만 통과해야 함
        ]
        result = LoanTableFormatter.process(raw_data)

        assert len(result) == 1
        assert "5.5%" in result[0]

    @pytest.mark.unit
    def test_alignment_and_fragment_recovery(self):
        # Given: '%' 기준 앞뒤로 잘게 쪼개진 엉망진창 데이터
        # 구조: [대출종류파편1, 2, 약정한도, 대출금액, 대출일파편1, 2, 만기일파편1, 2, 이자율(%), 이자지급일파편1, 2, 상환방법]
        raw_row = [
            "일반", "자금대출", "100000000", "50000000", "23", "0101", "24", "1231",
            "45%",
            "23", "0531", "만기일시상환"
        ]

        # When
        result = LoanTableFormatter.process([raw_row])
        row = result[0]

        # Then: 9칸 표준 구조로 완벽히 재조립되어야 함
        assert len(row) == 9
        assert row[0] == "일반자금대출"  # 대출종류 병합
        assert row[1] == "100,000,000"  # 약정한도 콤마 부활
        assert row[2] == "50,000,000"  # 대출금액 콤마 부활
        assert row[3] == "23.01.01"  # 대출일 병합 및 포매팅
        assert row[4] == "24.12.31"  # 만기일 병합 및 포매팅
        assert row[5] == "4.5%"  # 이자율 포매팅
        assert row[6] == "23.05.31"  # 이자지급일 병합 및 포매팅
        assert row[7] == "만기일시상환"  # 상환방법

    @pytest.mark.unit
    def test_missing_amount_defense(self):
        # Given: 이율(%) 앞부분에 숫자로 된 금액 데이터가 아예 없는 예외 상황
        raw_row = ["신용대출", "230101", "241231", "55%", "230531"]

        # When
        result = LoanTableFormatter.process([raw_row])
        row = result[0]

        # Then: 프로그램이 죽지 않고, 금액 2칸(약정한도, 대출금액)을 "확인바람"으로 채워야 함
        assert row[1] == "확인바람"
        assert row[2] == "확인바람"
