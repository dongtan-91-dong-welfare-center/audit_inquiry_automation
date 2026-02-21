# tests/core/test_preprocessor.py
import pytest
import cv2
import numpy as np
import os
import glob
from src.core.preprocessor import ImagePreprocessor

# 테스트 파일 목록 자동 추출
IMAGE_FILES = glob.glob("tests/input/*.jpg")

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
        color_img = np.zeros((10, 10, 3), dtype=np.uint8)
        gray_img = np.zeros((10, 10), dtype=np.uint8)

        # len으로 채널의 수를 확인하는 이유는 array(array(), array(), ..., array()) 형태로 되어 있기 때문
        assert len(preprocessor.enhance_image(color_img).shape) == 2
        assert len(preprocessor.enhance_image(gray_img).shape) == 2

    # 이미지 파일이 없는 경우 스킵하여 테스트 결과를 깔끔하게 확인
    @pytest.mark.skipif(not IMAGE_FILES, reason="테스트용 실제 이미지 파일이 없습니다.")
    # 동일한 테스트 로직을 여러 개의 서로 다른 데이터로 반복해서 실행하는 데코레이터
    @pytest.mark.parametrize("image_path", IMAGE_FILES)
    def test_real_document_processing(self, preprocessor: ImagePreprocessor, image_path: str):
        """
        [통합 테스트] 금융조회서 이미지를 처리했을 때 에러가 없는지 검증
        """
        img = cv2.imread(image_path)
        # 개별 파일에 문제 발생 시 실패 로그 확인
        if img is None:
            pytest.fail(f"이미지 로드 실패: {image_path}")

        # 처리 수행
        result = preprocessor.enhance_image(img)

        # 결과 검증
        assert result is not None
        assert result.dtype == np.uint8
        # 이진화 결과물은 픽셀 값이 0과 255 위주여야 함
        mean_val = np.mean(result)
        assert 0 < mean_val < 255, f"{image_path}의 결과가 너무 어둡거나 밝습니다."

    def test_save_processed_samples(self, preprocessor: ImagePreprocessor):
        """
        [통합 테스트] 직접 눈으로 확인할 수 있도록 처리 결과를 tests/output에 저장
        """
        if not IMAGE_FILES:
            pytest.skip("샘플 파일 없음")

        output_dir = "tests/output"
        os.makedirs(output_dir, exist_ok=True)

        for path in IMAGE_FILES[:2]:  # 상위 2개만 샘플링
            img = cv2.imread(path)
            result = preprocessor.enhance_image(img)

            file_name = f"result_{os.path.basename(path)}"
            cv2.imwrite(os.path.join(output_dir, file_name), result)

        print(f"\n[알림] 실제 이미지 전처리 결과가 {output_dir}에 저장되었습니다. 직접 확인해 보세요!")
