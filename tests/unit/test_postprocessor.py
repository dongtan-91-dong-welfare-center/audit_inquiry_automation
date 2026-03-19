# tests/unit/test_postprocessor.py

import os
import pytest
from src.core.pdf_loader import PDFLoader
from src.core.preprocessor import ImagePreprocessor
from src.core.ocr_engine import OCRExtractor
from src.core.postprocessor import PostProcessor
