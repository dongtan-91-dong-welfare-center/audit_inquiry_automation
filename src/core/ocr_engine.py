# src/core/ocr_engine.py

class OCRExtractor:
    """
    [AI/OCR 담당자]
    전처리된 이미지에서 표 영역을 찾고 텍스트를 읽어냅니다.
    """
    def __init__(self):
        # TODO: 사용할 OCR 모델(EasyOCR, Tesseract, 또는 네이버 Clova API 등) 초기화
        pass

    def extract_table_data(self, processed_image):
        """
        이미지 내의 표를 인식하여 셀 단위의 원시 데이터(Raw Text)로 반환합니다.
        """
        # TODO: 이미지에서 표 테두리(Grid) 인식
        # TODO: 각 셀의 좌표(Bounding Box)를 기준으로 텍스트 추출
        # return raw_table_data (리스트 또는 딕셔너리 형태)
        pass