# src/core/preprocessor.py
import cv2
import numpy
import numpy as np
from numpy import ndarray


class ImagePreprocessor:
    """
    [비전 처리 담당자]
    OCR 인식률을 극대화하기 위해 이미지를 보정합니다.
    # TODO: 표가 크롭된 이미지일 때, 외곽 테두리(표 선)가 1,000픽셀이고, 글자가 100픽셀일 때 기울기를 올바르게 계산할 수 있나 확인
    # TODO: 글자가 있는 부분만 잘라서 각도를 계산하여 표 테두리에 의해 기울기에 영향을 받지 않도록 조정
    # TODO: 글자 획이 얇아지면 커널 크기를 줄이거나 닫힘 연산을 조정하여 글자 연결성 확보
    # TODO: 적응형 이진화 상수(C) 조정하여 글자가 얇아지거나 굵어지는 것을 방지
    """
    def enhance_image(self, image: np.ndarray) -> ndarray:
        """
        단일 이미지를 입력받아 노이즈 제거 및 보정을 수행합니다.
        흐름: 그레이스케일 -> 블러링 -> 이진화 -> 기울기 보정 -> 모폴로지(열림/닫힘)

        Args:
            image (numpy.ndarray): OpenCV로 읽어온 BGR 이미지 데이터

        Returns:
            numpy.ndarray: 전처리가 완료된 이미지
        """
        # 1. 그레이스케일(Grayscale)  변환 수행
        """
        numpy.ndarray.shape: 배열의 차원을 나타내는 함수
        컬러이미지의 배열: (세로, 가로, 3), 흑백이미지의 배열: (세로, 가로)
        """
        if len(image.shape) == 3:  # 컬러 이미지인 경우
            processed_image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)   # 흑백 이미지로 변환
        else:
            processed_image = image.copy()

        # 2. 가우시안 블러(Gaussian Blur)를 적용하여 미세한 스캔 노이즈 제거
        """
        가우시안 블러: 각 픽셀을 주변 픽셀의 가중 평균값으로 교체하여 이미지를 부드럽게 만드는 깁법
        이미지 스캔 시 발생하는 미세한 노이즈 제거
        ksize는 필터의 중심 픽셀을 기준으로 주변을 계산해야 하므로 홀수여야 함
        kernel size가 커지면 연산량이 증가하고, 이미지가 너무 흐릿해져 글자를 인식하는 데 어려움 발생 가능
        -> ksize는 (3, 3) 또는 (5, 5)가 일반적
        """
        processed_image = cv2.GaussianBlur(processed_image, (3, 3), 0)

        # 3. 어댑티브 임계값 처리(Adaptive Thresholding)로 이진화 수행
        """
        어댑티브 임계값: 전체 이미지의 평균을 기준으로 0(검정)과 255(하양)로 구분하는 것이 아니라
        이미지를 작은 구역으로 나누어 임계값마다 배경은 하얗게(255), 글자는 까맣게(0) 처리
        -> 스캔 문서에서 명암 차이에서도 글자를 잘 찾아내게 함
        - 255: 임계값을 넘었을 때 부여할 최대값으로 흰색을 만들어야 하므로 255 고정
        - cv2.ADAPTIVE_THRESH_GAUSSIAN_C: 주변 영역의 평균을 구할 때 중앙부 픽셀에 가중치를 두어 조명 변화에 더 유연하게 대응하기 위한 가우시안 가중치
        - cv2.THRESH_BINARY: 기준보다 밝으면 255, 어두우면 0으로 나누는 이진화 방식
        - 11 (blockSize): 임계값을 계산할 주변 영역의 크기(11x11)입니다. 글자의 획 굵기보다 충분히 커야 글자와 배경을 구분 가능
        - 2 (C): 계산된 평균값에서 뺄 상수입니다. 노이즈를 미세하게 조절하여 배경을 더 깨끗하게 날리는 역할
        """
        processed_image = cv2.adaptiveThreshold(
            processed_image, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2
        )

        # 4. 이미지 기울기 보정(Deskewing) 로직 호출
        angle = self._get_skew_angle(processed_image)
        if abs(angle) > 0.5:    # 0.5도 미만의 미세한 기울기는 OCR 엔진이 자체적으로 허용 범위 내에서 처리할 수 있는 수준
            # 기울어진 각도의 반대 방향으로 회전을 시켜야 수평을 맞출 수 있음
            processed_image = self._rotate_image(processed_image, -angle)

        # 5. 모폴로지 팽창/침식 연산을 통해 끊어진 표의 선을 보정
        """
        모톨로지 연산: 이미지의 형태를 변경하는 연산
        - 팽창: 글자를 두껍게 하여 이미지의 형태를 변경하는 연산
        - 침식: 글자를 얇게 하여 붙어 있는 노이즈를 제거
        - 열림: 침식 후 팽창(작은 점 노이즈 제거)
        - 닫힘: 팽창 후 침식(끊어진 선 연결)
        - 커널: 특정 픽셀을 검증하기 위해 주변을 살피는 범위
        """
        kernel = np.ones((3, 3), np.uint8)

        processed = cv2.morphologyEx(processed_image, cv2.MORPH_OPEN, kernel)   # 열림
        processed = cv2.morphologyEx(processed, cv2.MORPH_CLOSE, kernel)    # 닫힘

        return processed

    @staticmethod
    def _get_skew_angle(binary_image: numpy.ndarray) -> float:
        """
        이미지 내 텍스트 픽셀의 분포를 분석하여 기울어진 각도를 계산합니다.

        Args:
            binary_image: 이진화된 이미지 (배경: 255, 글자: 0)
        Returns:
            보정해야 할 각도 (float)
        """
        # 1. 이미지 내의 텍스트 픽셀 좌표를 추출하여 회전 각도 산출
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
        y_coords, x_coords = np.where(binary_image < 127)  # 255 // 2 = 127 이므로 127보다 작은 것은 검정색이라고 인식

        # 2. 좌표 순서 교정 (y, x) -> (x, y)
        # openCV 함수는 (x, y) 형태의 좌표계를 사용
        coords = np.column_stack((x_coords, y_coords))

        # 3. 텍스트의 최소 면적 사각형(minAreaRect)을 찾아 수평 각도 산출
        """
        사각형을 회전시키며 글자 픽셀을 감싸는 넓이가 제일 작은 사각형을 찾는 함수
        이 때 사각형의 각도가 문서가 삐뚫어진 각도와 일치함
        binary_image는 배경이 255(흰색), 글자가 0(검은색)이므로 반전시켜 좌표를 추출
        """
        if not len(coords):
            return 0.0

        # 반시계 방향으로 기울어지면 양수, 시계 방향으로 기울어지면 음수 반환
        # 이미지 좌표계는 아래로 내려갈수록 Y의 값이 커짐
        rect = cv2.minAreaRect(coords)
        angle = rect[-1]
        width, height = rect[1]

        # 4. 사각형의 가로/세로 길이를 비교하여 긴 변을 기준으로 각도를 보정
        if width < height: angle += 90

        # 5. 가장 가까운 수평/수직 축과의 차이를 계산
        # (angle + 45) % 90 - 45 는 항상 각도를 [-45, 45]로 매핑함
        # 그 후, 이미지 좌표계(y-down) 특성을 반영하여 부호를 반전시킴
        skew_angle =  -((angle + 45) % 90 - 45)

        return skew_angle

    @staticmethod
    def _rotate_image(image: np.ndarray, angle: float) -> np.ndarray:
        """
        주어진 각도만큼 이미지를 아핀 변환(Affine Transformation)을 통해 회전시킵니다.
        """
        h, w = image.shape[:2]
        center = (w // 2, h // 2)

        # 1. 이미지 중심점을 기준으로 회전 행렬 생성
        # 모든 픽셀 좌표(x, y)에 곱할 행렬을 전달해야 함
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
