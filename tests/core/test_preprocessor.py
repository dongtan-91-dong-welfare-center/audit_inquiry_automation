# tests/core/test_preprocessor.py
import pytest
import cv2
import numpy as np
import os
from src.core.preprocessor import ImagePreprocessor
from src.core.pdf_loader import PDFLoader

# 실제 스캔본 PDF 경로
SCAN_PDF_PATH = "tests/data/input/bank_audit_letter-scan.pdf"


def get_scanned_images():
    """PDFLoader를 사용하여 실제 스캔본에서 이미지 리스트를 추출합니다."""
    if not os.path.exists(SCAN_PDF_PATH):
        return []
    with open(SCAN_PDF_PATH, "rb") as f:
        loader = PDFLoader(f)
        return loader.convert_to_images()


IMAGE_SAMPLES = get_scanned_images()


class TestImagePreprocessor:
    @pytest.fixture(autouse=True)
    def setup(self):
        self.preprocessor = ImagePreprocessor()
        self.output_dir = "tests/data/output"
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)

    @pytest.mark.skipif(not IMAGE_SAMPLES, reason="테스트용 PDF 파일이 없습니다.")
    @pytest.mark.parametrize("idx, image", enumerate(IMAGE_SAMPLES))
    def test_process_and_visualize_pages(self, idx, image):
        """
        각 페이지별 표 검출 결과를 시각화하고 저장합니다.
        """
        table_images = self.preprocessor.process_page(image)

        # 검출된 각 표를 페이지별/순서별로 저장 (예: p0_table_0.jpg)
        for i, table_img in enumerate(table_images):
            save_path = os.path.join(self.output_dir, f"p{idx}_table_{i}.jpg")
            cv2.imwrite(save_path, table_img)

        print(f"\n[Page {idx}] {len(table_images)} tables extracted and saved.")
        assert len(table_images) > 0

    def test_process_pages_integration(self):
        """전체 페이지 통합 처리 및 리스트 반환을 검증합니다."""
        if not IMAGE_SAMPLES:
            pytest.skip("이미지가 없습니다.")

        all_tables = self.preprocessor.process_pages(IMAGE_SAMPLES)
        assert isinstance(all_tables, list)
        assert len(all_tables) >= len(IMAGE_SAMPLES)

    @pytest.mark.parametrize("idx, image", enumerate(IMAGE_SAMPLES))
    def test_output_quality_and_metrics(self, idx, image):
        """추출된 표 이미지의 OCR 적합성(밝기, 대비)을 검증합니다."""
        table_images = self.preprocessor.process_page(image)

        for i, table_img in enumerate(table_images):
            # 1. 밝기 검증
            mean_val = np.mean(table_img)
            assert 10 < mean_val < 245, f"P{idx}_T{i}: 밝기 이상 ({mean_val:.2f})"

            # 2. 대비(표준편차) 검증
            contrast = np.std(table_img)
            assert contrast > 20, f"P{idx}_T{i}: 대비 부족 ({contrast:.2f})"

            # 3. 크기 검증 (A4 업스케일 기준)
            h, w = table_img.shape[:2]
            assert h > 100 and w > 100, f"P{idx}_T{i}: 영역 너무 작음 ({w}x{h})"

    def test_specific_page_table_count(self):
        """요구사항에 명시된 특정 페이지의 표 개수가 일치하는지 확인합니다."""
        if len(IMAGE_SAMPLES) < 10:
            pytest.skip("페이지 수가 부족하여 검증 불가")

        # 6페이지(인덱스 5)는 표 2개 예상
        page_6_tables = self.preprocessor.process_page(IMAGE_SAMPLES[5])
        assert len(page_6_tables) >= 2, f"6페이지 표 검출 부족: {len(page_6_tables)}"

        # 9페이지(인덱스 8)는 표 2개 예상
        page_9_tables = self.preprocessor.process_page(IMAGE_SAMPLES[8])
        assert len(page_9_tables) >= 2, f"9페이지 표 검출 부족: {len(page_9_tables)}"
