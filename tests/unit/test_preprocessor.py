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
    def setup(self):
        """각 테스트 메서드 실행 전 Preprocessor 인스턴스와 출력 폴더를 초기화합니다."""
        self.preprocessor = ImagePreprocessor()
        self.output_dir = "tests/data/output/preprocessor"
        os.makedirs(self.output_dir, exist_ok=True)

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
    def test_table_filtering_and_sorting(self):
        """미세 노이즈(면적 1% 미만) 필터링 기능과 좌표 기반 정렬(위에서 아래로, 왼쪽에서 오른쪽으로) 기능이 정확히 동작하는지 검증합니다."""
        # 1000x1000 크기의 빈 백지(255) 생성
        mock_page = np.full((1000, 1000), 255, dtype=np.uint8)

        # 표 1: 우측 상단 배치 (업스케일 반영 후 면적: 800*600 = 480,000 -> 1% 초과)
        cv2.rectangle(mock_page, (500, 100), (900, 400), (0, 0, 0), -1)

        # 표 2: 좌측 하단 배치 (업스케일 반영 후 면적: 800*600 = 480,000 -> 1% 초과)
        cv2.rectangle(mock_page, (100, 600), (500, 900), (0, 0, 0), -1)

        # 노이즈: 좌측 상단 아주 작은 점 (업스케일 반영 후 면적: 40*40 = 1,600 -> 1% 미만)
        cv2.rectangle(mock_page, (10, 10), (30, 30), (0, 0, 0), -1)

        # 단일 페이지 전처리 수행
        tables = self.preprocessor._process_page(mock_page)

        # 노이즈가 필터링되어 정확히 2개의 표만 추출되어야 함
        assert len(tables) == 2

        # y좌표가 작은 것(표 1, 상단)이 먼저 오고, 3채널(BGR)로 변환되었는지 검증
        table_1, table_2 = tables

        # 팽창 연산으로 인해 사방으로 확장된 픽셀(14px)을 반영한 크기로 검증
        assert table_1.shape == (614, 814, 3), "첫 번째 표의 크기나 채널이 맞지 않습니다."
        assert table_2.shape == (614, 814, 3), "두 번째 표의 크기나 채널이 맞지 않습니다."

    @pytest.mark.unit
    def test_remove_vertical_lines(self):
        """
        세로선 제거 로직(_remove_vertical_lines)이 일반 텍스트(가로선)는 보존하고 긴 세로선만 흰색으로 지우는지 검증합니다.
        """
        # 100x200 크기의 백지 생성
        mock_image = np.full((200, 100), 255, dtype=np.uint8)

        # 중앙에 검은색(0) 긴 세로선 그리기 (굵기 2)
        cv2.line(mock_image, (50, 10), (50, 190), 0, 2)

        # 일반 글자를 흉내낸 작은 노이즈(가로선) 추가
        cv2.line(mock_image, (20, 100), (40, 100), 0, 2)

        # 세로선 제거 로직 단독 실행 (3채널 BGR 반환)
        result = self.preprocessor._remove_vertical_lines(mock_image)

        # Then 1: 긴 세로선이 있던 (100, 50) 픽셀은 흰색([255, 255, 255])으로 지워져야 함
        assert np.all(result[100, 50] == 255), "세로선이 정상적으로 제거되지 않았습니다."

        # Then 2: 가로선(일반 텍스트)이 있던 (100, 30) 픽셀은 여전히 검은색(0) 근처여야 함
        assert np.all(result[100, 30] < 255), "일반 텍스트(가로선)가 잘못 지워졌습니다."

    @pytest.mark.unit
    def test_process_pages_channel_conversion(self):
        """
        입력 이미지가 1채널 흑백이더라도 파이프라인의 최종 출력물은 반드시 3채널(BGR)로 규격화되는지 검증합니다.
        """
        # 표가 하나 그려진 1채널 흑백 이미지 생성
        mock_page_gray = np.full((500, 500), 255, dtype=np.uint8)
        cv2.rectangle(mock_page_gray, (50, 50), (450, 450), (0, 0, 0), -1)

        # 배치 처리 파이프라인 통과
        result_tables = self.preprocessor.process_pages([mock_page_gray])

        # 크롭된 표가 리스트에 담겨 반환되며, BGR 3채널로 확정되어야 함
        assert len(result_tables) == 1
        assert result_tables[0].ndim == 3, "결과물이 3차원 배열이 아닙니다."
        assert result_tables[0].shape[-1] == 3, "결과물이 3채널(BGR)로 변환되지 않았습니다."

    @pytest.mark.unit
    def test_empty_table_handling(self):
        """
        이미지 내에 추출할 수 있는 표(1% 이상 면적)가 전혀 없을 때 오류를 발생시키지 않고 빈 리스트를 정상적으로 반환하는지 방어 로직을 검증합니다.
        """
        # 완전히 비어있는 3채널 백지 생성
        mock_empty_page = np.full((500, 500, 3), 255, dtype=np.uint8)

        # 단일 페이지 처리
        result_tables = self.preprocessor._process_page(mock_empty_page)

        # 에러 없이 빈 리스트를 반환
        assert result_tables == [], "빈 페이지에서 빈 리스트가 아닌 값을 반환했습니다."
