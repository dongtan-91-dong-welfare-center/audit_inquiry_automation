# src/core/pdf_loader.py
import pdfplumber
import numpy as np
import cv2
from PIL import Image


class PDFLoader:
    """
    [파일 처리 담당자]
    Streamlit에서 업로드된 PDF를 읽어 들여, 비전 처리(OpenCV)에 적합한 고해상도 이미지 배열로 변환합니다.
    원본 페이지의 무손실 변환에 집중합니다.
    """
    def __init__(self, uploaded_file):
        """
        업로드된 스트림 기반의 PDF 파일 객체를 초기화합니다.

        Args:
            uploaded_file: Streamlit에서 전달받은 UploadedFile 객체
        """
        self.uploaded_file = uploaded_file

        # TODO: 파일명 유효성 및 확장자(.pdf) 검증 로직 추가 (validators.py 등 외부 유틸리티 연동 고려)

    def convert_to_images(self) -> list[np.ndarray]:
        """
        PDF의 각 페이지를 순회하며 OpenCV에서 처리 가능한 고해상도(300 DPI) BGR 이미지 배열로 변환합니다.

        Returns:
            list[numpy.ndarray]: 변환된 전체 페이지 이미지(BGR) 리스트
        """
        # TODO: pdfplumber.open(self.uploaded_file)을 사용하여 PDF 스트림 열기
        # TODO: pdf 내의 각 페이지(pages 속성)를 순회하는 반복문 작성
        # TODO: page.to_image(resolution=300)을 호출하여 각 페이지를 고해상도 이미지(PIL 객체)로 렌더링
        # TODO: 렌더링된 PIL 객체(기본 RGB 포맷)를 numpy.ndarray로 변환
        # TODO: cv2.cvtColor를 사용하여 RGB 채널을 OpenCV 기본 포맷인 BGR 채널로 변경
        # TODO: 변환이 완료된 BGR 이미지 배열을 리스트에 담아 반환 (대용량 파일 대비 제너레이터(yield) 패턴 사용 고려)

        all_pages_bgr = []

        # pdfplumber.open(self.uploaded_file)을 사용하여 PDF 스트림 열기
        with pdfplumber.open(self.uploaded_file) as pdf:
            # pdf 내의 각 페이지(pages 속성)를 순회하는 반복문 작성
            for page in pdf.pages:
                # page.to_image(resolution=300)을 호출하여 각 페이지를 고해상도 이미지(PIL 객체)로 렌더링
                img_pil = page.to_image(resolution=300).original    # resolution=300은 OCR 인식률 향상을 위한 고해상도 설정

                # 렌더링된 PIL 객체(기본 RGB 포맷)를 numpy.ndarray로 변환
                img_array = np.array(img_pil)

                # cv2.cvtColor를 사용하여 RGB 채널을 OpenCV 기본 포맷인 BGR 채널로 변경
                # PIL은 기본적으로 RGB 포맷이므로 OpenCV 처리를 위해 BGR로 변환이 필요
                img_bgr = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)

                # 변환이 완료된 BGR 이미지 배열을 리스트에 담아 반환
                all_pages_bgr.append(img_bgr)

        return all_pages_bgr

    def _extract_native_text_or_tables(self):
        """
        [추후 고도화 과제 - Native PDF Bypass]
        스캔본이 아닌, 디지털 방식으로 텍스트와 선 데이터가 포함되어 생성된(Native) PDF의 경우,
        무거운 전처리와 OCR 과정을 거치지 않고 pdfplumber의 자체 기능인 extract_text()나
        extract_tables()를 사용하여 데이터를 즉시 추출하는 우회 경로 로직입니다.
        """
        # TODO: 현재 문서가 Native PDF인지 스캔 이미지 덩어리인지 판별하는 로직 구현
        # TODO: Native PDF일 경우 직접 텍스트/표 데이터를 파싱하여 반환하는 파이프라인 분기 처리
        pass
