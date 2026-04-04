# tests/unit/test_ocr_engine.py

import os
import pytest
import numpy as np
from unittest.mock import patch

# conftest.py가 작동하므로, sys.path 설정 없이 바로 src 모듈 임포트 가능
from src.core.pdf_loader import PDFLoader
from src.core.preprocessor import ImagePreprocessor
from src.core.ocr_engine import OCRExtractor

# TODO: test_ocr_pipeline_integration을 tests/integration/test_pipeline_flow.py로 이관
@pytest.mark.integration
def test_ocr_pipeline_integration():
    """
    [통합 테스트 파이프라인]
    PDFLoader -> Preprocessor -> OCRExtractor가 연계되었을 때
    실제 은행 조회서 이미지가 어떤 3차원 리스트(표 단위)로 도출되는지 확인합니다.
    """

    # 1. 테스트 이미지 경로 설정 (tests/data/input/ 기준)
    current_dir = os.path.dirname(os.path.abspath(__file__))
    pdf_path = os.path.join(current_dir, "..", "data", "input", "bank_audit_letter-scan.pdf")

    print(f"\n▶ 1. PDF 파일 로딩 중: {os.path.basename(pdf_path)}")

    # PDFLoader 클래스를 불러와서 일괄적으로 돌리는 흐름 유지
    loader = PDFLoader(pdf_path)
    page_images = loader.convert_to_images()

    # pytest에서는 assert문을 활용해 에러를 검증합니다.
    assert page_images is not None and len(page_images) > 0, "❌ PDF에서 이미지를 불러오지 못했습니다. 경로를 확인해주세요."
    print(f"   - 로드 성공 (총 {len(page_images)} 페이지 변환 완료)")

    # 2. 전처리 (Preprocessor) 모듈 실행
    print("\n▶ 2. 전처리 파이프라인 통과 중 (전체 페이지 배열 처리 -> 표 탐지 -> 크롭)...")
    preprocessor = ImagePreprocessor()

    # 메인 파이프라인인 process_page 호출 (결과는 표 이미지들의 리스트)
    table_images = preprocessor.process_pages(page_images)
    assert table_images, "❌ 전처리된 표 이미지가 없습니다 (표를 찾지 못함)."
    print(f"   - 전처리 완료! 총 {len(table_images)}개의 표 영역 이미지가 추출되었습니다.")

    # 3. OCR (OCRExtractor) 모듈 실행
    print("\n▶ 3. OCR 엔진 구동 및 표 데이터 일괄 추출 중...")
    extractor = OCRExtractor()

    all_tables_data = extractor.extract_table_data(table_images)

    # 4. 결과 출력
    if not all_tables_data:
         print("   ❌ 추출된 데이터가 전혀 없습니다.")
    else:
        for table_idx, table_data in enumerate(all_tables_data):
            print(f"\n================== [ 표 {table_idx + 1} 결과 ] ==================")

            if not table_data:
                print("   해당 표에서 추출된 데이터가 없습니다.")
            else:
                for i, row in enumerate(table_data):
                    print(f"Row {i:02d} | 칸 수: {len(row)} | 데이터: {row}")

    print("\n=======================================================================\n")


class TestOCRExtractorUnit:
    """OCRExtractor 내부의 데이터 정제 및 정렬 로직 검증"""

    @pytest.fixture(autouse=True)
    def setup(self):
        """
        테스트가 실행될 때마다 무거운 PaddleOCR 모델이 다운로드되거나 메모리에 올라가는 것을
        방지하기 위해 unittest.mock.patch를 사용하여 가짜 객체로 대체합니다.
        """
        with patch('src.core.ocr_engine.PaddleOCR') as MockPaddle:
            # 모델 초기화 없이 OCRExtractor 인스턴스 생성
            self.extractor = OCRExtractor()
            self.mock_ocr_instance = MockPaddle.return_value

    @pytest.mark.unit
    def test_group_into_rows_basic_sorting(self):
        """
        Y축 중심점을 기준으로 동일한 행(Row)으로 잘 묶이는지,
        같은 행 안에서 X축 기준으로 왼쪽에서 오른쪽으로 잘 정렬되는지 검증합니다.
        """
        # PaddleOCR이 반환하는 형태의 가짜(Mock) 데이터 생성
        # 형식: [  [  [x1,y1],[x2,y2],[x3,y3],[x4,y4]  ], ('텍스트', 신뢰도)  ]
        mock_ocr_data = [
            # 첫 번째 줄, 오른쪽 단어 (center_y: 15, left: 60)
            [[[60, 10], [100, 10], [100, 20], [60, 20]], ("계좌번호", 0.98)],

            # 두 번째 줄, 단독 단어 (center_y: 35, left: 10)
            [[[10, 30], [50, 30], [50, 40], [10, 40]], ("111-222-3333", 0.95)],

            # 첫 번째 줄, 왼쪽 단어 (center_y: 16 -> 1번 단어와 오차범위 내이므로 같은 줄로 판정되어야 함, left: 10)
            [[[10, 11], [50, 11], [50, 21], [10, 21]], ("예금종류", 0.99)]
        ]

        result = self.extractor._group_into_rows(mock_ocr_data)

        # 총 2개의 줄(행)으로 분리되어야 함
        assert len(result) == 2

        # 첫 번째 줄은 X축 기준 정렬이 수행되어 '예금종류'가 '계좌번호'보다 먼저 와야 함
        assert result[0] == ["예금종류", "계좌번호"]

        # 두 번째 줄은 다음 행으로 분리되어야 함
        assert result[1] == ["111-222-3333"]

    @pytest.mark.unit
    def test_group_into_rows_invalid_data_handling(self):
        """
        빈 값, 구조가 깨진 배열, 텍스트가 없는 경우 등
        예측 불가능한 OCR 결과물에 대해 방어 로직이 에러 없이 잘 작동하는지 검증합니다.
        """
        # 고의로 망가뜨린 형태의 가짜 데이터
        invalid_ocr_data = [
            [],  # 1. 완전히 빈 리스트
            [[[0, 0]], ()],  # 2. 길이가 부족하거나 튜플이 비어있는 경우
            [[[10, 10], [20, 10], [20, 20], [10, 20]], ("", 0.9)],  # 3. 좌표는 있으나 텍스트가 빈 문자열인 경우
            [[[10, 10], [20, 10], [20, 20], [10, 20]], ("정상데이터", 0.99)],  # 4. 정상 데이터
            None  # 5. None 타입
        ]

        # 헬퍼 메서드 실행
        result = self.extractor._group_into_rows(invalid_ocr_data)

        # 에러가 발생하지 않아야 하며, 4번 정상 데이터만 추출되어야 함
        assert len(result) == 1
        assert result[0] == ["정상데이터"]

    @pytest.mark.unit
    def test_extract_table_data_empty_input(self, mock_image_factory):
        """
        빈 이미지 리스트가 들어왔을 때나, OCR 엔진이 아무것도 찾지 못했을 때의 처리를 검증합니다.
        """
        # 빈 이미지 리스트 입력 테스트
        assert self.extractor.extract_table_data([]) == []

        # OCR이 결과를 찾지 못한 경우 self.ocr.ocr() 호출 시 [None]을 반환하도록 설정
        self.mock_ocr_instance.ocr.return_value = [None]

        dummy_image = mock_image_factory(height=100, width=100, channels=3)
        result = self.extractor.extract_table_data([dummy_image])

        # 빈 결과물을 반환해야 함
        assert result == []

    @pytest.mark.unit
    def test_group_into_rows_corrupted_bbox(self):
        """
        손상된 좌표(Bounding Box) 데이터 예외 처리 검증
        ocr_engine.py 내부의 try-except (IndexError, TypeError) 블록이
        정상적으로 작동하여 에러 없이 해당 단어를 스킵하는지 확인합니다.
        """
        # 고의로 손상시킨 좌표 데이터 모음
        corrupted_ocr_data = [
            # 1. IndexError 유발 케이스 (2차원 좌표값이 아닌 단일 값만 존재하는 경우)
            [[[10], [20], [20], [10]], ("에러유발_인덱스", 0.9)],

            # 2. TypeError 유발 케이스 (None 또는 정수가 아닌 잘못된 타입이 들어간 경우)
            [[None, None, None, None], ("에러유발_타입", 0.9)],

            # 3. 정상 데이터 (이 데이터만 정상적으로 추출되어야 함)
            [[[10, 10], [20, 10], [20, 20], [10, 20]], ("정상데이터", 0.99)]
        ]

        result = self.extractor._group_into_rows(corrupted_ocr_data)

        # 프로그램이 중간에 멈추지 않고(Skip 처리), 정상 데이터 1개만 추출되어야 함
        assert len(result) == 1
        assert result[0] == ["정상데이터"]

    @pytest.mark.unit
    def test_extract_table_data_multiple_tables(self, mock_image_factory):
        """
        다중 표(Multiple Tables) 3차원 리스트 반환 검증
        여러 장의 표 이미지가 주어졌을 때, 최종 아키텍처인
        List[List[List[str]]] 형태를 정확하게 구축하여 반환하는지 확인합니다.
        """
        # 2개의 가짜(Dummy) 이미지 생성
        image1 = mock_image_factory(height=100, width=100, channels=3)
        image2 = mock_image_factory(height=100, width=100, channels=3)

        # 첫 번째 표 이미지에서 인식될 가짜 OCR 결과 (행 1개, 단어 2개)
        ocr_result_table1 = [
            [
                [[[10, 10], [50, 10], [50, 20], [10, 20]], ("표1-단어1", 0.99)],
                [[[60, 10], [100, 10], [100, 20], [60, 20]], ("표1-단어2", 0.99)]
            ]
        ]

        # 두 번째 표 이미지에서 인식될 가짜 OCR 결과 (행 1개, 단어 1개)
        ocr_result_table2 = [
            [
                [[[10, 10], [50, 10], [50, 20], [10, 20]], ("표2-단어1", 0.99)]
            ]
        ]

        # extract_table_data 내부에서 for문으로 이미지를 순회할 때,
        # 순차적으로 다른 OCR 결과를 반환하도록 side_effect 설정
        self.mock_ocr_instance.ocr.side_effect = [ocr_result_table1, ocr_result_table2]

        # 2개의 표 이미지를 엔진에 입력
        result = self.extractor.extract_table_data([image1, image2])

        # 1. 3차원 리스트 형태 검증 및 최상위 요소 개수 검증 (표가 2개여야 함)
        assert isinstance(result, list)
        assert len(result) == 2

        # 2. 첫 번째 표 데이터 검증
        assert isinstance(result[0], list)  # 2차원 요소 검증
        assert isinstance(result[0][0], list)  # 3차원 요소 검증
        assert result[0] == [["표1-단어1", "표1-단어2"]]

        # 3. 두 번째 표 데이터 검증
        assert result[1] == [["표2-단어1"]]
