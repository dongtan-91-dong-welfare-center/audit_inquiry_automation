# src/utils/validators.py

import re

"""
[공통 유틸 담당자]
추출된 데이터가 상식적으로 올바른지(유효한지) 검사하는 함수 모음입니다.
"""

def is_valid_account_number(acc_str):
    """
    주어진 문자열이 계좌번호 형식에 부합하는지 정규식으로 판별합니다.
    """
    # TODO: 숫자와 하이픈(-)으로만 이루어져 있는지 확인하는 로직
    pass

def has_empty_essential_fields(row_data):
    """
    필수 데이터(예: 계좌번호, 잔액)가 누락되었는지 확인합니다.
    """
    # TODO: 필수 키(Key)값이 비어있는지 검증
    pass