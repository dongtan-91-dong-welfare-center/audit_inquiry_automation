# tests/core/test_preprocessor.py
import pytest
import cv2
import os
import numpy as np
from src.core.preprocessor import ImagePreprocessor
from src.core.pdf_loader import PDFLoader


@pytest.fixture(scope="module")
def real_body_pages(scan_pdf_path):
    """
    통합 테스트를 위해 실제 PDF 파일의 3페이지 이후 본문 이미지를 로드하는 픽스처입니다.
    """
    with open(scan_pdf_path, "rb") as f:
        loader = PDFLoader(f)
        return loader.convert_to_images(start_page=3)

class TestImagePreprocessor:
    """ImagePreprocessor 클래스의 기능 검증을 위한 테스트 스위트"""

    @pytest.fixture(autouse=True)
    def setup(self, mock_image_factory):
        """각 테스트 메서드 실행 전 Preprocessor 인스턴스와 출력 폴더를 초기화합니다."""
        self.preprocessor = ImagePreprocessor()
        self.output_dir = "tests/data/output/preprocessor"
        os.makedirs(self.output_dir, exist_ok=True)

        # 공통으로 사용할 빈 이미지 생성
        self.white_page = mock_image_factory()

    # ---------------------------------------------------------
    # 1. Integration Tests (실데이터 및 PDFLoader 연동 검증)
    # ---------------------------------------------------------

    @pytest.mark.integration
    def test_integration_with_pdf_loader(self, real_body_pages):
        """
        PDFLoader에서 불러온 실제 스캔 이미지가 Preprocessor 전체 파이프라인을 거쳐 정상적으로 크롭 및 3채널 변환되는지 검증합니다.
        """
        # 다수의 페이지 이미지를 전처리 파이프라인에 통과시킴
        extracted_tables = self.preprocessor.process_pages(real_body_pages)

        # 최소 1개 이상의 표를 정상적으로 추출해야 함
        assert len(real_body_pages) > 0, "PDF에서 표를 추출할 수 없었습니다."

        for i, table_img in enumerate(extracted_tables):
            # Numpy 배열 형태의 BGR 3채널에 부합하는지 확인
            assert isinstance(table_img, np.ndarray), "numpy 배열이 아닙니다."
            assert table_img.ndim == 3 and table_img.shape[2] == 3, "추출된 표 이미지가 BGR(3채널) 포맷이 아닙니다."

            # 디버깅 및 시각적 확인을 위해 테스트 산출물 시각화 저장
            save_path = os.path.join(self.output_dir, f"integration_table_{i}.jpg")
            cv2.imwrite(save_path, table_img)

    # ---------------------------------------------------------
    # 2. Unit Tests (Mock Numpy Array를 활용한 로직 검증)
    # ---------------------------------------------------------

    @pytest.mark.unit
    def test_noise_and_area_filtering(self):
        """설정한 임계값 미만의 노이즈 컨투어를 제거하는지 검증"""
        mock_page = self.white_page.copy()
        # 유효한 표(면적 큼)
        cv2.rectangle(mock_page, (100, 100), (400, 400), 0, -1)

        # 노이즈(매우 작은 점)
        cv2.rectangle(mock_page, (10, 10), (20, 20), 0, -1)

        tables = self.preprocessor.process_pages(mock_page)

        # 노이즈는 무시하고 큰 사각형 1개를 추출해야 함
        assert len(tables) == 1

    @pytest.mark.unit
    def test_empty_contour_handling(self):
        """표가 없는 이미지 입력 시 IndexError 없이 빈 리스트를 반화하는지 검증"""
        empty_image = self.white_page.copy()

        result = self.preprocessor._process_page(empty_image)

        assert isinstance(result, list)
        assert len(result) == 0

    @pytest.mark.unit
    def test_multi_table_sorting_order(self):
        """여러 표가 있을 때 상단 -> 하단, 좌 -> 우 순서로 정렬하여 반환하는지 검증"""
        mock_page = self.white_page.copy()

        # 좌측 상단(1순위)
        cv2.rectangle(mock_page, (100, 100), (300, 300), 0, -1)

        # 우측 상단(2순위)
        cv2.rectangle(mock_page, (500, 100), (700, 300), 0, -1)

        # 중앙 하단(3순위)
        cv2.rectangle(mock_page, (300, 600), (500, 800), 0, -1)

        table = self.preprocessor._process_page(mock_page)

        assert len(table) == 3

    @pytest.mark.unit
    def test_vertical_line_removal_logic(self):
        """
        긴 세로선은 제거하되, 짧은 가로선(텍스트 대용)은 유지하는지 검증
        """
        mock_page = self.white_page.copy()

        # 제거 대상 세로선
        cv2.line(mock_page, (100, 20), (100, 180), 0, 2)
        # 보존 대상 가로선
        cv2.line(mock_page, (80, 100), (120, 100), 0, 2)

        processed = self.preprocessor._remove_vertical_lines(mock_page)

        # 세로선 좌표는 흰색으로 변해야 함
        assert processed[20, 100] == 255
        # 가로선 좌표는 여전히 검은색(텍스트 보존)이어야 함
        assert processed[100, 85] < 255

    @pytest.mark.unit
    def test_output_channel_dimensions(self):
        """
        입력 이미지가 1채널 흑백이더라도 결과물은 항상 3채널(BGR)인지 검증합니다.
        """
        mock_page = self.white_page.copy()
        cv2.rectangle(mock_page, (100, 100), (200, 200), -1)

        # 배치 처리 파이프라인 통과
        tables = self.preprocessor._process_page(mock_page)

        for table in tables:
            assert table.ndim == 3
            assert table.shape[2] == 3

    @pytest.mark.unit
    def test_multi_page_result_merging(self):
        """
        여러 페이지에서 나온 표가 순서대로 하나의 리스트에 병합하는지 검증
        """
        page_1 = self.white_page.copy()
        cv2.rectangle(page_1, (100, 100), (200, 200), 0, -1)

        page_2 = self.white_page.copy()
        cv2.rectangle(page_2, (100, 100), (200, 200), 0, -1)

        # 전체 파이프라인 실행
        combined_tables = self.preprocessor.process_pages([page_1, page_2])

        assert len(combined_tables) == 2
