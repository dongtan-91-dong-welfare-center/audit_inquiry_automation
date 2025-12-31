"""
공통 유틸리티(Utilities): 보조 도구 모음

[모듈 개요]
프로젝트의 여러 곳에서 공통적으로 사용될 수 있는 '작은 기능'들을 모아둔 파일입니다.
현재는 뼈대만 잡혀 있으며, 추후 구체적인 로직을 채워 넣을 예정입니다.

[향후 구현 계획]
- 데이터 정제 로직 (Req-122: 0/O 보정 등)
- 데이터 검증 로직 (날짜 형식 확인 등)
"""

import logging
from logging.handlers import RotatingFileHandler
from .config import Config


def extract_table_data(text):
    """
    [예정 기능] 텍스트 기반 데이터 추출

    OCR이나 PDF 파서가 읽어온 덩어리 텍스트(Raw Text)에서,
    정규표현식(Regex) 등을 사용하여 우리가 원하는 알맹이 데이터만 쏙 뽑아내는 함수입니다.

    (현재는 extractor.py에서 처리하고 있으나, 복잡한 텍스트 파싱이 필요하면 이곳으로 분리합니다.)
    """
    pass


def clean_data(data):
    """
    [예정 기능] 데이터 정제 (Data Cleaning)

    추출된 데이터에 섞여 있는 노이즈를 제거합니다.

    [구현 예정 로직]
    - Req-122: 유사 문자 보정 (예: 숫자 0과 알파벳 O, 숫자 1과 소문자 l 구분)
    - 앞뒤 불필요한 공백 제거 (Trim)
    - 특수문자 제거
    """
    pass


def validate_data(data):
    """
    [예정 기능] 데이터 유효성 검사 (Validation)

    데이터가 우리가 원하는 규칙에 맞는지 검사하는 '품질 관리(QC)' 단계입니다.

    [구현 예정 로직]
    - 필수 항목(금액, 날짜 등)이 비어있지 않은지 확인
    - 날짜 형식이 'YYYY-MM-DD'에 맞는지 확인
    """
    pass


def format_data_for_export(data):
    """
    [예정 기능] 내보내기용 포맷팅

    엑셀 생성기(excel_writer)에게 넘겨주기 전에,
    데이터를 엑셀에 넣기 좋은 모양으로 예쁘게 다듬는 과정입니다.
    """
    pass


def parse_filename(filename: str) -> dict | None:
        """
        파일명 파싱 및 유효성 검사 (Func-111)

        - Configurations.csv의 CONF-006 (FILENAME_PARSE_REGEX) 패턴을 사용합니다:
            ^(?P<audited_company>.+?)\d+(?P<inquired_company>.+?)$
        - 확장자가 있는 경우 제거한 뒤 정규식을 적용합니다.

        반환값:
            - 매칭 성공: {'audited_company': str, 'inquired_company': str}
            - 매칭 실패: None  # 파일명 형식이 올바르지 않음 (CONF-006 위반)
        """
        import re
        import os

        if not filename or not isinstance(filename, str):
                return None

        # 확장자 제거 (.pdf 등)
        basename, _ = os.path.splitext(filename)

        pattern = r"^(?P<audited_company>.+?)\d+(?P<inquired_company>.+?)$"
        m = re.match(pattern, basename)
        if not m:
                # 파일명 형식이 올바르지 않음 (CONF-006 위반)
                return None

        return {
                'audited_company': m.group('audited_company'),
                'inquired_company': m.group('inquired_company'),
        }


def setup_logger(name: str | None = None, log_file: str = 'app.log') -> logging.Logger:
        """
        로거 설정 유틸리티 (Func-143)

        - 로그 레벨은 `Config.LOG_LEVEL`을 참조합니다.
        - 콘솔 출력(StreamHandler)과 파일 출력(RotatingFileHandler)을 모두 설정합니다.
        - 포맷: [%(levelname)s] %(asctime)s - %(module)s: %(message)s
        """
        logger = logging.getLogger(name)

        # 이미 핸들러가 설정되어 있으면 재설정하지 않음
        if logger.handlers:
            return logger

        level_name = getattr(Config, 'LOG_LEVEL', 'INFO')
        level = getattr(logging, level_name.upper(), logging.INFO)
        logger.setLevel(level)

        fmt = logging.Formatter("[%(levelname)s] %(asctime)s - %(module)s: %(message)s")

        sh = logging.StreamHandler()
        sh.setLevel(level)
        sh.setFormatter(fmt)

        fh = RotatingFileHandler(log_file, maxBytes=1024 * 1024, backupCount=3, encoding='utf-8')
        fh.setLevel(level)
        fh.setFormatter(fmt)

        logger.addHandler(sh)
        logger.addHandler(fh)

        return logger