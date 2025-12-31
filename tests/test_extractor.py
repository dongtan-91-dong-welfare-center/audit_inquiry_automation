import types
import pytest
import pandas as pd

from audit_inquiry_automation import extractor


class NoTablePage:
    def extract_tables(self):
        return []

    def to_image(self, resolution=300):
        class Img:
            original = None

        return Img()


def test_ocr_fallback_parses_table(monkeypatch):
    # pdfplumber.open -> 페이지 목록이 NoTablePage 하나를 반환하도록 모킹
    monkeypatch.setattr(
        "pdfplumber.open",
        lambda p: types.SimpleNamespace(__enter__=lambda s: types.SimpleNamespace(pages=[NoTablePage()]), __exit__=lambda s, *e: None),
    )
    # OCR 결과 문자열을 모킹
    monkeypatch.setattr("audit_inquiry_automation.extractor.image_to_text", lambda img: "col1  col2\nval1  val2\nval3  val4")

    tables = extractor.extract_tables_from_pdf("dummy.pdf")
    assert len(tables) == 1
    df = tables[0]
    assert isinstance(df, pd.DataFrame)
    assert df.shape[1] == 2
    assert df.iloc[0, 0] == "col1"


def test_merge_consecutive_tables_simple():
    # 동일한 컬럼을 가진 두 개의 DataFrame은 병합되어야 함
    a = pd.DataFrame([["h1", "v1"], ["h1", "v2"]])
    a.columns = ["A", "B"]
    b = pd.DataFrame([["h1", "v3"]])
    b.columns = ["A", "B"]

    merged = extractor._merge_consecutive_tables([a, b])
    assert len(merged) == 1
    assert merged[0].shape[0] == 3


def test_merge_consecutive_tables_separate():
    # 컬럼이 다르면 분리 유지
    a = pd.DataFrame([["x"]])
    a.columns = ["X"]
    b = pd.DataFrame([["y", "z"]])
    b.columns = ["Y", "Z"]

    merged = extractor._merge_consecutive_tables([a, b])
    assert len(merged) == 2
