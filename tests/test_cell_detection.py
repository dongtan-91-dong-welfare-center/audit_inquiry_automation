import numpy as np
from PIL import Image
import cv2

from audit_inquiry_automation.extractor import extract_tables_from_image


def make_grid_image(cell_w=80, cell_h=40, cols=3, rows=4, line_thickness=2):
    width = cols * cell_w + (cols + 1) * line_thickness
    height = rows * cell_h + (rows + 1) * line_thickness
    img = np.ones((height, width, 3), dtype=np.uint8) * 255

    # draw vertical lines
    x = 0
    for c in range(cols + 1):
        x1 = c * (cell_w + line_thickness)
        cv2.rectangle(img, (x1, 0), (x1 + line_thickness - 1, height), (0, 0, 0), -1)

    # draw horizontal lines
    for r in range(rows + 1):
        y1 = r * (cell_h + line_thickness)
        cv2.rectangle(img, (0, y1), (width, y1 + line_thickness - 1), (0, 0, 0), -1)

    return Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))


def test_extract_tables_from_image_grid(monkeypatch):
    pil = make_grid_image(cell_w=50, cell_h=30, cols=4, rows=3, line_thickness=3)

    # OCR 모킹: 모든 셀은 빈 문자열로 처리해도 셀 분할은 확인 가능
    monkeypatch.setattr('audit_inquiry_automation.extractor.image_to_text', lambda img: "")

    tables = extract_tables_from_image(pil)
    assert len(tables) == 1
    df = tables[0]
    # rows=3, cols=4 -> df shape should be (3,4)
    assert df.shape == (3, 4)


def test_extract_tables_from_image_with_text(monkeypatch):
    pil = make_grid_image(cell_w=40, cell_h=20, cols=2, rows=2, line_thickness=2)
    # OCR 모킹: 모든 셀은 'X'로 채움
    monkeypatch.setattr('audit_inquiry_automation.extractor.image_to_text', lambda img: "X")
    tables = extract_tables_from_image(pil)
    assert len(tables) == 1
    df = tables[0]
    assert df.shape == (2, 2)
    assert df.iloc[0, 0] == "X"
