# src/core/preprocessor.py
import cv2
import numpy as np

class ImagePreprocessor:
    """
    금융 조회서의 선명한 글자를 보존하며, 표 영역을 자동으로 탐지하여 크롭합니다.
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
        단일 페이지에서 표 영역을 찾아 크롭하고 전처리를 수행합니다.
        """
        # 1. Grayscale 변환 및 해상도 업스케일링 (인식률 향상)
        # 전문가 의견 반영: 블러를 제거하여 글자 선명도 유지
        gray = cv2.cvtColor(page_image, cv2.COLOR_BGR2GRAY)
        upscaled = cv2.resize(gray, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
        
        # 2. Adaptive Thresholding (이진화)
        # 글자가 이미 또렷하므로 블록 사이즈(11)를 유지하여 배경만 날림
        binary = cv2.adaptiveThreshold(
            upscaled, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
            cv2.THRESH_BINARY_INV, 11, 2  # 컨투어 탐색을 위해 글자를 흰색(INV)으로 설정
        )

        # 3. 표 영역(Table) 탐지를 위한 모폴로지 연산 (글자 훼손 없이 영역만 추출)
        # 글자 보정용이 아니라 '표 테두리'를 연결하기 위한 용도로만 잠시 사용
        kernel = np.ones((5, 5), np.uint8)
        dilate = cv2.dilate(binary, kernel, iterations=3)

        # 4. 외곽선(Contours) 찾기
        contours, _ = cv2.findContours(dilate, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        table_images = []
        min_table_area = (upscaled.shape[0] * upscaled.shape[1]) * 0.1  # 페이지의 10% 이상 크기만 표로 간주

        for cnt in contours:
            area = cv2.contourArea(cnt)
            if area > min_table_area:
                x, y, w, h = cv2.boundingRect(cnt)
                
                # 원본(upscaled)에서 해당 영역 크롭 (binary가 아닌 원본 그레이스케일 권장)
                # Tesseract는 이진화된 이미지보다 그레이스케일에서 자체 이진화를 할 때 결과가 좋을 때가 많음
                table_crop = upscaled[y:y+h, x:x+w]
                
                # (옵션) 크롭된 이미지에 선 제거 로직을 추가하거나, 
                # 현재는 원본의 선명함을 유지하기 위해 바로 반환
                table_images.append(table_crop)

        # 위에서 아래 방향으로 표 순서 정렬 (여러 표가 있을 경우 대비)
        table_images.sort(key=lambda x: x.shape[0], reverse=True) 
        
        return table_images if table_images else [upscaled] # 표를 못 찾으면 전체 페이지 반환