import pytest
from PIL import Image
import pytesseract

from audit_inquiry_automation.ocr import image_to_text


def test_image_to_text_monkeypatched(monkeypatch):
    # pytesseract 결과를 모킹
    monkeypatch.setattr(pytesseract, "image_to_string", lambda img, lang=None: "hello world")
    img = Image.new("RGB", (10, 10), color="white")
    assert image_to_text(img) == "hello world"
