import types
import pytest
import pandas as pd

from audit_inquiry_automation.detection import detect_tables


class FakePage:
    def __init__(self, tables):
        self._tables = tables

    def extract_tables(self):
        return self._tables


class FakePDF:
    def __init__(self, pages):
        self.pages = pages


def fake_open_with_table(path):
    return types.SimpleNamespace(__enter__=lambda s: FakePDF([FakePage([["col1", "col2"], ["a", "b"]])]), __exit__=lambda s, *e: None)


def test_detect_tables_with_table(monkeypatch):
    monkeypatch.setattr("pdfplumber.open", lambda p: fake_open_with_table(p))
    tables = detect_tables("dummy.pdf")
    assert isinstance(tables, list)
    assert len(tables) == 1
    assert isinstance(tables[0], pd.DataFrame)
    assert tables[0].iloc[0, 0] == "col1"


def test_detect_tables_invalid_file():
    # 실제로 존재하지 않는 파일을 열면 FileNotFoundError가 발생해야 함
    with pytest.raises(FileNotFoundError):
        detect_tables("nonexistent_file_hopefully_12345.pdf")