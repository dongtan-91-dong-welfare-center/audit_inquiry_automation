import pytest
import numpy as np
from unittest.mock import MagicMock, patch
from src.core.pdf_loader import PDFLoader


class TestPDFLoader:

    # ---------------------------------------------------------
    # 1. Integration Tests (실제 PDF 데이터 기반 품질 검증)
    # ---------------------------------------------------------

    @pytest.mark.integration
    def test_image_format_and_quality(self, scan_pdf_path):
        """반환된 이미지의 타입, 채널, 해상도가 OCR에 적합한지 검증합니다."""
        with open(scan_pdf_path, "rb") as f:
            loader = PDFLoader(f)
            images = loader.convert_to_images(start_page=3)

        for i, img in enumerate(images):
            # 타입 및 채널 검증 (OpenCV BGR 포맷)
            assert isinstance(img, np.ndarray), f"{i}번째 결과가 numpy 배열이 아닙니다."
            assert img.ndim == 3 and img.shape[2] == 3, f"{i}번째 이미지 채널이 BGR(3)이 아닙니다."

            # 해상도 검증 (300 DPI 기준, OCR 인식률 보장을 위한 최소 높이/너비)
            height, width = img.shape[:2]
            assert height > 2000 or width > 2000, f"{i}번째 이미지 해상도가 OCR 기준에 미달합니다: {width}x{height}"

            # 데이터 유효성 검증 (빈 이미지가 아닌지 표준편차로 확인)
            assert np.std(img) > 0, f"{i}번째 이미지 데이터가 유효하지 않습니다."

    # ---------------------------------------------------------
    # 2. Unit Tests (Mock을 활용한 방어 로직 및 예외 처리 검증)
    # ---------------------------------------------------------

    @pytest.mark.unit
    def test_invalid_input_and_extension(self):
        """잘못된 입력(None) 및 확장자 핸들링을 테스트합니다."""
        # 1. None 입력 테스트
        with pytest.raises(ValueError, match="지원하지 않는 파일 형식입니다"):
            PDFLoader(None)

        # 2. 잘못된 확장자 테스트
        mock_file = MagicMock()
        mock_file.name = "not_a_pdf.png"

        with pytest.raises(ValueError, match="지원하지 않는 파일 형식입니다|pdf 파일만"):
            PDFLoader(mock_file)

    @pytest.mark.unit
    @patch("pdfplumber.open")
    def test_password_protected_pdf(self, mock_pdf_open):
        """비밀번호가 걸린 PDF 처리 시 방어 로직이 동작하는지 확인합니다."""
        # pdfplumber가 비밀번호가 걸린 파일을 열 때 발생하는 예외 모킹
        from pdfminer.pdfdocument import PDFPasswordIncorrect
        mock_pdf_open.side_effect = PDFPasswordIncorrect("")

        mock_file = MagicMock()
        mock_file.name = "(주)삼성전자_2_하나은행.pdf"
        loader = PDFLoader(mock_file)

        # 비밀번호 예외를 감지하고 적절한 에러 메시지를 반환하는지 검증
        with pytest.raises(ValueError, match="비밀번호가 설정된|접근 권한"):
            loader.convert_to_images()

    @pytest.mark.unit
    def test_filename_parsing_logic(self):
        """파일명에서 회사명과 조회처가 올바르게 분리되는지 확인합니다."""
        mock_file = MagicMock()
        mock_file.name = " 현대자동차 _ 01 _ 우리은행 .pdf"  # 공백이 섞인 경우 가정

        loader = PDFLoader(mock_file)
        assert loader.metadata["company_name"] == "현대자동차"
        assert loader.metadata["bank_name"] == "우리은행"

    @pytest.mark.unit
    def test_filename_parsing_invalid_format(self):
        """규칙에 맞지 않는 파일명이 들어왔을 때 방어 로직이 작동하는지 확인합니다."""
        # Case A: 언더바가 없는 경우
        mock_file_invalid = MagicMock()
        mock_file_invalid.name = "삼성전자국민은행.pdf"

        loader = PDFLoader(mock_file_invalid)
        assert loader.metadata["is_valid_format"] is False
        assert loader.metadata["company_name"] == "삼성전자국민은행"

        # Case B: 파트가 부족한 경우 (회사_숫자.pdf)
        mock_file_short = MagicMock()
        mock_file_short.name = "삼성전자_1.pdf"

        loader_short = PDFLoader(mock_file_short)
        assert loader_short.metadata["is_valid_format"] is False
        assert loader_short.metadata["bank_name"] == "형식오류_조회처"

    @pytest.mark.unit
    @patch("src.core.pdf_loader.cv2.cvtColor")
    @patch("pdfplumber.open")
    def test_page_slicing_and_default_logic(self, mock_pdf_open, mock_cv2_convert):
        """페이지 슬라이싱 로직과 기본값(3페이지) 적용 여부를 통합 검증합니다."""
        # 1. 가짜 PDF 설정 (총 10페이지)
        mock_pdf = MagicMock()
        mock_page  = MagicMock()

        # page.to_image().original이 호출될 때 반환할 가짜 값
        mock_page.to_image.return_value.original = np.zeros((100, 100, 3), dtype=np.uint8)
        mock_pdf.pages = [MagicMock()] * 10
        mock_pdf_open.return_value.__enter__.return_value = mock_pdf

        # cv2.cvtColor 호출 시 입력받은 것을 그대로 변환
        mock_cv2_convert.side_effect = lambda x, y: x

        loader = PDFLoader(MagicMock())

        # Case A: 3페이지부터 시작 (10 - 2 = 8개 기대)
        assert len(loader.convert_to_images(start_page=3)) == 8

        # Case B: 인자 생략 시 기본값(3) 적용 확인
        assert len(loader.convert_to_images()) == 8

        # Case C: 1페이지부터 전체 로드 (10개 기대)
        assert len(loader.convert_to_images(start_page=1)) == 10

    @pytest.mark.unit
    @patch("pdfplumber.open")
    def test_edge_cases_handling(self, mock_pdf_open):
        """범위를 벗어난 페이지나 빈 PDF 파일에 대한 방어 로직을 검증합니다."""
        # 가짜 PDF 설정 (총 2페이지)
        mock_pdf = MagicMock()
        mock_pdf.pages = [MagicMock(), MagicMock()]
        mock_pdf_open.return_value.__enter__.return_value = mock_pdf

        loader = PDFLoader(MagicMock())

        # Case A: 전체 페이지보다 큰 시작 페이지 요청
        assert loader.convert_to_images(start_page=5) == []

        # Case B: 빈 PDF 파일 (0페이지)
        mock_pdf.pages = []
        assert loader.convert_to_images() == []

