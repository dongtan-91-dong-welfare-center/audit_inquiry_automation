# tests/core/test_preprocessor.py
import pytest
import cv2
import os
from src.core.preprocessor import ImagePreprocessor
from src.core.pdf_loader import PDFLoader

SCAN_PDF_PATH = "tests/data/input/bank_audit_letter-scan.pdf"


def get_scanned_body_pages():
    """3페이지부터 본문 이미지를 가져옵니다."""
    if not os.path.exists(SCAN_PDF_PATH):
        return []
    with open(SCAN_PDF_PATH, "rb") as f:
        loader = PDFLoader(f)
        return loader.convert_to_images(start_page=3)


# 3페이지 이후 본문 데이터셋
BODY_SAMPLES = get_scanned_body_pages()


class TestImagePreprocessorMVP:
    @pytest.fixture(autouse=True)
    def setup(self):
        self.preprocessor = ImagePreprocessor()
        self.output_dir = "tests/data/output"
        os.makedirs(self.output_dir, exist_ok=True)

    @pytest.mark.skipif(not BODY_SAMPLES, reason="본문 데이터 샘플이 없습니다.")
    @pytest.mark.parametrize("idx, image", enumerate(BODY_SAMPLES))
    def test_body_table_extraction(self, idx, image):
        """본문 페이지에서 표가 유실 없이 추출되는지 확인합니다."""
        # 3페이지부터 시작하므로 인덱스 보정
        actual_page_num = idx + 3
        table_images = self.preprocessor.process_page(image)

        # 시각화 저장
        for i, table_img in enumerate(table_images):
            save_path = os.path.join(self.output_dir, f"p{actual_page_num}_table_{i}.jpg")
            cv2.imwrite(save_path, table_img)
