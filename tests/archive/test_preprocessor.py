# tests/unit/test_preprocessor.py
import pytest
import cv2
import numpy as np
import os
import glob
from src.core.preprocessor import ImagePreprocessor

# 테스트 파일 목록 자동 추출
IMAGE_FILES = glob.glob("tests/data/input/*.jpg")

class TestImagePreprocessor:
    # 테스트를 수행하기 위해 미리 준비해야 하는 환경을 정의하는 데코레이터
    # 함수마다 매번 ImagePreprocessor() 수행하지 않아도 되니 코드가 깔끔해지고 효율적
    @pytest.fixture
    def preprocessor(self):
        """테스트에 사용할 클래스 인스턴스를 미리 생성"""
        return ImagePreprocessor()

    def test_get_skew_angle_precision(self, preprocessor: ImagePreprocessor):
        """
        [단위 테스트] 코드로 생성한 정확한 각도를 감지하는지 검증
        _get_skew_angle이 expected_angle만큼 회전한 것을 잘 인식했는지 확인
        """
        expected_angle = 10.0
        # 200x200 흰색 배경에 검은색 긴 막대(텍스트 대용) 생성
        img = np.full((200, 200), 255, dtype=np.uint8)
        # 배열, 시작점, 끝점, 색상, 두께
        cv2.rectangle(img, (50, 90), (150, 110), 0, -1)

        # 정확히 expected_angle 만큼 회전
        center = (100, 100)
        matrix = cv2.getRotationMatrix2D(center, expected_angle, 1.0)
        # dsize: 결과 이미지의 너비와 높이
        tilted_img = cv2.warpAffine(img, matrix, (200, 200), borderValue=255)

        # 감지된 각도 확인 (오차 범위 0.5도 이내)
        detected_angle = preprocessor._get_skew_angle(tilted_img)
        assert abs(detected_angle - expected_angle) < 0.5

    def test_enhance_image_logic_branches(self, preprocessor: ImagePreprocessor):
        """
        [단위 테스트] 컬러 이미지는 흑백으로, 이미 흑백인 이미지는 그대로 처리되는지 검증
        """
        # 1. 입력 채널 처리 분기 테스트 (컬러/흑백 모두 2차원 흑백 결과물 반환 확인)
        color_img = np.zeros((10, 10, 3), dtype=np.uint8)
        gray_img = np.zeros((10, 10), dtype=np.uint8)

        # len으로 채널의 수를 확인하는 이유는 array(array(), array(), ..., array()) 형태로 되어 있기 때문
        assert len(preprocessor._enhance_image(color_img).shape) == 2
        assert len(preprocessor._enhance_image(gray_img).shape) == 2

        # 2. 이미지 개선 효과 정밀 검증 (노이즈 제거 및 선명도)
        # 100x100 크기의 연한 회색(200) 배경 이미지 생성
        test_img = np.full((100, 100), 200, dtype=np.uint8)

        # 가상의 '글자' 추가: 진한 회색(50)으로 선을 그음
        cv2.line(test_img, (20, 50), (80, 50), 50, 3)

        # 가상의 '노이즈' 추가: 배경과 대비되는 아주 검은 점(0)을 찍음
        test_img[10, 10] = 0

        # 전처리 실행
        enhanced = preprocessor._enhance_image(test_img)

        # 반드시 이진 이미지(0과 255로만 구성)여야 함
        unique_values = np.unique(enhanced)
        assert set(unique_values).issubset({0, 255}), "결과물이 이진화되지 않았습니다."

        # 노이즈 제거 확인
        # Gaussian Blur(5x5)와 Adaptive Thresholding에 의해 단일 픽셀 노이즈는 배경색(255)으로 동화되어야 함
        assert enhanced[10, 10] == 255, "단일 픽셀 노이즈가 제거되지 않았습니다."

        # 글자 보존 및 명암 개선 확인
        # 원본에서 진한 회색(50)이었던 글자 영역은 전처리 후 완전한 검은색(0)이 되어야 함
        assert enhanced[50, 50] == 0, "글자 영역이 검은색으로 선명하게 처리되지 않았습니다."

        # 배경 보존 확인
        # 글자가 없는 일반 배경 영역은 완전한 흰색(255)이 되어야 함
        assert enhanced[20, 20] == 255, "배경 영역이 흰색으로 정돈되지 않았습니다."

    def test_detect_tables_logic(self, preprocessor: ImagePreprocessor):
        """
        [단위 테스트] 코드로 생성한 가상의 표(Grid) 영역을 정확히 탐지하여 좌표를 반환하는지 검증
        """
        # 1. 테스트용 가상 표 생성 정보 정의
        expected_x, expected_y = 100, 150
        expected_w, expected_h = 600, 300  # (700-100), (450-150)

        # 800x800 흰색 배경 생성
        img = np.full((800, 800, 3), 255, dtype=np.uint8)

        # 표 외곽선 그리기 (100, 150)에서 (700, 450)까지
        cv2.rectangle(img, (expected_x, expected_y), (700, 450), (0, 0, 0), 2)

        # 내부에 세로 구분선 4개 추가 (Column 구조 생성)
        for i in range(1, 5):
            cv2.line(img, (100 + i * 120, 150), (100 + i * 120, 450), (0, 0, 0), 1)

        # 2. 표 탐지 실행
        bounding_boxes = preprocessor._detect_tables(img)

        # 3. 정밀 검증 로직
        # 탐지된 박스가 최소 1개 이상이어야 함
        assert len(bounding_boxes) >= 1

        # 첫 번째로 탐지된 박스(상단 정렬 기준)의 좌표 추출
        detected_x, detected_y, detected_w, detected_h = bounding_boxes[0]

        # 허용 오차 범위 설정 (픽셀 단위)
        # 이진화 및 팽창(Dilation) 과정에서 외곽선이 1~3픽셀 정도 확장될 수 있음을 고려
        tolerance = 5

        assert abs(detected_x - expected_x) <= tolerance, f"X좌표 오차 초과: 예상 {expected_x}, 실제 {detected_x}"
        assert abs(detected_y - expected_y) <= tolerance, f"Y좌표 오차 초과: 예상 {expected_y}, 실제 {detected_y}"
        assert abs(detected_w - expected_w) <= tolerance, f"너비 오차 초과: 예상 {expected_w}, 실제 {detected_w}"
        assert abs(detected_h - expected_h) <= tolerance, f"높이 오차 초과: 예상 {expected_h}, 실제 {detected_h}"

    def test_exclude_instruction_notes(self, preprocessor: ImagePreprocessor):
        """[단위 테스트] 빽빽한 작성요령 영역이 배제되는지 확인"""
        # 1000x1000 배경
        img = np.full((1000, 1000), 255, dtype=np.uint8)

        # 실제 작성요령처럼 줄 간격이 좁은 텍스트 덩어리 모사
        for i in range(800, 950, 10):  # 10픽셀 간격으로 빽빽하게 선 생성
            cv2.line(img, (100, i), (900, i), 0, 5)

        # 상단에는 여백이 충분한 표 생성
        cv2.rectangle(img, (100, 100), (900, 400), 0, 2)
        cv2.line(img, (100, 250), (900, 250), 0, 2)  # 여백이 큼

        boxes = preprocessor._detect_tables(img)

        # 하단 덩어리는 whitespace_ratio 필터에 의해 제거되어야 함
        assert len(boxes) == 1
        assert boxes[0][1] < 500

    def test_empty_image_returns_empty_list(self, preprocessor: ImagePreprocessor):
        """
        [엣지 케이스] 글자나 표가 전혀 없는 빈 이미지가 들어왔을 때 빈 리스트를 반환하는지 검증
        """
        # 500x500 크기의 순백색(255) 이미지 생성
        img = np.full((500, 500, 3), 255, dtype=np.uint8)

        # 처리 수행
        tables = preprocessor.process_page(img)

        # 검증: 에러 없이 빈 리스트를 반환해야 함
        assert isinstance(tables, list)
        assert len(tables) == 0

    def test_very_small_image_handling(self, preprocessor: ImagePreprocessor):
        """
        [엣지 케이스] 처리할 수 없을 정도로 작은 이미지(예: 10x10)가 들어왔을 때
        에러 없이 동작하며 빈 리스트를 반환하는지 검증
        """
        # 10x10 크기의 아주 작은 이미지 생성
        # (이진화 알고리즘의 blockSize인 21보다 작은 경우를 가정)
        img = np.full((10, 10, 3), 255, dtype=np.uint8)

        try:
            # 처리 수행
            tables = preprocessor.process_page(img)

            # 검증: 에러 발생 없이 리스트 형태를 반환해야 함
            assert isinstance(tables, list)
            assert len(tables) == 0
        except Exception as e:
            # 에러가 발생하면 테스트 실패로 간주
            pytest.fail(f"매우 작은 이미지를 처리하는 도중 예외가 발생했습니다: {e}")

    # 이미지 파일이 없는 경우 스킵하여 테스트 결과를 깔끔하게 확인
    @pytest.mark.skipif(not IMAGE_FILES, reason="테스트용 실제 이미지 파일이 없습니다.")
    # 동일한 테스트 로직을 여러 개의 서로 다른 데이터로 반복해서 실행하는 데코레이터
    @pytest.mark.parametrize("image_path", IMAGE_FILES)
    def test_real_document_processing(self, preprocessor: ImagePreprocessor, image_path: str):
        """
        [통합 테스트] 금융조회서 이미지를 처리했을 때 표가 정상 분할/전처리되는지 검증
        """
        img = cv2.imread(image_path)
        # 개별 파일에 문제 발생 시 실패 로그 확인
        if img is None:
            pytest.fail(f"이미지 로드 실패: {image_path}")

        # 처리 수행
        tables = preprocessor.process_page(img)

        # 결과 검증
        # 리스트 형태로 반환되어야 함
        assert isinstance(tables, list)

        # 문서 내에 표가 최소 1개 이상 탐지되었다고 가정 (문서 특성에 따라 다를 수 있음)
        if len(tables) > 0:
            for table in tables:
                assert table is not None
                assert table.dtype == np.uint8
                assert len(table.shape) == 2  # 전처리가 끝난 표는 흑백(2차원 배열)이어야 함

                mean_val = np.mean(table)
                assert 0 < mean_val < 255, f"{image_path}의 표 결과가 너무 어둡거나 밝습니다."

    def test_save_processed_samples(self, preprocessor: ImagePreprocessor):
        """
        [통합 테스트] 직접 눈으로 확인할 수 있도록 표 크롭 및 전처리 결과를 tests/output에 저장
        """
        if not IMAGE_FILES:
            pytest.skip("샘플 파일 없음")

        output_dir = "tests/data/output"
        os.makedirs(output_dir, exist_ok=True)

        for path in IMAGE_FILES[:2]:  # 상위 2개만 샘플링
            img = cv2.imread(path)

            # 전체 페이지 파이프라인 실행
            tables = preprocessor.process_page(img)

            base_name = os.path.basename(path)

            # 분할된 표 배열들을 순회하며 개별 파일로 저장
            for idx, table_img in enumerate(tables):
                # 예: result_0_bank_audit_letter-0001.jpg
                file_name = f"result_{idx}_{base_name}"
                cv2.imwrite(os.path.join(output_dir, file_name), table_img)

        print(f"\n[알림] 분할/전처리된 표 이미지 들이 {output_dir}에 저장되었습니다. 직접 확인해 보세요!")
