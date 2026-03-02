# src/core/preprocessor.py
import cv2
import numpy as np


class ImagePreprocessor:
    """
    금융 조회서 본문 페이지에서 표 영역을 탐지하여 크롭하는 MVP 전처리기입니다.
    """

    def process_pages(self, page_images: list[np.ndarray]) -> list[np.ndarray]:
        all_table_images = []
        for page_img in page_images:
            tables = self.process_page(page_img)
            all_table_images.extend(tables)
        return all_table_images

    def process_page(self, page_image: np.ndarray) -> list[np.ndarray]:
        # 1. 그레이스케일 및 2배 업스케일링 (OCR 인식률 확보)
        gray = cv2.cvtColor(page_image, cv2.COLOR_BGR2GRAY)
        upscaled = cv2.resize(gray, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)

        # 2. 이진화 및 영역 팽창 (표 테두리 연결)
        binary = cv2.adaptiveThreshold(
            upscaled, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY_INV, 21, 5
        )
        kernel = np.ones((5, 5), np.uint8)
        dilate = cv2.dilate(binary, kernel, iterations=3)

        # 3. 외곽선 탐지
        contours, _ = cv2.findContours(dilate, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        table_data = []
        # 페이지 면적의 1% 이상인 경우만 표로 간주 (제목 박스 등 미세 노이즈 배제)
        min_table_area = (upscaled.shape[0] * upscaled.shape[1]) * 0.01

        for cnt in contours:
            if cv2.contourArea(cnt) > min_table_area:
                x, y, w, h = cv2.boundingRect(cnt)
                table_crop = upscaled[y:y + h, x:x + w]
                table_data.append({'img': table_crop, 'y': y, 'x': x})

        if not table_data:
            return []

        # 4. 문서 순서(위->아래, 왼쪽->오른쪽)에 따른 정렬
        table_data.sort(key=lambda s: (s['y'], s['x']))
        return [data['img'] for data in table_data]
