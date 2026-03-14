# tests/unit/test_validators.py

import pytest
from src.utils.validators import is_valid_account_number, has_empty_essential_fields


class TestValidatorsUnit:
    """validators.py 내의 공통 유효성 검사 로직 검증 (TDD 명세)"""

    @pytest.mark.unit
    @pytest.mark.parametrize("account_str, expected", [
        # 1. 정상 케이스
        ("111-222-33333", True),  # 하이픈이 포함된 정상 계좌번호
        ("12345678901234", True),  # 하이픈 없이 숫자로만 이어진 정상 계좌번호

        # 2. 비정상 케이스 (문자 및 기호 혼입)
        ("111-abc-3333", False),  # 영문자 포함
        ("111*222*333", False),  # 하이픈(-)이 아닌 특수기호 포함
        ("111 222 333", False),  # 공백 포함

        # 3. 비정상 케이스 (길이 및 엣지 케이스)
        ("123", False),  # 너무 짧은 계좌번호 (최소 자릿수 미달)
        ("---", False),  # 하이픈만 존재하는 경우
        ("", False),  # 빈 문자열
        (None, False)  # None 입력 방어
    ])
    def test_is_valid_account_number(self, account_str, expected):
        """
        계좌번호가 숫자와 하이픈(-)으로만 구성되었는지,
        상식적인 최소 길이를 만족하는지 검증합니다.
        """
        assert is_valid_account_number(account_str) == expected

    @pytest.mark.unit
    def test_has_empty_essential_fields(self):
        """
        데이터 딕셔너리 내에 필수 키(Key)값이 비어있거나 누락되었는지 검증합니다.
        (현재 기획상 계좌번호와 잔액을 필수 필드로 가정)
        """
        # 1. 필수 필드가 모두 정상적으로 존재하는 경우 -> 누락 없음(False)
        valid_row = {
            "account_number": "111-222-333",
            "balance": "50,000",
            "product_name": "정기예금"
        }
        assert has_empty_essential_fields(valid_row) is False

        # 2. 필수 필드인 '계좌번호'가 빈 문자열인 경우 -> 누락 발생(True)
        missing_account = {
            "account_number": "",
            "balance": "50,000",
            "product_name": "정기예금"
        }
        assert has_empty_essential_fields(missing_account) is True

        # 3. 필수 필드인 '잔액'이 None인 경우 -> 누락 발생(True)
        missing_balance = {
            "account_number": "111-222-333",
            "balance": None,
            "product_name": "정기예금"
        }
        assert has_empty_essential_fields(missing_balance) is True

        # 4. 필수 필드 Key 자체가 딕셔너리에 없는 경우 -> 누락 발생(True)
        missing_key = {
            "product_name": "정기예금"
            # account_number, balance 키 부재
        }
        assert has_empty_essential_fields(missing_key) is True
