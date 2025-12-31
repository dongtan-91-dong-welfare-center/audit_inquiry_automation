"""
OCR(광학 문자 인식) 처리 모듈

[모듈 개요]
이미지(Image) 형태의 문서에서 글자(Text)를 읽어내는 기능을 담당합니다.
외부 OCR 라이브러리(pytesseract 등)를 직접 사용하는 대신, 이 모듈을 통해 사용함으로써
기술적인 세부 사항을 감추고 '인터페이스' 역할을 합니다.

[아키텍처 포인트: 캡슐화]
현재는 `pytesseract`를 사용하고 있지만, 나중에 더 성능이 좋은 `PaddleOCR` 등으로
엔진을 교체해야 할 때(ADR-001 수정 반영 시), 이 파일 내부만 수정하면
전체 시스템에 영향을 주지 않고 업그레이드가 가능합니다.
"""

from typing import Optional
from PIL import Image

# OCR 기능을 제공하는 외부 라이브러리 (Tesseract)
import pytesseract


def image_to_text(img: Image.Image, lang: Optional[str] = None) -> str:
    """
    이미지 데이터를 입력받아 포함된 텍스트를 추출하여 반환합니다.

    [기능 설명]
    1. 외부 OCR 엔진에게 이미지를 전달합니다.
    2. 엔진이 읽어낸 글자들을 문자열(String)로 받습니다.
    3. 만약 읽는 과정에서 에러가 나면, 프로그램이 멈추지 않도록 빈 내용을 반환합니다.

    Args:
        img (Image.Image): PIL 라이브러리로 로드된 이미지 객체 (표가 포함된 영역 등)
        lang (str, optional): 인식할 언어 설정. (예: 'eng+kor'는 영어와 한글을 동시에 인식)
                              None일 경우 기본 설정을 따릅니다.

    Returns:
        str: 이미지에서 추출된 텍스트. (실패 시 빈 문자열 "")
    """
    try:
        # 언어 설정이 있는 경우 해당 언어로 인식을 시도합니다.
        if lang:
            return pytesseract.image_to_string(img, lang=lang)

        # 언어 설정이 없으면 기본 설정으로 인식을 시도합니다.
        return pytesseract.image_to_string(img)

    except Exception:
        # [예외 처리]
        # OCR 엔진이 설치되어 있지 않거나, 이미지 파일이 손상된 경우 등
        # 에러가 발생하더라도 프로그램 전체가 멈추지(Crash) 않도록
        # "읽지 못함(빈 문자열)"으로 처리하고 넘어갑니다.
        # 상위 로직(extractor)에서 결과가 비어있음을 확인하고 대응하게 됩니다.
        return ""