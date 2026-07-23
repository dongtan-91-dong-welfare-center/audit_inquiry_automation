# src/utils/formatters.py

import re
from typing import List

CURRENCIES = ['KRW', 'USD', 'JPY', 'EUR', 'CNY', 'DM']

class FinancialTableFormatter:
    """
    [금융상품(예·적금) 테이블 전용 포매터(PaddleOCR 맞춤형)]
    * 상태를 저장할 필요가 없이 단순히 추출된 데이터를 가공하는 툴이기 때문에 모든 메서드는 @staticmethod 로 구성합니다.
    """

    @staticmethod
    def process(extracted_rows: List[List[str]], bank_name: str = "") -> List[List[str]]:
        """
        추출된 전체 행(Row) 데이터를 순회하며 금융상품 전용 정제 규칙을 적용합니다.
        
        Args:
            extracted_rows: OCR 엔진이 추출한 날것의 2차원 리스트
            bank_name: 은행명 (제주은행 10자리 규칙 등을 위해 전달)
        Returns:
            정제가 완료된 2차원 리스트
        """
        processed_data = []
        is_data_started = False  # 데이터 영역 진입 여부를 알리는 스위치
        for row in extracted_rows:
            # 1. 데이터 영역 시작 전(헤더 구간) 통화 기호 스캔
            # 첫 통화 기호가 나타나기 전까지의 행(컬럼명 등)만 버림.
            if not is_data_started:
                # 현재 행에 통화 기호가 단 하나라도 있는지 검사
                if any(currency in cell for cell in row for currency in CURRENCIES):
                    is_data_started = True  # 이후 데이터는 모두 실제 데이터로 간주하여 처리 시작
                else:
                    continue  # 스위치가 꺼져있고 통화 기호도 없으면 헤더이므로 스킵
            
            # 이후에 ocr 성능으로 인해 %를 인식하는 오류가 발생하는 경우, _merge_split_cells에 의해 
            # 원본 row를 그대로 반환하므로 데이터가 보존됨.(안전 장치)
            
            # 2. 구조적 오류 수정: 쪼개진 상품명 및 계좌번호 병합
            merged_row = FinancialTableFormatter._merge_split_cells(row, bank_name)
            
            # 3. 내용적 오류 수정: 금액 콤마, 오타 등 텍스트 교정
            formatted_row = FinancialTableFormatter._format_cells(merged_row)
            
            # 노이즈가 제거되어 텅 비어버린 리스트(행)는 최종 결과에서 제외
            if formatted_row:
                processed_data.append(formatted_row)
            
        return processed_data

    @staticmethod
    def _merge_split_cells(row: List[str], bank_name: str) -> List[str]:
        """
        (내부 헬퍼) 띄어쓰기나 기호 때문에 여러 칸으로 쪼개진 셀들을 원래대로 병합합니다.
        PaddleOCR 맞춤형으로, 화폐 열의 위치를 기반으로 역추적하여 병합을 수행합니다.
        """
        if not row:
            return row

        # =====================================================================
        # [규칙 1] 화폐 단위(Anchor) 기준 위치 탐색
        # 현상: OCR 인식 오류나 셀 쪼개짐으로 인해 계좌번호와 상품명의 인덱스가 매번 변동됨
        # 해결: 절대 변하지 않는 기준점인 '화폐 단위'를 찾아 그 앞의 데이터들을 역추적함
        # =====================================================================
        currency_idx = -1
        for i, cell in enumerate(row):
            if cell in CURRENCIES:
                currency_idx = i
                break
                
        # 화폐 단위를 찾지 못했거나 구조가 너무 짧으면 원본 반환 (안전 장치)
        if currency_idx < 2:
            return row
            
        currency_amount = row[currency_idx - 1]          # 화폐 단위 바로 앞은 무조건 '금액'
        front_parts = row[:currency_idx - 1]        # 금액 앞의 모든 파편들 (상품명 + 계좌번호 파편)
        
        if not front_parts:
            return row
            
        account_parts = []
        product_parts = []
        
        # =====================================================================
        # [규칙 2] 은행별 계좌번호 자릿수 기반 분리 (역순 탐색)
        # 현상: ['예금', '401', '1239-1382-69'] 처럼 하이픈 없이 계좌번호가 쪼개지거나 상품명이 누락됨
        # 해결: 계좌번호의 최대 길이(일반 14자리, 제주은행 10자리)를 기준으로 
        #       뒤에서부터 숫자를 누적하며 계좌번호와 상품명을 완벽하게 분리함
        # =====================================================================
        max_digits = 10 if bank_name == "제주은행" else 14
        accumulated_digits = 0
        is_account_zone = True  # 뒤에서부터 읽을 때 '계좌번호 영역'인지 표시하는 플래그
        
        for part in reversed(front_parts):
            # 정규표현식 r'\D' 해설: 숫자가 아닌 모든 문자(한글, 알파벳, 기호 등)를 지움 ('')
            num_digits = len(re.sub(r'\D', '', part))
            
            # 2-1. 이미 계좌번호 영역이 끝났다고 판별된 경우, 나머지는 전부 상품명으로 넣음
            if not is_account_zone:
                # 숫자만 존재하는 파편은 상품명 노이즈(예: '10')이므로 삭제 (빈칸 유지)
                if part.isdigit():
                    continue
                product_parts.insert(0, part)
                continue
                
            # 2-2. 숫자가 전혀 없는 한글/기호 덩어리를 만나면 계좌번호 영역 즉시 종료!
            if num_digits == 0:
                is_account_zone = False
                product_parts.insert(0, part)
                continue
                
            # 2-3. 목표 자릿수(10자리 또는 14자리)를 채우기 전까지는 
            #      하이픈 여부 상관없이 무조건 계좌번호 파편으로 흡수
            if accumulated_digits < max_digits and (accumulated_digits + num_digits) <= max_digits:
                account_parts.insert(0, part)
                accumulated_digits += num_digits
            else:
                # 2-4. 목표 자릿수를 모두 채웠다면, 그 앞의 텍스트(예: 상품명이 오인식된 '10')는 상품명으로 취급
                is_account_zone = False
                product_parts.insert(0, part)
                    
        # =====================================================================
        # [규칙 3] 파편화된 데이터 최종 조립 및 노이즈 제거
        # 현상: 계좌번호 중간에 콜론(:)이나 불필요한 공백, 연속된 하이픈(--)이 섞여 들어옴
        # 해결: 정규식을 이용하여 순수 숫자와 단일 하이픈(-)만 남기고 깨끗하게 병합함
        # =====================================================================
        product_name = "".join(product_parts)
        
        # 모든 계좌번호 파편을 하이픈(-)으로 강제 연결
        raw_account = "-".join(account_parts)
        
        # 정규표현식 r'[^\d\-]' 해설: 숫자(\d)와 하이픈(\-)이 아닌(^) 모든 것을 찾아 지움
        cleaned_account = re.sub(r'[^\d\-]', '', raw_account)  
        
        # 정규표현식 r'-+' 해설: 하이픈이 1개 이상 연속되는 패턴을 찾아 하나의 하이픈('-')으로 단일화
        # .strip('-') : 양끝에 덜렁거리는 불필요한 하이픈 제거
        merged_account = re.sub(r'-+', '-', cleaned_account).strip('-')
        
        # =====================================================================
        # [규칙 4] 최종 행(Row) 재조립
        # =====================================================================
        new_row = []
        new_row.append(product_name) # 누락되었으면 억지로 '예금'을 넣지 않고 빈 문자열("") 그대로 삽입 (컬럼 유지 및 검증 용이)
        new_row.append(merged_account)
        new_row.append(currency_amount)
        new_row.extend(row[currency_idx:]) # 화폐 단위부터 끝까지 그대로 붙임
        
        return new_row

    @staticmethod
    def _format_cells(row: List[str]) -> List[str]:
        """
        (내부 헬퍼) 구조가 잡힌 개별 셀 안에서 글자 오탈자 및 기호를 교정합니다.
        PaddleOCR이 인식하지 못한 쉼표(,), 마침표(.) 등의 기호를 문맥에 맞게 복구합니다.

        [확정된 컬럼 구조]
        [0] 금융상품의 종류 | [1] 계좌번호 | [2] 금액 | [3] 통화 | [4] 연이자율 | [5] 최종이자지급일 | [6] 만기일 | [7] 인출제한 등
        """
        formatted = []
        
        for idx, item in enumerate(row):
            item = item.strip()
            
            # =====================================================================
            # 구조 보존
            # 현상: 이전 단계(_merge_split_cells)에서 상품명이 누락되어 빈칸("")이 들어올 수 있음
            # 해결: 데이터 열(Column) 구조가 무너지지 않도록 빈칸을 그대로 유지하고 패스함
            # =====================================================================
            if not item:
                formatted.append("")
                continue

            # =====================================================================
            # [인덱스 0] 상품명
            # =====================================================================
            if idx == 0:
                pass

            # =====================================================================
            # [인덱스 1, 3] 계좌번호, 통화
            # =====================================================================
            elif idx in [1, 3]:
                pass

            # =====================================================================
            # [인덱스 2] 금액 콤마(,) 부활
            # =====================================================================
            elif idx == 2:
                digits = re.sub(r'\D', '', item)
                if digits:
                    item = f"{int(digits):,}"

            # =====================================================================
            # [인덱스 4] 이자율 마침표(.) 및 % 기호 부활
            # 규칙: 모든 이자율은 소수점 한 자리.
            # 단, OCR 오류로 정수부가 날아가 숫자 1개만 남은 경우 빈칸("") 처리.
            # =====================================================================
            elif idx == 4:
                digits = re.sub(r'\D', '', item)
                if len(digits) > 1:
                    # 마지막 1자리를 소수점 첫째 자리로 취급 (예: '03' -> '0.3%', '25' -> '2.5%')
                    integer_part = digits[:-1]
                    decimal_part = digits[-1]
                    item = f"{integer_part}.{decimal_part}%"
                else:
                    # 숫자가 없거나 1개뿐이면 데이터가 훼손된 것으로 보고 빈칸 처리
                    item = ""

            # =====================================================================
            # [인덱스 5, 6] 날짜 마침표(.) 부활 (YY.MM.DD)
            # =====================================================================
            elif idx in [5, 6]:
                digits = re.sub(r'\D', '', item)
                if len(digits) == 6:
                    item = f"{digits[:2]}.{digits[2:4]}.{digits[4:]}"
                elif len(digits) == 8: # YYYYMMDD 형태로 인식된 예외 케이스 방어
                    item = f"{digits[:4]}.{digits[4:6]}.{digits[6:]}"

            # =====================================================================
            # [인덱스 7 ] 비고 등 기타 컬럼
            # =====================================================================
            else:
                pass

            formatted.append(item)

        while len(formatted) < 8:
            formatted.append("")
            
        return formatted


class LoanTableFormatter:
    """
    [대출거래 테이블 전용 포매터 (PaddleOCR 맞춤형)]
    연이자율(%)을 닻(Anchor)으로 삼아 데이터를 9칸 구조로 확정하며,
    대출거래 테이블에서 발생하는 오류들을 정제합니다.
    """

    @staticmethod
    def process(extracted_rows: List[List[str]]) -> List[List[str]]:
        """
        추출된 대출거래 표의 전체 행(Row) 데이터를 순회하며 전용 정제 규칙을 적용합니다.
        """
        processed_data = []
        for row in extracted_rows:
            # =====================================================================
            # [최적화] 이자율(%)이 없는 헤더 및 노이즈 행은 시작부터 즉시 폐기
            # =====================================================================
            if not any('%' in cell for cell in row):
                continue

            # 구조적 오류 수정: 이자율(%) 기준 컬럼 재배치 (날짜 조립 및 금액 누락 방어)
            aligned_row = LoanTableFormatter._align_by_anchor(row)
            
            # 내용적 오류 수정: 확정된 9칸 인덱스 기반 포매팅
            formatted_row = LoanTableFormatter._format_cells(aligned_row)
            
            if formatted_row:
                processed_data.append(formatted_row)
            
        return processed_data

    @staticmethod
    def _align_by_anchor(row: List[str]) -> List[str]:
        """
        (내부 헬퍼) '%' 기호를 포함한 연이자율을 기준으로 데이터를 9칸으로 완벽하게 재조립합니다.
        [0]대출종류 | [1]약정한도액 | [2]대출금액 | [3]대출일 | [4]최종만기일 | [5]연이자율 | [6]최종이자지급일 | [7]상환방법 | [8]담보보증 및 관련약정
        """
        rate_idx = -1
        for i, cell in enumerate(row):
            if '%' in cell:
                rate_idx = i
                break

        front_parts = row[:rate_idx]
        back_parts = row[rate_idx + 1:]

        # =====================================================================
        # [앞부분(front_parts) 파싱 - 역순 탐색]
        # =====================================================================
        
        # 1. 최종만기일(Maturity Date) 조립: 뒤에서부터 숫자 6개가 찰 때까지 파편을 흡수
        maturity_digits = ""
        while front_parts and len(maturity_digits) < 6:
            part = front_parts.pop()
            maturity_digits = re.sub(r'\D', '', part) + maturity_digits

        # 2. 대출일(Loan Date) 조립: 뒤에서부터 숫자 6개가 찰 때까지 파편을 흡수
        loan_digits = ""
        while front_parts and len(loan_digits) < 6:
            part = front_parts.pop()
            loan_digits = re.sub(r'\D', '', part) + loan_digits

        # 3. 금액 2개(대출금액, 약정한도액) 및 대출종류 분리
        amounts = []
        types = []
        for part in reversed(front_parts):
            digits = re.sub(r'\D', '', part)
            # 숫자가 존재하고 아직 금액 2개를 다 못 찾았다면 금액으로 취급
            if digits and len(amounts) < 2:
                amounts.insert(0, digits)
            else:
                types.insert(0, part)
                
        loan_type = "".join(types)

        # 금액 누락 방어: 2개를 온전히 찾지 못하면 둘 다 "확인바람" 처리
        if len(amounts) == 2:
            limit_amount = amounts[0]
            balance = amounts[1]
        else:
            limit_amount = "확인바람"
            balance = "확인바람"

        # =====================================================================
        # [뒷부분(back_parts) 파싱 - 정순 탐색]
        # =====================================================================
        
        # 4. 이자지급일(Payment Date) 조립: 앞에서부터 숫자 6개가 찰 때까지 흡수
        pay_digits = ""
        while back_parts:
            # 숫자 6개를 채우기 전에 '만기일시', '비고' 등 날짜가 아닌 텍스트가 나오면 날짜 조립 종료 (예외 방어)
            digits = re.sub(r'\D', '', back_parts[0])
            if not digits:
                break
                
            pay_digits += digits
            back_parts.pop(0)
            if len(pay_digits) >= 6:
                break

        # 5. 상환방법(Repayment Method) 및 비고(Remarks)
        repayment_method = back_parts.pop(0) if back_parts else ""
        remarks = " ".join(back_parts) if back_parts else ""

        # 9칸 배열을 고정적으로 반환함으로써 표 구조 유지
        return [
            loan_type,
            limit_amount,
            balance,
            loan_digits,
            maturity_digits,
            row[rate_idx],
            pay_digits,
            repayment_method,
            remarks
        ]

    @staticmethod
    def _format_cells(row: List[str]) -> List[str]:
        """
        (내부 헬퍼) 9칸으로 확정된 인덱스를 기반으로 각 항목을 포매팅합니다.
        """
        if len(row) != 9:
            return row
            
        formatted = []
        
        for idx, item in enumerate(row):
            item = item.strip()
            if not item:
                formatted.append("")
                continue
                
            # [인덱스 0, 7, 8] 대출종류, 상환방법, 비고 (텍스트 원본 보존)
            if idx in [0, 7, 8]:
                pass

            # [인덱스 1, 2] 금액 및 잔액 콤마(,) 부활
            elif idx in [1, 2]:
                if item == "확인바람":
                    pass 
                else:
                    digits = re.sub(r'\D', '', item)
                    if digits:
                        item = f"{int(digits):,}"

            # [인덱스 3, 4, 6] 날짜 마침표(.) 부활 (YY.MM.DD)
            elif idx in [3, 4, 6]:
                digits = re.sub(r'\D', '', item)
                if len(digits) == 6:
                    item = f"{digits[:2]}.{digits[2:4]}.{digits[4:]}"
                elif len(digits) == 8: 
                    item = f"{digits[:4]}.{digits[4:6]}.{digits[6:]}"

            # [인덱스 5] 연이자율 마침표(.) 및 % 기호 부활 (소수점 1자리 통일)
            elif idx == 5:
                digits = re.sub(r'\D', '', item)
                if len(digits) > 1:
                    integer_part = digits[:-1]
                    decimal_part = digits[-1]
                    item = f"{integer_part}.{decimal_part}%"
                else:
                    item = ""

            formatted.append(item)
            
        return formatted