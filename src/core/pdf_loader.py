# src/core/pdf_loader.py
from typing import Dict
import pdfplumber
import numpy as np
import os
import cv2

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

    def convert_to_images(self, start_page: int = 3) -> list[np.ndarray]:
        """
        PDF의 각 페이지를 순회하며 OpenCV에서 처리 가능한 고해상도(300 DPI) BGR 이미지 배열로 변환합니다.

        Args:
            start_page: 금융거래조회서는 3페이지부터 본문을 시작하고 있음
        Returns:
            list[numpy.ndarray]: 변환된 전체 페이지 이미지(BGR) 리스트
        """
        all_pages_bgr = []

        # pdfplumber.open(self.uploaded_file)을 사용하여 PDF 스트림 열기
        with pdfplumber.open(self.uploaded_file) as pdf:
            target_pages = pdf.pages[start_page - 1:]   # 인덱스는 0부터 시작

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
        예: "삼성전자_1_국민은행.pdf" -> {company: "삼성전자", bank: "국민은행", category: "은행"}
        """
        # TODO: category에서 금융거래조회서의 종류를 bank를 통해 추출하는 로직 추가
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
            # 파일명 전체를 회사명이나 조회처명에 임시로 할당하여 에러 방지
            metadata["company_name"] = parts[0] if parts[0] else "형식오류_회사"
            metadata["bank_name"] = "형식오류_조회처"

            print(f"⚠️ 파일명 형식이 규칙에 맞지 않습니다: {filename}")
        else:
            # 정상 케이스
            metadata["company_name"] = parts[0]
            metadata["bank_name"] = parts[2]

        return metadata

    def _extract_native_text_or_tables(self):
        """
        [추후 고도화 과제 - Native PDF Bypass]
        스캔본이 아닌, 디지털 방식으로 텍스트와 선 데이터가 포함되어 생성된(Native) PDF의 경우,
        무거운 전처리와 OCR 과정을 거치지 않고 pdfplumber의 자체 기능인 extract_text()나
        extract_tables()를 사용하여 데이터를 즉시 추출하는 우회 경로 로직입니다.
        """
        # TODO: 현재 문서가 Native PDF인지 스캔 이미지 덩어리인지 판별하는 로직 구현
        # TODO: Native PDF일 경우 직접 텍스트/표 데이터를 파싱하여 반환하는 파이프라인 분기 처리
        pass
