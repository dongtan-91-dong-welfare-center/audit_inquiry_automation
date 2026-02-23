# src/core/preprocessor.py
import cv2
import numpy
import numpy as np
from numpy import ndarray


class ImagePreprocessor:
    """
    OpenCV를 활용하여 문서 이미지의 기울기를 보정하고, 표 영역을 탐지하여 잘라낸 뒤,
    OCR 인식률을 극대화하기 위해 각 표의 이미지를 보정합니다.
    # TODO: 표가 크롭된 이미지일 때, 외곽 테두리(표 선)가 1,000픽셀이고, 글자가 100픽셀일 때 기울기를 올바르게 계산할 수 있나 확인
    """

    def process_page(self, page_image: np.ndarray) -> list[np.ndarray]:
        """
        문서 한 장을 입력받아 [수평 보정 -> 표 찾기 -> 자르기 -> 화질 개선] 과정을 거쳐
        최종적으로 OCR 인식에 최적화된 표 이미지 리스트를 반환하여 OCR을 수행할 수 있도록 합니다.

        Args:
            page_image (np.ndarray): PDF에서 변환된 원본 이미지 (BGR 컬러)

        Returns:
            list[np.ndarray]: 전처리가 완료된 '표 영역 이미지'의 리스트
        """
        # 전처리한 표 이미지를 보관하는 배열
        processed_tables = []

        # 1. 기울기 계산을 위해 페이지 전체 기울기 보정(Deskew) 로직 호출
        # 흑백(Gray) 상태에서 각도 계산이 더 정확하므로 컬러인 경우 흑백으로 변환합니다.
        if len(page_image.shape) == 3:  # 이미지가 컬러인 경우 (BGR)
            gray_for_skew = cv2.cvtColor(page_image, cv2.COLOR_BGR2GRAY)
        else:
            gray_for_skew = page_image

        # 2. 표 외곽선을 정확하게 찾기 위해 이미지의 기울어진 각도를 계산하고, 문서를 올바르게 회전하여 수평을 맞춥니다.
        angle = self._get_skew_angle(gray_for_skew)
        if abs(angle) > 0.5:    # 0.5도 미만의 미세한 기울기는 OCR 엔진이 자체적으로 허용 범위 내에서 처리할 수 있는 수준
            # 기울어진 각도의 반대 방향으로 회전을 시켜야 수평을 맞출 수 있음
            page_image = self._rotate_image(page_image, -angle)

        # 3. 문서 내에서 표가 위치한 영역을 탐지하여 Bounding Box (x, y, w, h) 형태를 획득
        bounding_boxes = self._detect_tables(page_image)

        # 4. 각각의 표를 이미지로 잘라내어 전처리를 수행
        for (x, y, w, h) in bounding_boxes: # 탐지한 각 표의 4가지 좌표를 순화하면서
            # 이미지 배열 슬라이싱을 통해 표 영역을 잘라냅니다.
            cropped_table = page_image[y:y+h, x:x+w]
            # 잘라낸 표의 이미지를 제거하고 글자를 선명하게 합니다.
            enhanced_table = self._enhance_image(cropped_table)
            processed_tables.append(enhanced_table)

        return processed_tables 

    @staticmethod
    def _get_skew_angle(binary_image: numpy.ndarray) -> float:
        """
        문서 내 글자 배치 방향을 분석하여 얼마나 이미지가 기울어졌는지 계산합니다.

        Args:
            binary_image: 전처리가 필요한 이진화된 이미지 (배경: 255(흰색), 글자: 0(검은색))

        Returns:
            이미지를 똑바로 세우기 위해 보정해야 할 각도 (float, Degree 단위, 양수는 반시계 방향, 음수는 시계 방향)
        """
        # 1. 배경과 글자를 명확히 분리 (Otsu 이진화)
        # 글자 부분을 255(흰색)으로 반전해야 각도를 계산하여 데이터로 인식할 수 있습니다.
        _, thresh = cv2.threshold(binary_image, 0, 255, cv2.THRESH_BINARY_INV | cv2.THRESH_OTSU)

        # 2. 글자가 있는 모든 좌표(x, y)를 추출
        """
        np.column_stack((array1, array2)): 두 배열을 옆으로 나란히 붙여서 2차원 배열(좌표 쌍)로 만듭니다.
            > np.column_stack(([1, 2, 3, 3], [1, 1, 1, 2]))
            > [[1, 1], [2, 1], [3, 1], [3, 2]] (y, x 좌표 쌍 완성)

        np.where(조건):
            배열에서 조건을 만족하는 요소들의 '인덱스(위치)'를 행(y) 따로, 열(x) 따로 반환합니다.

        l자_글자 = np.array([
            [255, 255, 255, 255, 255],
            [255,   0, 255, 255, 255], # (1, 1) 위치
            [255,   0, 255, 255, 255], # (2, 1) 위치
            [255,   0,   0, 255, 255], # (3, 1), (3, 2) 위치
            [255, 255, 255, 255, 255]
        ])

        조건(0인 글자 위치)을 만족하는 행(row) 인덱스와 열(column) 인덱스 추출
            > np.where(l자_글자 < 127)
            > (array([1, 2, 3, 3]), array([1, 1, 1, 2]))
        해석: 1행, 2행, 3행, 3행에 데이터가 있고 / 각 1열, 1열, 1열, 2열에 데이터가 있음
        """
        y_coords, x_coords = np.where(thresh > 0)   # 검은색이 아닌 글자 픽셀의 좌표 추출

        # 좌표 순서 교정 (y, x) -> (x, y)
        # openCV 함수는 (x, y) 형태의 좌표를 요구함
        # 추출한 좌표를 [x, y] 쌍의 형태로 묶어 2차원 리스트로 변환
        coords = np.column_stack((x_coords, y_coords))

        # 3. 모든 글자 좌표를 감싸는 '가장 작은 회전된 사각형'을 찾음
        if not len(coords):
            return 0.0

        # MinAreaRect는 사각형을 회전시키며 글자 픽셀을 감싸는 넓이가 제일 작은 사각형을 찾는 함수
        # 사각형의 [중심점, (너비, 높이), 회전각도]를 반환
        # 이때 사각형의 각도가 문서가 삐뚫어진 각도와 일치함
        # 반시계 방향으로 기울어지면 양수, 시계 방향으로 기울어지면 음수 반환
        rect = cv2.minAreaRect(coords)
        angle = rect[-1]    # 사각형의 회전 각도 (Degree 단위)
        width, height = rect[1] # 사각형의 가로, 세로 길이 추출

        # 4. 사각형의 방향 보정
        # OpenCV의 MinAreaRect는 긴 변이 아닌 특정 축을 기준으로 각도를 주므로 긴 변을 수평 기준으로 삼도록 90도를 보정합니다. 
        # width가 height보다 짧으면 기준이 세로로 잡힌 것이므로 90도를 더해 정규화함
        if width < height: angle += 90

        # 5. 최종 보정 각도 도출
        # (angle + 45) % 90 - 45 는 어떤 각도를 넣던 간에 수평축 기준으로 -45도 사이에서 45도 사이의 가장 가까운 회전값으로 변환합니다.
        # 마지막에 마이너스를 붙여 이미지 좌표계(아래로 갈수록 Y값이 커지는 특성)에서 회전 방향을 맞춥니다.
        skew_angle =  -((angle + 45) % 90 - 45)

        return skew_angle

    @staticmethod
    def _rotate_image(image: np.ndarray, angle: float) -> np.ndarray:
        """
        주어진 각도만큼 이미지를 회전하여 수평을 맞춥니다.
        회전 후 남는 모서리 부분은 흰색으로 채웁니다.
        """
        h, w = image.shape[:2]
        # 이미지가 제자리에서 돌 수 있도록 중심점 좌표 설정
        center = (w // 2, h // 2)

        # 1. 이미지 중심점을 기준으로 angle만큼 회전하는 회전 행렬 생성
        # 모든 픽셀 좌표(x, y)에 이 회전 행렬을 적용하여 새로운 위치로 이동시킵니다.
        rotation_matrix = cv2.getRotationMatrix2D(center, angle, 1.0)

        # 2. 아핀 변환(warpAffine) 적용
        """
        선의 평행성을 유지하면서 이미지를 밀거나 회전시키거나 크기를 조절하는 변환
        생성 후, 회전 행렬을 이미지의 모든 픽셀에 적용하여 새로운 위치로 픽셀을 이동
        - image: 원본 이미지
        - rotation_matrix: getRotationMatrix2D로 만든 2x3 회전 지도
        - (w, h): 결과 이미지의 크기
        - flags=cv2.INTER_CUBIC: 픽셀이 이동할 때 빈 공간이 생기지 않도록 주변 값을 참고해 부드럽게 채우는 보간법
        - borderMode=cv2.BORDER_CONSTANT: 이미지 경계 밖의 영역을 어떻게 처리할지 결정
        - borderValue=255: 경계 밖(회전 후 남는 모서리 공간)을 흰색으로 채움
        """
        rotated = cv2.warpAffine(
            image, rotation_matrix, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_CONSTANT, borderValue=255
        )

        return rotated

    @staticmethod
    def _detect_tables(image: np.ndarray) -> list[tuple[int, int, int, int]]:
        """
        이미지를 극단적으로 변형하여 글자는 지우고 표의 '선'만 추출해 좌표를 반환합니다.
        여기서 변환된 이미지는 반환되지 않고 버려집니다.
    
        Args:
            image (np.ndarray): 기울기가 보정된 전체 페이지 이미지 (BGR 또는 Grayscale)
    
        Returns:
            list[tuple[int, int, int, int]]: 탐지된 표들의 (x, y, w, h) 좌표 리스트 (위에서 아래 순서로 정렬 권장)
        """
        # 1. 그레이스케일(Grayscale) 변환
        """
        numpy.ndarray.shape: 배열의 차원을 나타내는 함수
        컬러이미지의 배열: (세로, 가로, 3), 흑백이미지의 배열: (세로, 가로)
        """
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image.copy()

        # 2. 어댑티브 임계값 처리(Adaptive Thresholding)로 이진화 수행
        """
        어댑티브 임계값: 전체 이미지의 평균을 기준으로 0(검정)과 255(하양)로 구분하는 것이 아니라
        이미지를 작은 구역으로 나누어 임계값마다 배경은 하얗게(255), 글자는 까맣게(0) 처리
        -> 스캔 문서에서 명암 차이에서도 글자를 잘 찾아내게 함
        - 255: 임계값을 넘었을 때 부여할 최대값으로 흰색을 만들어야 하므로 255 고정
        - cv2.ADAPTIVE_THRESH_GAUSSIAN_C: 주변 영역의 평균을 구할 때 중앙부 픽셀에 가중치를 두어 조명 변화에 더 유연하게 대응하기 위한 가우시안 가중치
        - cv2.THRESH_BINARY: 기준보다 밝으면 255, 어두우면 0으로 나누는 이진화 방식
        - blockSize: 임계값을 계산할 주변 영역의 크기. 글자의 획 굵기보다 충분히 커야 글자와 배경을 구분 가능
        - C: 계산된 평균값에서 뺄 상수. 노이즈를 미세하게 조절하여 배경을 더 깨끗하게 날리는 역할
        """
        binary = cv2.adaptiveThreshold(
            gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 21, 10
        )

        # 3. 텍스트 라인을 덩어리로 묶음 (가로 팽창 강화)
        # 본문 표의 끊어진 행들을 하나로 묶기 위해 가로 커널을 키웁니다.
        # 가로 팽창: 표의 행이 끊어지는 경우가 많아서, 가로로 긴 커널을 사용하여 글자들이 하나의 덩어리로 묶이도록 합니다.
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (50, 3)) # 가로로 매우 긴 직사각형 커널
        dilate = cv2.dilate(binary, kernel, iterations=2)   # 가로 방향으로 픽셀을 번지게 함

        # findcontours: 이미지에서 글자들이 뭉쳐진 덩어리를 감싸는 외곽선을 찾는 함수
        # cv2.RETR_EXTERNAL은 가장 바깥쪽의 외곽선만 찾도록 하는 옵션입니다.
        # 가장 바깥쪽 테두리 하나만 깔끔하게 가져옴
        contours, _ = cv2.findContours(dilate, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        height, width = binary.shape
        bounding_boxes = []

        for contour in contours:
            x, y, w, h = cv2.boundingRect(contour)

            # 전체 너비의 25%보다 작거나, 높이가 40px 미만이면 무시 
            if w < width * 0.25 or h < 40:
                continue

            # 밀도 계산: 영역 내 실제 픽셀(글자/셀)이 차지하는 비율
            roi_binary = binary[y:y + h, x:x + w]
            density = cv2.countNonZero(roi_binary) / (w * h)

            # 밀도가 0.45가 넘으면 글자가 너무 빽빽한 일반 텍스트 영역으로 판단하여 제외
            if density > 0.45:
                continue

            # 하단 75% 이후에 나타나는 작은 박스는 데이터가 아닌 안내문구일 확률이 높음
            if y > height * 0.75 and h < 250:
                continue

            bounding_boxes.append((x, y, w, h))

        # Y축 기준 정렬 (문서 흐름대로)
        bounding_boxes.sort(key=lambda b: b[1])

        return bounding_boxes
    
    @staticmethod
    def _enhance_image(cropped_image: np.ndarray) -> ndarray:
        """
        원본 해상도를 유지한 잘라낸 표 이미지를 입력받아 노이즈를 제거하고 글씨를 뚜렷하게 이진화합니다.
        흐름: 그레이스케일 -> 블러링 -> 이진화 -> 모폴로지(열림/닫힘)

        Args:
            cropped_image (numpy.ndarray): OpenCV로 읽어온 BGR 이미지 데이터

        Returns:
            numpy.ndarray: 전처리가 완료된 이미지
        """
        # TODO: 크롭된 표 내부에서도 미세하게 틀어진 각도가 있다면 추가 Deskew 고려

        # 1. 그레이스케일 변환 (크롭된 이미지가 컬러일 수 있으므로 필수)
        if len(cropped_image.shape) == 3:
            processed = cv2.cvtColor(cropped_image, cv2.COLOR_BGR2GRAY)
        else:
            processed = cropped_image.copy()

        # 2. 가우시안 블러(Gaussian Blur)를 적용하여 미세한 스캔 노이즈 제거
        """
        가우시안 블러: 각 픽셀을 주변 픽셀의 가중 평균값으로 교체하여 이미지를 부드럽게 만드는 기법
        스캔된 이미지의 미세한 먼지(잡티)를 살짝 번지게 하여 지우는 작업입니다.
        ksize는 필터의 중심 픽셀을 기준으로 주변을 계산해야 하므로 홀수여야 함
        kernel size가 커지면 연산량이 증가하고 너무 많이 흐릿해져 글자를 인식하는 데 어려움 발생 가능
        -> ksize는 (3, 3) 또는 (5, 5)가 일반적
        """
        processed_image = cv2.GaussianBlur(processed, (5, 5), 0)

        # 3. 이진화 (배경은 하얗게, 글자는 까맣게)
        # OCR 엔진은 흰 배경/검은 글자 상태일 때 가장 인식률이 높음
        # 21(blockSize): 주변 영역 n개의 픽셀을 보고 밝기를 판단, 10(C): 평균에서 10만큼 어두워야 글씨로 인정
        """
        cv2.THRESH_BINARY_INV: 기준보다 밝으면 0, 어두우면 255으로 나누는 이진화 방식
        cv2.THRESH_BINARY: 기준보다 밝으면 255, 어두우면 0으로 나누는 이진화 방식
        """
        processed = cv2.adaptiveThreshold(
            processed_image, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 21, 10
        )

        # 4. 모폴로지 팽창/침식 연산을 통해 끊어진 표의 선을 보정
        # 팽창 후 침식을 수행하여, 글자의 미세한 끊김이나 표 선의 빈틈을 '메워주는' 역할입니다.
        # 너무 큰 커널을 쓰면 글자가 뭉쳐 보이므로 (2,2)로 조밀하게 처리합니다.
        """
        모톨로지 연산: 이미지의 형태를 변경하는 연산
        - 팽창: 글자를 두껍게 하여 이미지의 형태를 변경하는 연산
        - 침식: 글자를 얇게 하여 붙어 있는 노이즈를 제거
        - 열림: 침식 후 팽창(작은 점 노이즈 제거)
        - 닫힘: 팽창 후 침식(끊어진 선 연결)
        - 커널: 특정 픽셀을 검증하기 위해 주변을 살피는 범위
        """
        kernel = np.ones((2, 2), np.uint8)
        processed = cv2.morphologyEx(processed, cv2.MORPH_CLOSE, kernel)    # 닫힘

        return processed
    