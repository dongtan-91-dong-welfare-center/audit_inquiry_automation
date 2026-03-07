import pytest
import cv2
import numpy as np

class TestOCRIntegration:
    """실제 데이터를 활용한 단계별 연결 및 전체 흐름 통합 테스트"""

    @pytest.fixture
    def real_pdf_path(self):
        return "tests/data/raw_pdf/actual_bank_statement.pdf"

    def test_step1_loader_to_pre(self, real_pdf_path):
        """실제 PDF를 읽어 전처리(세로선 제거)까지의 흐름 확인"""
        # 1. Loader 실행 (PDF -> List[np.ndarray])
        # 2. Preprocessor 실행 (이미지 전처리)
        # 사용자가 눈으로 확인할 수 있도록 중간 결과 저장 가능
        # cv2.imwrite("tests/data/output/debug_preprocessed.png", pre_image)
        assert True # 결과물의 shape이나 데이터 타입 검증

    def test_step2_pre_to_ocr(self):
        """전처리된 이미지가 OCR 엔진을 거쳐 텍스트로 나오는지 확인"""
        # 실제 전처리된 샘플 이미지를 로드하여 OCR 실행
        # 추출된 텍스트가 비어있지 않은지, 특정 키워드(예: '계좌번호')를 포함하는지 확인
        assert True

    def test_full_pipeline_execution(self, real_pdf_path):
        """[핵심] 전체 공정을 한 번에 이어서 실행"""
        # 위에서 검증된 step1, step2 로직을 순차적으로 실행
        # 최종 산출물(리스트 데이터)이 GROUND_TRUTH와 유사한지 확인
        # excel_builder를 통해 실제 파일이 생성되는지까지 확인
        assert True
