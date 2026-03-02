# src/core/preprocessor.py
import cv2
import numpy as np


class ImagePreprocessor:
    """
    금융 조회서에서 표 영역을 탐지하여 크롭하고 반환하는 전처리기입니다.
    """

    def process_pages(self, page_images: list[np.ndarray]) -> list[np.ndarray]:
        """
        여러 장의 페이지 이미지를 받아 각 페이지 내의 표 영역들을 추출합니다.
        """
        all_table_images = []
        for page_img in page_images:
            tables = self.process_page(page_img)
            all_table_images.extend(tables)
        return all_table_images

    def process_page(self, page_image: np.ndarray) -> list[np.ndarray]:
        """
        단일 페이지에서 표 영역을 찾아 크롭하여 반환합니다.
        """
        # 1. 이미지 기본 변환 및 해상도 조정
        gray = cv2.cvtColor(page_image, cv2.COLOR_BGR2GRAY)
        # OCR 인식률 향상을 위한 2배 업스케일링 유지
        upscaled = cv2.resize(gray, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)

        # [TODO: 스캔본의 기울기 보정(Deskewing) 로직 추가 예정]
        # [TODO: 노이즈 제거 및 글자 선명도 강화 필터 적용 예정]

        # 2. 표 탐지를 위한 최소한의 영역 연결 로직
        # 스캔본의 흐린 선을 감지하기 위해 블록 사이즈를 키워 이진화 수행
        binary = cv2.adaptiveThreshold(
            upscaled, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY_INV, 21, 5
        )

        # [TODO: 수직/수평 커널을 활용한 선 강조 로직으로 교체 검토]
        kernel = np.ones((5, 5), np.uint8)
        dilate = cv2.dilate(binary, kernel, iterations=3)

        # 3. 외곽선(Contours) 찾기 및 표 영역 확정
        contours, _ = cv2.findContours(dilate, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        table_data = []
        # 다중 표 인식을 위해 면적 임계값을 1%(0.01)로 설정
        min_table_area = (upscaled.shape[0] * upscaled.shape[1]) * 0.01

        for cnt in contours:
            area = cv2.contourArea(cnt)
            if area > min_table_area:
                x, y, w, h = cv2.boundingRect(cnt)

                # 원본(upscaled) 이미지에서 해당 좌표 영역 크롭
                table_crop = upscaled[y:y + h, x:x + w]

                # [TODO: 크롭된 이미지 내의 표 테두리 제거 로직 추가 예정]

                # 추출된 좌표(y, x)와 이미지 객체를 함께 저장
                table_data.append({'img': table_crop, 'y': y, 'x': x})

        # 4. 결과 반환 (표를 찾지 못한 경우 전체 페이지 반환)
        if not table_data:
            return [upscaled]

        # 문서를 읽는 일반적인 순서(위에서 아래, 왼쪽에서 오른쪽)로 정렬
        table_data.sort(key=lambda s: (s['y'], s['x']))

        return [data['img'] for data in table_data]
