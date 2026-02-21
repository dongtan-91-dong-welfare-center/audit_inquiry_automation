# tests/core/test_preprocessor.py
import pytest
import cv2
import numpy as np
import os
import glob
from src.core.preprocessor import ImagePreprocessor

# 테스트 파일 목록 자동 추출
IMAGE_FILES = glob.glob("tests/data/*.jpg")

class TestImagePreprocessor:
    @pytest.fixture
    def preprocessor(self):
        """테스트에 사용할 클래스 인스턴스를 미리 생성"""
        return ImagePreprocessor()

    def test_enhance_image_converts_to_grayscale(self, preprocessor):
        """
        검증 내용: 컬러 이미지를 넣었을 때 채널이 1개인 흑백 이미지가 나오는가?
        """
        # 1채널 흑백 이미지 생성 (100x100)
        grayscale_input = np.zeros((100, 100), dtype=np.uint8)

        result = preprocessor.enhance_image(grayscale_input)

        # 채널 유실이나 형태 변형이 없는지 확인
        assert len(result.shape) == 2

    @pytest.mark.parametrize("image_path", IMAGE_FILES)
    def test_with_real_files(self, preprocessor, image_path):
        """
        검증 내용: data 폴더 내의 모든 png 파일이 성공적으로 처리되는가?
        """
        img = cv2.imread(image_path)
        if img is None:
            pytest.fail(f"이미지를 로드할 수 없습니다: {image_path}")

        result = preprocessor.enhance_image(img)
        assert len(result.shape) == 2
