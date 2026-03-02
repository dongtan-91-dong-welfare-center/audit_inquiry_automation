# tests/core/test_pdf_loader.py
import pytest
import numpy as np
import os
import pdfplumber
from src.core.pdf_loader import PDFLoader


class TestPDFLoaderMVP:
    @pytest.fixture
    def scan_pdf_path(self):
        """실제 스캔본 PDF 파일 경로를 확인합니다."""
        path = "tests/data/input/bank_audit_letter-scan.pdf"
        if not os.path.exists(path):
            pytest.skip(f"테스트용 스캔본 파일이 없습니다: {path}")
        return path

    def test_convert_to_images_page_slicing(self, scan_pdf_path):
        """3페이지부터 로드하는 슬라이싱 로직이 정확한지 검증합니다."""
        start_page = 3

        # 1. 원본 PDF의 전체 페이지 수 확인
        with pdfplumber.open(scan_pdf_path) as pdf:
            total_pages = len(pdf.pages)
            expected_count = total_pages - (start_page - 1)

        # 2. 3페이지부터 로드 수행
        with open(scan_pdf_path, "rb") as f:
            loader = PDFLoader(f)
            images = loader.convert_to_images(start_page=start_page)

        # 3. 검증: 페이지 수가 정확히 슬라이싱 되었는가
        assert len(images) == expected_count, f"슬라이싱 오류. 기대값: {expected_count}, 실제값: {len(images)}"

    def test_image_format_and_quality(self, scan_pdf_path):
        """반환된 이미지의 타입, 채널, 해상도가 OCR에 적합한지 검증합니다."""
        with open(scan_pdf_path, "rb") as f:
            loader = PDFLoader(f)
            # 최소한의 데이터로 확인하기 위해 3페이지부터 로드
            images = loader.convert_to_images(start_page=3)

        for i, img in enumerate(images):
            # 타입 검증 (numpy ndarray)
            assert isinstance(img, np.ndarray), f"{i}번째 결과가 numpy 배열이 아닙니다."

            # 채널 검증 (OpenCV BGR: 3채널)
            assert img.ndim == 3 and img.shape[2] == 3, f"{i}번째 이미지 채널이 BGR(3)이 아닙니다."

            # 해상도 검증 (300 DPI 기준, 최소 2000px 이상)
            height, width = img.shape[:2]
            assert height > 2000 or width > 2000, f"{i}번째 이미지 해상도가 OCR 기준에 미달합니다: {width}x{height}"

            # 데이터 유효성 검증 (빈 이미지가 아닌지 표준편차로 확인)
            assert np.std(img) > 0, f"{i}번째 이미지 데이터가 유효하지 않습니다."

    def test_default_page_loading(self, scan_pdf_path):
        """인자 없이 호출했을 때 기본값(3페이지)이 적용되는지 확인합니다."""
        with open(scan_pdf_path, "rb") as f:
            loader = PDFLoader(f)
            images_default = loader.convert_to_images()  # 기본값 사용

        with pdfplumber.open(scan_pdf_path) as pdf:
            expected_count = len(pdf.pages) - 2

        assert len(images_default) == expected_count, "기본 시작 페이지(3) 로직이 올바르지 않습니다."
