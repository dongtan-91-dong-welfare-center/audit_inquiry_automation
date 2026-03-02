# tests/core/test_pdf_loader.py
import pytest
import numpy as np
import os
import cv2
import pdfplumber
from src.core.pdf_loader import PDFLoader


class TestPDFLoader:
    @pytest.fixture(autouse=True)
    def setup(self):
        """
        테스트 결과물을 저장할 디렉토리를 준비합니다.
        """
        self.output_dir = "tests/data/output"
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)

    @pytest.fixture
    def scan_pdf_path(self):
        """
        실제 스캔본 PDF 파일 경로를 반환합니다.
        """
        path = "tests/data/input/bank_audit_letter-scan.pdf"
        if not os.path.exists(path):
            pytest.skip(f"테스트용 스캔본 파일이 없습니다: {path}")
        return path

    def test_convert_to_images_and_visualize(self, scan_pdf_path):
        """
        PDF를 이미지로 변환하고 결과물을 저장합니다.
        """
        with open(scan_pdf_path, "rb") as f:
            loader = PDFLoader(f)
            images = loader.convert_to_images()

        assert len(images) > 0, "변환된 이미지가 없습니다."

        # PDF 파일명 추출 (확장자 제외)
        pdf_name = os.path.splitext(os.path.basename(scan_pdf_path))[0]

        for i, img in enumerate(images):
            # 저장 경로 설정: tests/data/output/debug_loader_page_0.jpg
            output_path = os.path.join(self.output_dir, f"debug_loader_{pdf_name}_p{i}.jpg")

            # OpenCV를 사용하여 BGR 이미지 저장
            success = cv2.imwrite(output_path, img)

            assert success, f"이미지 저장에 실패했습니다: {output_path}"
            print(f"이미지 저장 완료: {output_path}")

    def test_convert_to_images_page_count(self, scan_pdf_path):
        """
        반환된 이미지 리스트의 개수가 PDF 실제 페이지 수와 일치하는지 확인합니다.
        """
        # 1. 실제 PDF의 페이지 수 확인
        with pdfplumber.open(scan_pdf_path) as pdf:
            expected_page_count = len(pdf.pages)

        # 2. PDFLoader 실행 (Streamlit UploadedFile 모사를 위해 binary mode로 오픈)
        with open(scan_pdf_path, "rb") as f:
            loader = PDFLoader(f)
            images = loader.convert_to_images()

        # 3. 검증
        assert len(images) == expected_page_count, f"페이지 수가 일치하지 않습니다. 기대값: {expected_page_count}, 실제값: {len(images)}"

    def test_convert_to_images_type_and_resolution(self, scan_pdf_path):
        """
        반환된 객체가 np.ndarray 타입인지, OCR에 적합한 고해상도인지 검증합니다.
        """
        with open(scan_pdf_path, "rb") as f:
            loader = PDFLoader(f)
            images = loader.convert_to_images()

        for i, img in enumerate(images):
            # 1. 타입 검증
            assert isinstance(img, np.ndarray), f"{i}번째 페이지가 numpy.ndarray 타입이 아닙니다."

            # 2. 채널 확인 (BGR 포맷이므로 3채널이어야 함)
            assert len(img.shape) == 3 and img.shape[2] == 3, f"{i}번째 이미지의 채널 구성이 올바르지 않습니다."

            # 3. 해상도 검증 (300 DPI 기준, 일반적인 A4 사이즈는 약 2480x3508 픽셀 내외)
            # OCR 인식률을 위해 최소 가로 또는 세로가 2000 픽셀 이상인지 확인
            height, width = img.shape[:2]
            assert height > 2000 or width > 2000, f"{i}번째 이미지 해상도가 OCR에 부적합합니다: {width}x{height}"

    def test_image_data_validity(self, scan_pdf_path):
        """
        이미지 데이터가 비어있지 않고 유효한지 확인합니다.
        """
        with open(scan_pdf_path, "rb") as f:
            loader = PDFLoader(f)
            images = loader.convert_to_images()

        for img in images:
            # 픽셀 값이 모두 0(검은색)이거나 모두 255(흰색)가 아닌지 확인
            assert np.std(img) > 0, "이미지가 단일 색상으로 구성되어 데이터가 유효하지 않습니다."
