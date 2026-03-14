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
        with pytest.raises(ValueError, match="업로드한 파일"):
            PDFLoader(None)

        # 2. 잘못된 확장자 테스트
        mock_file = MagicMock()
        mock_file.name = "(주)삼성은행_4_신한은행.png"
        mock_file.size = 10 * 1024 * 1024

        with pytest.raises(ValueError, match="지원하지 않는 파일 형식"):
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
        mock_file.size = 10 * 1024 * 1024
        loader = PDFLoader(mock_file)

        # 비밀번호 예외를 감지하고 적절한 에러 메시지를 반환하는지 검증
        with pytest.raises(ValueError, match="비밀번호가 설정된|접근 권한"):
            loader.convert_to_images()

    @pytest.mark.unit
    def test_file_size_limit_exceeded(self):
        """PDF 크기가 제한(예: 300MB)을 초과하는 경우 에러를 반환하는지 확인합니다."""
        mock_file = MagicMock()
        mock_file.name = "(주)삼성전자_3_우리은행.pdf"
        # 파일 크기를 350MB (350 * 1024 * 1024 bytes)로 모킹
        mock_file.size = 367001600

        with pytest.raises(ValueError, match="크기 제한|300MB"):
            PDFLoader(mock_file)

    @pytest.mark.unit
    def test_filename_parsing_logic(self):
        """파일명에서 회사명과 조회처가 올바르게 분리되는지 확인합니다."""
        mock_file = MagicMock()
        mock_file.name = " 현대자동차 _ 01 _ 우리은행 .pdf"  # 공백이 섞인 경우 가정
        mock_file.size = 10 * 1024 * 1024

        loader = PDFLoader(mock_file)
        assert loader.metadata["company_name"] == "현대자동차"
        assert loader.metadata["bank_name"] == "우리은행"

    @pytest.mark.unit
    def test_filename_parsing_invalid_format(self):
        """규칙에 맞지 않는 파일명이 들어왔을 때 방어 로직이 작동하는지 확인합니다."""
        # Case A: 언더바가 없는 경우
        mock_file_invalid = MagicMock()
        mock_file_invalid.name = "삼성전자국민은행.pdf"
        mock_file_invalid.size = 10 * 1024 * 1024

        #  raises로 에러 발생을 확인
        with pytest.raises(ValueError, match="파일명 형식"):
            PDFLoader(mock_file_invalid)

        # Case B: 파트가 부족한 경우 (회사_숫자.pdf)
        mock_file_short = MagicMock()
        mock_file_short.name = "삼성전자_1.pdf"
        mock_file_short.size = 10 * 1024 * 1024

        with pytest.raises(ValueError, match="파일명 형식"):
            PDFLoader(mock_file_short)

    @pytest.mark.unit
    @patch("src.core.pdf_loader.cv2.cvtColor")
    @patch("pdfplumber.open")
    def test_convert_to_images_slicing(self, mock_pdf_open, mock_cv2_convert):
        """다양한 start_page 인자에 따라 올바른 페이지 수를 반환하는지 검증합니다."""
        # 공통 설정
        mock_cv2_convert.side_effect = lambda x, y: x

        # 업로드 파일 모킹 (pdfloader 생성용)
        mock_file = MagicMock()
        mock_file.name = "(주)삼성전자_6_제주은행.pdf"
        mock_file.size = 10 * 1024 * 1024

        # pdf 내용 모킹
        mock_pdf = MagicMock()
        mock_pdf.pages = [MagicMock()] * 10
        mock_pdf_open.return_value.__enter__.return_value = mock_pdf

        loader = PDFLoader(mock_file)

        # Case A: 기본값 적용 (3페이지부터 끝까지 -> 8개)
        assert len(loader.convert_to_images()) == 8

        # Case B: 특정 페이지 지정 (5페이지부터 끝까지 -> 6개)
        assert len(loader.convert_to_images(start_page=5)) == 6

        # Case C: 1페이지부터 전체 로드 (10개)
        assert len(loader.convert_to_images(start_page=1)) == 10

    @pytest.mark.unit
    @patch("cv2.cvtColor")
    @patch("pdfplumber.open")
    def test_convert_to_images_invalid_pages(self, mock_pdf_open, mock_cv2_convert):
        """DF 페이지 수가 시작 페이지 설정보다 적을 때의 에러 처리를 검증합니다."""
        # 공통 설정
        mock_cv2_convert.side_effect = lambda x, y: x

        # 업로드 파일 모킹 (pdfloader 생성용)
        mock_file = MagicMock()
        mock_file.name = "(주)삼성전자_5_IM은행.pdf"
        mock_file.size = 10 * 1024 * 1024

        # pdf 내용 모킹
        mock_pdf = MagicMock()
        mock_pdf.pages = [MagicMock()] * 10
        mock_pdf_open.return_value.__enter__.return_value = mock_pdf

        loader = PDFLoader(mock_file)

        # Case A: 2페이지 PDF에서 3페이지(기본값) 시작 요청 시 에러
        mock_pdf.pages = [MagicMock()] * 2
        with pytest.raises(ValueError, match="파일의 페이지가"):
            loader.convert_to_images()

        # Case B: 0페이지(빈 파일) PDF일 때 에러
        mock_pdf.pages = []
        with pytest.raises(ValueError, match="파일의 페이지가"):
            loader.convert_to_images()

        # Case C: 시작 페이지를 10으로 주었는데 실제론 5페이지일 때
        mock_pdf.pages = [MagicMock()] * 5
        with pytest.raises(ValueError, match="파일의 페이지가"):
            loader.convert_to_images(start_page=10)

