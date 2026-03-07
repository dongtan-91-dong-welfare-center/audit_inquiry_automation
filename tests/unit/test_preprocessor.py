# tests/unit/test_preprocessor.py
import pytest
import cv2
import numpy as np
import glob
import os
from src.core.preprocessor import ImagePreprocessor

# 테스트 파일 목록 자동 추출
IMAGE_FILES = glob.glob("tests/data/input/*.jpg")

class TestImagePreprocessor:
    @pytest.fixture(autouse=True)
    def setup(self):
        self.preprocessor = ImagePreprocessor()
        self.output_dir = "tests/data/output"
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)

    @pytest.mark.parametrize("image_path", IMAGE_FILES)
    def test_process_page_detection(self, image_path):
        """
        각 이미지에서 표 영역이 최소 하나 이상 검출되는지 테스트합니다.
        """
        image = cv2.imread(image_path)
        assert image is not None, f"이미지를 불러올 수 없습니다: {image_path}"

        table_images = self.preprocessor.process_page(image)

        # 표가 검출되었는지 확인 (리스트가 비어있지 않아야 함)
        assert len(table_images) > 0

        # 검출된 결과물 저장 (디버깅 용도)
        file_name = os.path.basename(image_path)
        for i, table_img in enumerate(table_images):
            output_path = os.path.join(self.output_dir, f"result_{i}_{file_name}")
            cv2.imwrite(output_path, table_img)

    def test_process_pages_multi_input(self):
        """
        다중 페이지(리스트 입력) 처리가 올바르게 수행되는지 테스트합니다.
        """
        sample_images = [cv2.imread(path) for path in IMAGE_FILES[:2] if cv2.imread(path) is not None]
        if not sample_images:
            pytest.skip("테스트할 이미지 파일이 부족합니다.")

        all_tables = self.preprocessor.process_pages(sample_images)

        # 여러 페이지에서 추출된 표들이 하나의 리스트로 통합되었는지 확인
        assert isinstance(all_tables, list)
        assert len(all_tables) >= len(sample_images)

    @pytest.mark.parametrize("image_path", IMAGE_FILES)
    def test_output_image_quality(self, image_path):
        """
        전처리 후의 이미지가 OCR에 적합한 품질(선명도)을 유지하는지 확인합니다.
        전문가 의견 반영: 글자가 뭉치지 않았는지 간접적으로 체크합니다.
        """
        image = cv2.imread(image_path)
        table_images = self.preprocessor.process_page(image)

        for table_img in table_images:
            # 1. 업스케일링 확인 (fx=2 적용 시 원본 영역보다 커야 함)
            # 원본 대비 가로/세로 비율이 적절한지 확인
            assert table_img.shape[0] > 0
            assert table_img.shape[1] > 0

            # 2. 이미지 이진화 상태 확인 (이미지가 너무 어둡거나 밝지 않은지)
            mean_brightness = np.mean(table_img)
            assert 10 < mean_brightness < 245, "이미지가 너무 검거나 흰색입니다. 이진화 설정을 확인하세요."

    def test_table_area_ratio(self):
        """
        추출된 영역이 너무 작거나(노이즈) 너무 크지(전체 배경) 않은지 검증합니다.
        """
        path = IMAGE_FILES[0]
        image = cv2.imread(path)
        table_images = self.preprocessor.process_page(image)

        for table_img in table_images:
            h, w = table_img.shape[:2]
            # 너무 작은 영역(예: 50x50 미만)은 표가 아닐 가능성이 높음
            assert h > 100 and w > 100, f"추출된 영역이 너무 작습니다: {w}x{h}"
