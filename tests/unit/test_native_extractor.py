import pytest
from unittest.mock import MagicMock, patch
from src.core.native_extractor import NativeExtractor

class TestNativeExtractor:
    @pytest.mark.unit
    @patch("pdfplumber.open")
    def test_extract_table_data(self, mock_pdf_open):
        """NativeExtractor가 pdfplumber를 이용해 제대로 표를 추출하는지 검증합니다."""
        mock_pdf = MagicMock()
        mock_page1 = MagicMock()
        mock_page2 = MagicMock()

        # 첫 번째 페이지 표 추출 가짜 데이터
        mock_page1.extract_tables.return_value = [[
            ["Header1", "Header2"],
            ["Row1Col1", "Row1Col2"]
        ]]
        # 두 번째 페이지 표 추출 가짜 데이터 (일부 None 포함)
        mock_page2.extract_tables.return_value = [[
            ["Header3", "Header4"],
            ["Row2Col1", None]
        ]]

        mock_pdf.pages = [mock_page1, mock_page2]
        mock_pdf_open.return_value.__enter__.return_value = mock_pdf

        extractor = NativeExtractor()

        # 파일 포인터를 모킹하여 seek가 있더라도 에러나지 않게 설정
        mock_stream = MagicMock()

        tables = extractor.extract_table_data(mock_stream, start_page=1, end_page=2)

        assert len(tables) == 2
        assert tables[0] == [["Header1", "Header2"], ["Row1Col1", "Row1Col2"]]
        assert tables[1] == [["Header3", "Header4"], ["Row2Col1", ""]]
