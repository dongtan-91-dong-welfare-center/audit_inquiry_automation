# src/core/preprocessor.py
import cv2
import numpy as np


class ImagePreprocessor:
    """
    금융 조회서 본문 페이지에서 표 영역을 탐지하여 크롭하는 MVP 전처리기입니다.
    문서 전체의 기울기를 계산하여 수평을 맞추는 로직이 포함되어 있습니다.
    """

    def process_pages(self, page_images: list[np.ndarray]) -> list[np.ndarray]:
        all_table_images = []
        for page_img in page_images:
            tables = self.process_page(page_img)
            # OCR 엔진(PaddleOCR) 호환을 위해 최종 출력 이미지를 3채널(BGR)로 통일
            bgr_tables = [
                cv2.cvtColor(tbl, cv2.COLOR_GRAY2BGR) if tbl.ndim == 2 else tbl 
                for tbl in tables
            ]
            all_table_images.extend(bgr_tables)
        return all_table_images

    def process_page(self, page_image: np.ndarray) -> list[np.ndarray]:
        # 1. 그레이스케일 및 2배 업스케일링 (OCR 인식률 확보)
        # INTER_CUBIC 보간법은 이미지 확대 시 가장 부드러운 결과를 제공하여 OCR 인식률을 높이는 데 도움이 됨
        if len(page_image.shape) == 3:
            gray = cv2.cvtColor(page_image, cv2.COLOR_BGR2GRAY)
        else:
            gray = page_image.copy()
        
        # [투 트랙 전략 적용]
        # 표 영역 탐지용 이미지 
        upscaled = cv2.resize(gray, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
        # =================================================================
        # OCR에 실제로 사용되는 세로선을 지운 깨끗한 이미지
        upscaled_no_lines = self._remove_vertical_lines(upscaled)


        # 2. 이진화 및 영역 팽창 (표 테두리 연결)
        """
        255 - 조건을 만족했을 때 칠할 색상 (255 = 완전한 흰색)
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C - 주변 밝기를 계산하는 방식 (가우시안: 중앙에 가중치를 두어 더 자연스럽게 계산)
        cv2.THRESH_BINARY_INV - 칠하는 방식 (INV = Invert, 즉 글자를 흰색으로, 배경을 검은색으로 반전)
        21 - 블록 크기 (홀수여야 하며, 주변 픽셀을 고려하는 영역의 크기. 작을수록 세밀하게 글자의 테두리를 잡아내지만 노이즈도 증가할 수 있음)
        5 - 상수 C (블록 평균에서 빼는 상수, 값이 클수록 더 적은 픽셀이 흰색으로 칠해짐. 즉, 클수록 글자 인식이 엄격해짐)
        kernel - pdf 스캔본을 확대해보면 끊어진 부분들이 존재하기 때문에 5*5 크기의 행렬로 붓의 역할을 수행하여 테두리를 연결함.
        dilate - 붓을 이용해 흰색 부분을 칠하는 작업을 3번 반복해 연결된 테두리를 만들어냄 (반복 횟수가 많을수록 더 넓게 연결됨)
        """
        binary = cv2.adaptiveThreshold(
            upscaled, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY_INV, 21, 5
        )
        kernel = np.ones((5, 5), np.uint8)
        dilate = cv2.dilate(binary, kernel, iterations=3)

        # 3. 외곽선 탐지
        """
        contours, _ - cv2.findContours 함수는 이미지에서 외곽선과 계층 정보를 반환하는데 계층 데이터는 저장하지 않는다는 파이썬 문법
        cv2.RETR_EXTERNAL - 가장 바깥쪽의 외곽선만 찾음
        cv2.CHAIN_APPROX_SIMPLE - 외곽선의 꼭짓점만 저장하여 메모리 절약 (예: 직사각형은 4개의 꼭짓점만 저장)
        """
        contours, _ = cv2.findContours(dilate, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        table_images= []
        # 페이지 면적의 1% 이상인 경우만 표로 간주 (제목 박스 등 미세 노이즈 배제)
        # shape[0]은 문서의 높이, shape[1]은 문서의 너비를 나타냅니다.
        min_table_area = (upscaled.shape[0] * upscaled.shape[1]) * 0.01

        for cnt in contours:
            if cv2.contourArea(cnt) > min_table_area:
                x, y, w, h = cv2.boundingRect(cnt)
                table_crop = upscaled[y:y + h, x:x + w]
                table_images.append({'img': table_crop, 'y': y, 'x': x})

        if not table_images:
            return []

        # 4. 문서 순서(위->아래, 왼쪽->오른쪽)에 따른 정렬
        table_images.sort(key=lambda s: (s['y'], s['x']))
        return [image['img'] for image in table_images]

    def _remove_vertical_lines(self, image: np.ndarray) -> np.ndarray:
        """
        OCR 엔진이 표의 세로선을 'I'나 '|'로 오인하는 것을 방지하기 위해 세로선을 제거합니다.
        """
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image.copy()
        
        # 1. 이미지 이진화 (배경은 검은색, 글자/선은 흰색)
        binary = cv2.adaptiveThreshold(
            gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 21, 10
        )

        # 2. 세로선 탐지용 커널 생성 (이미지 높이의 1/20 크기)
        # 낱개 글자('1', 'I')는 무시하고 긴 세로선만 잡기 위해 길게 설정합니다.
        """
        cv2.getStructuringElement - 모폴로지 연산에서 사용할 커널을 생성하는 함수. 위의 kernel = np.ones((5, 5), np.uint8)과 유사.
        cv2.MORPH_RECT - 직사각형 모양의 커널을 생성합니다. 세로선 탐지에 적합한 형태입니다.
        가로선 1픽셀, 세로선 vertical_size 픽셀
        """
        rows = binary.shape[0]
        vertical_size = rows // 20
        vertical_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, vertical_size))

        # 3. 모폴로지 연산을 통해 얇은 글자는 지우고 긴 세로선만 남기기
        """
        cv2.erode - vertical_kernel보다 큰 이미지만 남기고 나머지는 지우는 연산
        cv2.dilate - erode로 남은 세로선을 vertical_kernel 크기로 확장하여 더 명확하게 만듦
        """
        vertical_lines = cv2.erode(binary, vertical_kernel, iterations=1)
        vertical_lines = cv2.dilate(vertical_lines, vertical_kernel, iterations=1)

        # 4. 원본 이미지에서 탐지된 세로선 영역을 흰색(255)으로 칠해서 지워버리기
        result = gray.copy()
        result[vertical_lines > 0] = 255

        return result