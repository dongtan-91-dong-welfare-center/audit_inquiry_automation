"""
프로세서(Processor): 전체 작업 흐름을 관리하는 지휘관 모듈

[모듈 개요]
사용자가 요청한 PDF 파일을 받아서 최종 결과물인 엑셀 파일로 변환하는
'전체 과정(High-level Flow)'을 제어합니다.

직접 복잡한 계산을 수행하기보다는,
1. 추출 담당(extractor)에게 표를 찾아오라고 시키고,
2. 결과가 있으면 저장 담당(excel_writer)에게 엑셀로 만들라고 지시하는
중간 관리자 역할을 수행합니다.
"""

import os

# src 폴더 내의 다른 전문가(모듈)들을 데려옵니다.
# extractor: PDF에서 표 데이터를 긁어오는 역할 (Func-113)
from .extractor import extract_tables_from_pdf
# excel_writer: 데이터를 엑셀 파일로 예쁘게 포장하는 역할 (Func-151)
from .excel_writer import write_tables_to_excel
from .utils import setup_logger
from .exceptions import (
    PasswordProtectedError,
    FileCorruptedError,
    InvalidFilenameError,
    EmptyFileError,
    ExtractionError,
)


# 모듈 로거 초기화
logger = setup_logger(__name__)


def process_pdf_to_excel(pdf_path: str, output_path: str) -> int:
    """
    하나의 PDF 파일을 처리하여 엑셀 파일로 저장합니다.

    [작업 순서]
    1. PDF 읽기 및 표 추출 (Extractor 호출)
    2. 표가 있는지 확인 (없으면 중단)
    3. 저장할 폴더가 있는지 확인 (없으면 생성)
    4. 엑셀 파일 저장 (Writer 호출)

    Args:
        pdf_path (str): 처리할 원본 PDF 파일의 경로
        output_path (str): 결과 엑셀 파일을 저장할 경로 (파일명 포함)

    Returns:
        int: 추출 및 저장에 성공한 표의 개수.
             (0이 반환되면 표를 못 찾았다는 뜻이므로, 호출한 쪽에서 알림을 띄울 때 사용합니다.)
    """

    # 1. [데이터 추출] 전문 모듈(extractor)에게 PDF 분석을 맡깁니다.
    # tables 변수에는 추출된 표 데이터들(DataFrame 리스트)가 담깁니다.
    try:
        tables = extract_tables_from_pdf(pdf_path)
    except Exception as e:
        # 예외 메시지 기반 특수 처리 (암호화, 손상 등)
        msg = str(e)
        lower = msg.lower()
        if "password" in lower or "encrypted" in lower or "password required" in lower:
            logger.error("Failed to process %s: %s", pdf_path, msg)
            raise PasswordProtectedError(msg)

        # PDF 문법 오류 등은 FileCorruptedError로 래핑
        try:
            from pdfminer.pdfparser import PDFSyntaxError

            if isinstance(e, PDFSyntaxError):
                logger.error("Failed to process %s: %s", pdf_path, msg)
                raise FileCorruptedError(msg)
        except Exception:
            # pdfminer가 설치되지 않았거나, 다른 예외라면 무시하고 일반 처리로 넘어갑니다.
            pass

        logger.exception("Failed to process %s: %s", pdf_path, msg)
        raise ExtractionError(msg)

    # 2. [유효성 검사] 추출된 표가 하나도 없는 경우를 처리합니다.
    if not tables:
        # 표가 없는데 빈 엑셀 파일을 만드는 것은 무의미하므로 여기서 작업을 마칩니다.
        # 0을 반환하여 "아무것도 찾지 못했다"는 신호를 보냅니다.
        return 0

    # 3. [환경 설정] 결과물을 저장할 폴더가 실제로 존재하는지 확인합니다.
    # 예: 'result/output.xlsx'를 저장하려는데 'result' 폴더가 없으면 에러가 납니다.
    out_dir = os.path.dirname(output_path)

    # 폴더 경로가 지정되어 있고(!= 빈 문자열), 그 폴더가 아직 없다면
    if out_dir and not os.path.exists(out_dir):
        # 폴더를 새로 만듭니다. (exist_ok=True: 이미 있어도 에러 내지 말라는 뜻)
        os.makedirs(out_dir, exist_ok=True)

    # 4. [엑셀 저장] 전문 모듈(excel_writer)에게 데이터를 엑셀로 쓰라고 지시합니다.
    write_tables_to_excel(tables, output_path)

    # 5. [결과 보고] 총 몇 개의 표를 저장했는지 보고합니다.
    count = len(tables)
    logger.info("Processing complete: %s (Tables: %d)", pdf_path, count)
    return count