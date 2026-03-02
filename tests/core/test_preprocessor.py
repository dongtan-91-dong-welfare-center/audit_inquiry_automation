# tests/core/test_preprocessor.py
import pytest
import cv2
import numpy as np
import glob
import os
from src.core.preprocessor import ImagePreprocessor
from src.core.pdf_loader import PDFLoader

# 실제 스캔본 PDF 경로 설정
SCAN_PDF_PATH = "tests/data/input/bank_audit_letter-scan.pdf"


def get_scanned_images():
    """
    PDFLoader를 사용하여 테스트용 스캔본 이미지를 로드합니다.
    통합 테스트를 위해 실제 PDF에서 변환된 이미지 리스트를 반환합니다.
    """
    if not os.path.exists(SCAN_PDF_PATH):
        # 파일이 없을 경우 테스트 건너뛰기를 위한 빈 리스트 반환
        # TODO: 필요 시 Mocking
        return []

    with open(SCAN_PDF_PATH, "rb") as f:
        loader = PDFLoader(f)
        return loader.convert_to_images()

# PDF에서 추출한 이미지 배열 리스트 사용
IMAGE_SAMPLES = get_scanned_images()

class TestImagePreprocessor:
    @pytest.fixture(autouse=True)
    def setup(self):
        self.preprocessor = ImagePreprocessor()
        self.output_dir = "tests/data/output"
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)

    @pytest.mark.skipif(not IMAGE_SAMPLES, reason="스캔본 PDF 파일이 없습니다.")
    @pytest.mark.parametrize("image", IMAGE_SAMPLES)
    def test_process_page_detection(self, image):
        """
        각 이미지에서 표 영역이 최소 하나 이상 검출되는지 테스트합니다.
        """
        table_images = self.preprocessor.process_page(image)

        # 표가 검출되었는지 확인 (리스트가 비어있지 않아야 함)
        assert len(table_images) > 0, "표 영역을 검출하지 못했습니다."

        # 검출된 결과물 저장 (디버깅 용도)
        for i, table_img in enumerate(table_images):
            output_path = os.path.join(self.output_dir, f"scan_result_{i}.jpg")
            cv2.imwrite(output_path, table_img)

    def test_process_pages_multi_input(self):
        """
        PDF 전체 페이지(리스트)에 대한 일괄 처리가 올바르게 수행되는지 테스트합니다.
        """
        if not IMAGE_SAMPLES:
            pytest.skip("테스트할 스캔 이미지가 없습니다.")

        all_tables = self.preprocessor.process_pages(IMAGE_SAMPLES)

        # 여러 페이지에서 추출된 표들이 하나의 리스트로 통합되었는지 확인
        assert isinstance(all_tables, list)
        assert len(all_tables) >= len(IMAGE_SAMPLES)

    @pytest.mark.parametrize("image", IMAGE_SAMPLES)
    def test_output_image_quality(self, image):
        """
        전처리 후의 이미지가 OCR에 적합한 품질을 유지하는지 확인합니다.
        글자가 뭉치지 않았는가, 밝기 및 대비는 적절한가, 선명도는 어떠한가
        """
        table_images = self.preprocessor.process_page(image)

        for table_img in table_images:
            # 1. 이미지 이진화 상태 확인
            mean_brightness = np.mean(table_img)    # 밝기의 평균값
            assert 10 < mean_brightness < 245, f"이미지가 너무 어둡거나 밝습니다. (Mean: {mean_brightness:.2f})"

            # 2. 대비 체크
            # 표준편차가 높을수록 픽셀 값이 골고루 퍼져 있어 OCR에 유리함
            contrast = np.std(table_img)
            assert contrast > 20, f"이미지 대비가 너무 낮아 OCR 인식률이 저하될 수 있습니다. (std: {contrast:.2f})"

            # 3. 해상도 유지 확인
            # fx=2 적용을 고려한 최소 해상도 체크
            h, w = table_img.shape[:2]
            assert h > 400 and w > 400, f"추출된 표 영역의 해상도가 너무 낮습니다: {w}x{h}"

    def test_table_area_ratio(self):
        """
        추출된 영역이 노이즈가 아닌 유의미한 표인지 크기 및 비율로 검증합니다.
        """
        if not IMAGE_SAMPLES:
            pytest.skip("이미지가 없습니다.")

        image = IMAGE_SAMPLES[0]
        table_images = self.preprocessor.process_page(image)

        for table_img in table_images:
            h, w = table_img.shape[:2]
            # A4 기준 800px 이상의 너비를 가지는 확인
            assert w > 800, f"표의 너비가 너무 좁습니다: {w}px"
