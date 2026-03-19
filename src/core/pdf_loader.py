# src/core/pdf_loader.py
from typing import Dict
import pdfplumber
import numpy as np
import os
import cv2

# 기본 시작 페이지를 상수로 선언합니다.
DEFAULT_START_PAGE = 3

class PDFLoader:
    """
    [파일 처리 담당자]
    Streamlit에서 업로드된 PDF를 OCR 처리가 가능한 이미지(고해상도)로 변환합니다.
    """
    def __init__(self, uploaded_file):
        """
        업로드된 스트림 기반의 PDF 파일 객체를 초기화합니다.

        Args:
            uploaded_file: Streamlit에서 전달받은 UploadedFile 객체
        """
        self.uploaded_file = uploaded_file
        self.metadata = self._parse_filename()

        # TODO: 파일명 유효성 및 확장자(.pdf) 검증 로직 추가 (validators.py 등 외부 유틸리티 연동 고려)

    def convert_to_images(self, start_page: int = DEFAULT_START_PAGE, end_page: int = None) -> list[np.ndarray]:
        """
        PDF의 각 페이지를 순회하며 OpenCV에서 처리 가능한 고해상도(300 DPI) BGR 이미지 배열로 변환합니다.

        Args:
            start_page: 금융거래조회서는 3페이지부터 본문을 시작하고 있음
            TODO: 실제 조회서는 송장을 PDF 맨 앞 페이지에 포함하므로 실제로 업무에 활용할 때는 4페이지로 변경
        Returns:
            list[numpy.ndarray]: 변환된 전체 페이지 이미지(BGR) 리스트
        """
        all_pages_bgr = []

        # 파일 포인터를 처음으로 되돌려 안전하게 다시 읽을 수 있도록 합니다.
        if hasattr(self.uploaded_file, 'seek'):
            self.uploaded_file.seek(0)

        # pdfplumber.open(self.uploaded_file)을 사용하여 PDF 스트림 열기
        with pdfplumber.open(self.uploaded_file) as pdf:
            total_pages = len(pdf.pages)
            # OCR 처리가 필요한 페이지 범위 설정 (기본적으로 3페이지부터 끝까지)
            if end_page is None:
                end_page = total_pages
            target_pages = pdf.pages[start_page - 1:end_page]

            # pdf 내의 각 페이지(pages 속성)를 순회하는 반복문 작성
            for page in target_pages:
                # page.to_image(resolution=300)을 호출하여 각 페이지를 고해상도 이미지(PIL 객체)로 렌더링
                img_pil = page.to_image(resolution=300).original    # resolution=300은 OCR 인식률 향상을 위한 고해상도 설정

                # 렌더링된 PIL 객체(기본 RGB 포맷)를 numpy.ndarray로 변환
                img_array = np.array(img_pil)

                # cv2.cvtColor를 사용하여 RGB 채널을 OpenCV 기본 포맷인 BGR 채널로 변경
                # PIL은 기본적으로 RGB 포맷이므로 OpenCV 처리를 위해 BGR로 변환이 필요
                img_bgr = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)

                # 변환이 완료된 BGR 이미지 배열을 리스트에 담아 반환
                # TODO: 대용량 파일 대비 제너레이터(yield) 패턴 사용 고려
                all_pages_bgr.append(img_bgr)

        return all_pages_bgr

    def _parse_filename(self) -> Dict[str, str]:
        """
        파일명 규칙 "감사대상회사_{숫자}_조회처"를 분석합니다.
        예: "삼성전자_1_국민은행.pdf" -> {company: "삼성전자", 조회처: "국민은행", category: "은행"}
        """
        # TODO: category에서 금융거래조회서의 종류를 조회처를 통해 추출하는 로직 추가
        # 1. 기본값 설정
        metadata = {
            "company_name": "미분류_회사",
            "bank_name": "미분류_조회처",
            "is_valid_format": True
        }

        if not self.uploaded_file:
            metadata["is_valid_format"] = False
            return metadata

        filename = getattr(self.uploaded_file, 'name', str(self.uploaded_file))
        # 확장자 제거 및 파일명 분리
        name_without_ext = os.path.splitext(os.path.basename(filename))[0]
        parts = [p.strip() for p in name_without_ext.split('_')]

        # 2. 형식 검증 (언더바가 최소 2개 이상 있어서 3개 이상의 파트가 나와야 함)
        if len(parts) < 3 or not parts[0] or not parts[2]:
            # 형식이 맞지 않는 경우
            metadata["is_valid_format"] = False
            metadata["company_name"] = parts[0] if parts[0] else "형식오류_회사"
            metadata["bank_name"] = "형식오류_조회처"
        else:
            # 정상 케이스
            metadata["company_name"] = parts[0]
            metadata["bank_name"] = parts[2]

        return metadata

    def is_native_pdf(self) -> bool:
        """
        업로드된 PDF 문서가 디지털 방식으로 생성된(Native) PDF인지,
        스캔된 이미지로 이루어진 PDF인지 판별합니다.

        본문이 시작되는 페이지(기본 3페이지)에서 인식되는 실제 텍스트 객체(chars)의 개수를 기준으로,
        일정 개수 이상이면 디지털 PDF로 간주합니다.
        """
        # 파일 포인터를 처음으로 되돌려 안전하게 다시 읽을 수 있도록 합니다.
        if hasattr(self.uploaded_file, 'seek'):
            self.uploaded_file.seek(0)

        with pdfplumber.open(self.uploaded_file) as pdf:
            # 본문이 시작되는 페이지보다 작으면 판별이 어려우므로 False를 반환 (또는 스캔본으로 처리)
            if len(pdf.pages) < DEFAULT_START_PAGE:
                return False

            # 인덱스는 0부터 시작하므로 DEFAULT_START_PAGE - 1
            test_page = pdf.pages[DEFAULT_START_PAGE - 1]

            # 실제 텍스트 객체(chars)가 존재하는지 확인하여 판별
            # 스캔본의 미세 노이즈 오인식 방지를 위해 안전하게 임계값을 20으로 설정합니다.
            return len(test_page.chars) > 20
