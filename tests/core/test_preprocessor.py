# tests/core/test_preprocessor.py
import pytest
import cv2
import numpy as np
import glob
from src.core.preprocessor import ImagePreprocessor

# 테스트 파일 목록 자동 추출
IMAGE_FILES = glob.glob("tests/data/*.jpg")

class TestImagePreprocessor:
    # 테스트를 수행하기 위해 미리 준비해야 하는 환경을 정의하는 데코레이터
    # 함수마다 매번 ImagePreprocessor() 수행하지 않아도 되니 코드가 깔끔해지고 효율적
    @pytest.fixture
    def preprocessor(self):
        """테스트에 사용할 클래스 인스턴스를 미리 생성"""
        return ImagePreprocessor()

    # 동일한 테스트 로직을 여러 개의 서로 다른 데이터로 반복해서 실행하는 데코레이터
    # 파라미터를 통해 흑백(2D)과 컬러(3D) 입력을 한 번에 테스트
    @pytest.mark.parametrize("input_shape", [
        (100, 100),      # 흑백 입력
        (100, 100, 3),   # 컬러(RGB) 입력
        (100, 100, 4)    # 투명도 포함(RGBA)
    ])
    def test_enhance_image_converts_to_grayscale(self, preprocessor, input_shape: tuple):
        """
        검증 내용: 어떤 차원의 이미지가 입력되어도 결과는 항상 2차원(흑백)이어야 함
        """
        # 1. 더미 이미지 생성
        input_img = np.zeros(input_shape, dtype=np.uint8)

        # 2. 이미지 전처리
        result = preprocessor.enhance_image(input_img)

        # 3. 검증
        # 차원 수 확인
        assert len(result.shape) == 2, f"입력 {input_shape}에 대해 결과가 2차원이 아님: {result.shape}"
        # 가로, 세로 크기 유지
        assert result.shape == input_shape[:2]
        # 데이터 타입 유지 확인
        assert result.dtype == np.uint8

    # IMAGE_FILES 하위의 모든 .jpg를 대상으로 테스트 진행
    @pytest.mark.parametrize("image_path", IMAGE_FILES)
    def test_with_real_files(self, preprocessor, image_path):
        """
        검증 내용: 색상이 있는 금융거래조회서 이미지 처리 시 흑백으로 변경되었는지 확인
        """
        img = cv2.imread(image_path)
        if img is None:
            pytest.skip(f"파일을 찾을 수 없거나 손상됨: {image_path}")

        result = preprocessor.enhance_image(img)
        assert len(result.shape) != len(img.shape), f"{image_path}의 채널 수가 변했습니다."
        assert result.shape[:2] == img.shape[:2], "이미지 해상도가 변형되었습니다."
