import importlib


def test_excel_writer_importable():
    # 단순히 엑셀 writer 모듈이 임포트 가능한지 확인
    mod = importlib.import_module('audit_inquiry_automation.excel_writer')
    assert hasattr(mod, 'write_tables_to_excel')