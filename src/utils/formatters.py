# src/utils/formatters.py

"""
[공통 유틸 담당자]
문자열이나 숫자의 형식을 변환하는 순수 함수(Pure Function) 모음입니다.
"""

def format_interest_rate(rate_str):
    """
    인식된 이자율 문자열을 표준 퍼센트(%) 형식으로 변환합니다.
    예: "6.99" -> "6.99%", "5.5%" -> "5.5%"
    """
    # TODO: 문자열에 '%'가 없으면 추가하고, 공백 제거 등의 로직 구현
    pass

def clean_currency_amount(amount_str):
    """
    금액 텍스트에서 쉼표(,)나 '원' 글자를 제거하고 숫자로 변환합니다.
    예: "1,234,567 원" -> 1234567
    """
    # TODO: 정규표현식(re)이나 문자열 대체(replace)를 활용한 필터링
    pass

def standardize_account_number(acc_str):
    """
    계좌번호의 하이픈(-)을 유지하거나 제거하는 등 일관된 포맷으로 맞춥니다.
    """
    # TODO: 계좌번호 포맷팅 로직 구현
    pass