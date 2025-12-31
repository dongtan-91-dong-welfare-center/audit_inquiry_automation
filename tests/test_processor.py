import types
import pandas as pd
from audit_inquiry_automation.processor import process_pdf_to_excel


def test_process_pdf_to_excel(tmp_path, monkeypatch):
    # 모킹: 추출 함수가 두 개의 DataFrame을 반환
    dummy_tables = [pd.DataFrame({"a": [1]}), pd.DataFrame({"b": [2]})]
    monkeypatch.setattr("audit_inquiry_automation.extractor.extract_tables_from_pdf", lambda p: dummy_tables)

    out = tmp_path / "out.xlsx"
    count = process_pdf_to_excel("dummy.pdf", str(out))
    assert count == 2
    # 파일 존재 확인
    assert out.exists()
