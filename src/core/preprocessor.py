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
            all_table_images.extend(tables)
        return all_table_images

    def process_page(self, page_image: np.ndarray) -> list[np.ndarray]:
        """
        단일 페이지에서 수평 보정 후 표 영역을 찾아 크롭하고 전처리를 수행합니다.
        """
        # =================================================================
        # 0. 기울기 계산 및 수평 보정 (Deskew)
        """
        gray_for_skew는 기울기 계산 및 수평 보정만을 위한 1회성 그레이스케일 이미지입니다.
        """
        if len(page_image.shape) == 3:  # BGR 컬러인 경우 흑백 변환
            gray_for_skew = cv2.cvtColor(page_image, cv2.COLOR_BGR2GRAY)
        else:
            gray_for_skew = page_image

        angle = self._get_skew_angle(gray_for_skew)
        
        # 0.5도 이상의 기울기가 감지되면 반대 방향으로 회전하여 수평을 맞춤
        if abs(angle) > 0.5:
            page_image = self._rotate_image(page_image, angle)

        # =================================================================
        # 1. 그레이스케일 및 2배 업스케일링 (OCR 인식률 확보)
        # INTER_CUBIC 보간법은 이미지 확대 시 가장 부드러운 결과를 제공하여 OCR 인식률을 높이는 데 도움이 됨
        gray = cv2.cvtColor(page_image, cv2.COLOR_BGR2GRAY)
        upscaled = cv2.resize(gray, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)

        # =================================================================
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

        # =================================================================
        # 3. 외곽선 탐지
        """
        contours, _ - cv2.findContours 함수는 이미지에서 외곽선과 계층 정보를 반환하는데 계층 데이터는 저장하지 않는다는 파이썬 문법
        cv2.RETR_EXTERNAL - 가장 바깥쪽의 외곽선만 찾음
        cv2.CHAIN_APPROX_SIMPLE - 외곽선의 꼭짓점만 저장하여 메모리 절약 (예: 직사각형은 4개의 꼭짓점만 저장)
        """
        contours, _ = cv2.findContours(dilate, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        table_images = []
        # 페이지 면적의 1% 이상인 경우만 표로 간주 (제목 박스, 서명 등 미세 노이즈 배제)
        # shape[0]은 문서의 높이, shape[1]은 문서의 너비를 나타냅니다.
        min_table_area = (upscaled.shape[0] * upscaled.shape[1]) * 0.01

        for cnt in contours:
            if cv2.contourArea(cnt) > min_table_area:
                x, y, w, h = cv2.boundingRect(cnt)
                table_crop = upscaled[y:y + h, x:x + w]
                table_images.append({'img': table_crop, 'y': y, 'x': x})

        if not table_images:
            return [upscaled]

        # =================================================================
        # 4. 문서 순서(위->아래, 왼쪽->오른쪽)에 따른 정렬
        table_images.sort(key=lambda s: (s['y'], s['x']))
        return [image['img'] for image in table_images]
    
    # =================================================================
    # Deskew(기울기 보정) 관련 로직
    # =================================================================
    @staticmethod
    def _get_skew_angle(gray_for_skew: np.ndarray) -> float:
        """
        문서 내 글자 배치 방향을 분석하여 얼마나 이미지가 기울어졌는지 계산합니다.
        """
        # 1. 배경과 글자를 명확히 분리 (Otsu 이진화)
        """
        0 - 255(흰색)을 적용할 임계치(기준값)인데 OTSU 알고리즘이 자동으로 최적의 값을 찾아주기 때문에 아무 숫자로 설정
        255 - 조건을 만족했을 때 칠할 색상 (255 = 완전한 흰색)
        cv2.THRESH_BINARY_INV | cv2.THRESH_OTSU - |는 비트 연산자로 두 가지 옵션을 동시에 적용하는 역할 (Otsu 알고리즘으로 최적 임계값 계산 + 글자를 흰색으로 반전)
        _, thresh - 오츠 알고리즘이 찾아낸 최적의 기준점, 흑백 이진화 이미지 결과물 중 이미지만 반환
        """
        _, thresh = cv2.threshold(gray_for_skew, 0, 255, cv2.THRESH_BINARY_INV | cv2.THRESH_OTSU)

        # 2. 글자(255인 흰색)가 있는 모든 좌표(x, y)를 추출
        # np 행렬은 행(y_coords)과 열(x_coords) 데이터 순으로 반환
        # 이를 opencv에서 사용하는 (x, y) 좌표 형태로 변환하기 위해 column_stack으로 묶어서 coords라는 2차원 배열(리스트)로 만듦
        y_coords, x_coords = np.where(thresh > 0)
        coords = np.column_stack((x_coords, y_coords))

        # 3. 모든 글자 좌표를 감싸는 '가장 작은 회전된 사각형'을 찾음
        # rect는 ((상자중심 x, 상자중심 y), (width, height), angle) 형태의 튜플을 반환
        if not len(coords):
            return 0.0

        rect = cv2.minAreaRect(coords)
        angle = rect[-1]
        width, height = rect[1]

        # 4. 사각형의 방향 보정
        if width < height: 
            angle += 90

        # 5. 최종 보정 각도 도출
        skew_angle = -((angle + 45) % 90 - 45)

        return skew_angle

    @staticmethod
    def _rotate_image(page_image: np.ndarray, angle: float) -> np.ndarray:
        """
        주어진 각도만큼 이미지를 회전하여 수평을 맞춥니다.
        회전 후 남는 모서리 부분은 흰색으로 채웁니다.
        """
        h, w = page_image.shape[:2]
        center = (w // 2, h // 2)

        rotation_matrix = cv2.getRotationMatrix2D(center, angle, 1.0)
        
        # 아핀 변환
        # flags=cv2.INTER_CUBIC는 회전 시 발생하는 빈 픽셀들을 주변 픽셀 16개를 기준으로 보간
        # borderMode=cv2.BORDER_CONSTANT는 회전 후 생기는 빈 공간(삼각형들)을 일정한 색상으로 채우는 옵션
        # borderValue=(255, 255, 255) - 컬러 이미지인 경우와 그레이스케일인 경우 모두 흰색으로 채움
        rotated = cv2.warpAffine(
            page_image, rotation_matrix, (w, h), 
            flags=cv2.INTER_CUBIC, 
            borderMode=cv2.BORDER_CONSTANT, 
            borderValue=(255, 255, 255) if len(page_image.shape) == 3 else 255
        )

        return rotated