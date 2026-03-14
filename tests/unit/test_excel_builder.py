# tests/unit/test_excel_builder.py

import pytest
from unittest.mock import patch, MagicMock
from src.core.excel_builder import ExcelBuilder


class TestExcelBuilderUnit:
    """ExcelBuilder 내부의 파일 I/O 및 데이터 병합 로직 검증"""

    @pytest.fixture(autouse=True)
    def setup(self):
        """
        테스트가 실행될 때마다 실제 폴더가 생성되는 것을 방지하기 위해 os.makedirs를 Mocking 처리합니다.
        """
        # patcher를 수동으로 시작하여 테스트 끝까지 Mock 유지
        self.makedirs_patcher = patch('os.makedirs')
        self.mock_makedirs = self.makedirs_patcher.start()

        # 가짜 경로를 주입하여 객체 생성
        self.builder = ExcelBuilder(template_dir="/mock/templates", output_dir="/mock/output")

        yield  # 여기서 실제 테스트 함수들이 실행됩니다.

        # 테스트가 종료되면 Mocking을 해제하여 다른 테스트에 영향을 주지 않도록 함
        self.makedirs_patcher.stop()

    @pytest.mark.unit
    def test_build_sheet_data_map(self):
        """엑셀 시트명과 데이터 딕셔너리 매핑 로직 검증"""
        # Given: 가짜 워크북 객체 및 시트명 세팅
        mock_wb = MagicMock()
        mock_wb.sheetnames = ["1.금융상품_커스텀", "2.대출거래_커스텀"]

        processed_tables = {
            "financial_table": [["예금", "111-222"]],
            "loan_table": [["신용대출", "5000"]]
        }

        # When
        result = self.builder.build_sheet_data_map(mock_wb, processed_tables)

        # Then: 실제 시트명에 맞게 데이터가 할당되어야 함
        assert len(result) == 2
        assert "1.금융상품_커스텀" in result
        assert "2.대출거래_커스텀" in result
        assert result["1.금융상품_커스텀"] == [["예금", "111-222"]]

    @pytest.mark.unit
    @patch('os.path.exists')
    def test_missing_template_raises_error(self, mock_exists):
        """템플릿 파일이 없을 때 FileNotFoundError 발생 검증"""
        # os.path.exists가 항상 False를 반환하도록 조작 (출력 파일도 없고, 템플릿도 없음)
        mock_exists.return_value = False

        # 에러가 발생하는지 확인하는 pytest 구문
        with pytest.raises(FileNotFoundError, match="템플릿 파일이 존재하지 않습니다"):
            self.builder.export_to_excel(
                company_name="테스트회사",
                bank_name="테스트은행",
                processed_tables={"financial_table": [["데이터"]]}
            )

    @pytest.mark.unit
    @patch('os.path.exists')
    @patch('shutil.copy')
    @patch('openpyxl.load_workbook')
    def test_export_data_append_logic(self, mock_load_wb, mock_copy, mock_exists):
        """데이터 삽입 및 조회처 꼬리표 부착 로직 검증"""

        # 1. 파일 시스템 상태 모의: os.path.exists
        # 처음 호출(출력 파일 확인) 시 False 반환 -> 두 번째 호출(템플릿 파일 확인) 시 True 반환
        # if not os.path.exists(output_path) -> False
        # if not os.path.exists(template_path) -> True
        mock_exists.side_effect = [False, True, True, True]

        # 2. openpyxl 워크북 및 워크시트 상태 모의
        mock_wb = MagicMock()
        mock_ws = MagicMock()
        mock_wb.sheetnames = ["1.금융상품"]
        # wb["1.금융상품"] 을 호출했을 때 mock_ws를 반환하도록 매직 메서드 조작
        mock_wb.__getitem__.return_value = mock_ws
        mock_load_wb.return_value = mock_wb

        # 3. 입력 데이터 준비
        test_company = "삼성전자"
        test_bank = "농협은행"
        processed_tables = {
            "financial_table": [["정기예금", "123-456", "10,000"]]
        }

        # When: 엑셀 내보내기 실행
        self.builder.export_to_excel(test_company, test_bank, processed_tables)

        # Then 1: 파일이 없었으므로 템플릿 복사(shutil.copy)가 1회 호출되어야 함
        mock_copy.assert_called_once()

        # Then 2: 마지막 열에 test_bank("농협은행")가 덧붙여진 채로 append 되어야 함
        expected_row = ["정기예금", "123-456", "10,000", test_bank]
        mock_ws.append.assert_called_once_with(expected_row)

        # Then 3: 파일 저장 및 닫기가 누락 없이 수행되어야 함
        mock_wb.save.assert_called_once()
        mock_wb.close.assert_called_once()
