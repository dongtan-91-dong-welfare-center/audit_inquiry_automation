# src/core/pdf_loader.py

class PDFLoader:
    """
    [파일 처리 담당자]
    Streamlit에서 업로드된 PDF를 OCR 처리가 가능한 이미지(고해상도)로 변환합니다.
    """
    def __init__(self, uploaded_file):
        self.uploaded_file = uploaded_file

    def convert_to_images(self):
        """
        PDF의 각 페이지를 이미지 객체(PIL Image 또는 numpy array)의 리스트로 반환합니다.
        """
        # TODO: pdf2image(convert_from_bytes) 또는 PyMuPDF(fitz) 라이브러리 연동
        # TODO: 이미지 변환 시 해상도(DPI)를 300 이상으로 설정하여 인식률 확보
        # return image_list
        pass