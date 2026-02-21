# src/core/preprocessor.py
import cv2
import numpy
import numpy as np
from numpy import ndarray


class ImagePreprocessor:
    """
    [비전 처리 담당자]
    OpenCV를 활용하여 문서 이미지의 기울기를 보정하고, 표 영역을 탐지하여 잘라낸 뒤,
    OCR 인식률을 극대화하기 위해 각 표의 이미지를 보정합니다.
    # TODO: 표가 크롭된 이미지일 때, 외곽 테두리(표 선)가 1,000픽셀이고, 글자가 100픽셀일 때 기울기를 올바르게 계산할 수 있나 확인
    """

    def process_page(self, page_image: np.ndarray) -> list[np.ndarray]:
        """
        단일 페이지 이미지를 입력받아 전체 흐름(기울기 보정 -> 표 탐지 -> 크롭 -> 개별 전처리)을 제어합니다.

        Args:
            page_image (np.ndarray): PDFLoader에서 전달받은 1페이지 분량의 원본 이미지(BGR)

        Returns:
            list[np.ndarray]: 전처리가 완료된 '표 영역 이미지'의 리스트
        """
        processed_tables = []

        # 1. 페이지 전체 기울기 보정(Deskew) 로직 호출
        # 원본 BGR 이미지를 임시로 그레이스케일로 변환하여 각도 계산에 사용
        if len(page_image.shape) == 3:
            gray_for_skew = cv2.cvtColor(page_image, cv2.COLOR_BGR2GRAY)
        else:
            gray_for_skew = page_image

        angle = self._get_skew_angle(gray_for_skew)
        if abs(angle) > 0.5:    # 0.5도 미만의 미세한 기울기는 OCR 엔진이 자체적으로 허용 범위 내에서 처리할 수 있는 수준
            # 표 외곽선을 정확히 찾기 위해 페이지 전체의 수평을 먼저 맞춥니다.
            # 기울어진 각도의 반대 방향으로 회전을 시켜야 수평을 맞출 수 있음
            page_image = self._rotate_image(page_image, -angle)

        # 2. 표 영역 탐지 (Table Detection)
        # TODO: _detect_tables 메서드를 호출하여 표들의 Bounding Box (x, y, w, h) 리스트를 획득
        bounding_boxes = self._detect_tables(page_image)

        # 3. 크롭 및 개별 전처리 수행
        for (x, y, w, h) in bounding_boxes:
            # TODO: numpy 슬라이싱(page_image[y:y+h, x:x+w])을 사용하여 표 영역만 크롭
            cropped_table = page_image[y:y+h, x:x+w]

            # TODO: 크롭된 이미지를 enhance_image()에 넘겨 이진화/노이즈 제거 등의 전처리 수행
            enhanced_table = self.enhance_image(cropped_table)

            # TODO: 처리된 표 이미지를 processed_tables 리스트에 추가
            processed_tables.append(enhanced_table)
            pass

        return processed_tables

    @staticmethod
    def _detect_tables(image: np.ndarray) -> list[tuple[int, int, int, int]]:
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image.copy()

        # 1. 이진화 (선이 연해도 잡을 수 있도록 C값을 높임)
        binary = cv2.adaptiveThreshold(
            gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 21, 10
        )

        # 2. 텍스트 라인을 덩어리로 묶음 (가로 팽창 강화)
        # 본문 표의 끊어진 행들을 하나로 묶기 위해 가로 커널을 키웁니다.
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (50, 3))
        dilate = cv2.dilate(binary, kernel, iterations=2)

        contours, _ = cv2.findContours(dilate, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        height, width = binary.shape
        bounding_boxes = []

        for contour in contours:
            x, y, w, h = cv2.boundingRect(contour)

            # [수정] 최소 조건 완화: 본문 표가 작게 찍힌 경우도 대비
            if w < width * 0.25 or h < 40:
                continue

            # [수정] 빽빽한 텍스트 덩어리(작성요령)를 거르는 밀도 (0.4 정도로 상향)
            roi_binary = binary[y:y + h, x:x + w]
            density = cv2.countNonZero(roi_binary) / (w * h)

            # 작성요령(image_8a0c1d.png)은 밀도가 매우 높지만,
            # 본문 표를 살리기 위해 밀도 필터는 보조적으로만 사용합니다.
            if density > 0.45:
                continue

            # [핵심] 위치 기반 필터: 작성요령은 보통 하단 75% 이후에 위치함
            # 만약 박스가 하단에 있으면서 높이가 낮다면 작성요령일 확률이 매우 높음
            if y > height * 0.75 and h < 250:
                # 이 영역은 작성요령일 가능성이 높으므로 건너뜁니다.
                continue

            bounding_boxes.append((x, y, w, h))

        # Y축 기준 정렬 (문서 흐름대로)
        bounding_boxes.sort(key=lambda b: b[1])
        return bounding_boxes

    # @staticmethod
    # def _detect_tables(image: np.ndarray) -> list[tuple[int, int, int, int]]:
    #     """
    #     이미지를 극단적으로 변형하여 글자는 지우고 표의 '선'만 추출해 좌표를 반환합니다.
    #     여기서 변환된 이미지는 반환되지 않고 버려집니다.
    #
    #     Args:
    #         image (np.ndarray): 기울기가 보정된 전체 페이지 이미지 (BGR 또는 Grayscale)
    #
    #     Returns:
    #         list[tuple[int, int, int, int]]: 탐지된 표들의 (x, y, w, h) 좌표 리스트 (위에서 아래 순서로 정렬 권장)
    #     """
    #     # 1. 그레이스케일(Grayscale) 변환
    #     """
    #     numpy.ndarray.shape: 배열의 차원을 나타내는 함수
    #     컬러이미지의 배열: (세로, 가로, 3), 흑백이미지의 배열: (세로, 가로)
    #     """
    #     if len(image.shape) == 3:  # 컬러 이미지인 경우
    #         gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)   # 흑백 이미지로 변환
    #     else:
    #         gray = image.copy()
    #
    #     # 2. 어댑티브 임계값 처리(Adaptive Thresholding)로 이진화 수행
    #     """
    #     어댑티브 임계값: 전체 이미지의 평균을 기준으로 0(검정)과 255(하양)로 구분하는 것이 아니라
    #     이미지를 작은 구역으로 나누어 임계값마다 배경은 하얗게(255), 글자는 까맣게(0) 처리
    #     -> 스캔 문서에서 명암 차이에서도 글자를 잘 찾아내게 함
    #     - 255: 임계값을 넘었을 때 부여할 최대값으로 흰색을 만들어야 하므로 255 고정
    #     - cv2.ADAPTIVE_THRESH_GAUSSIAN_C: 주변 영역의 평균을 구할 때 중앙부 픽셀에 가중치를 두어 조명 변화에 더 유연하게 대응하기 위한 가우시안 가중치
    #     - cv2.THRESH_BINARY: 기준보다 밝으면 255, 어두우면 0으로 나누는 이진화 방식
    #     - 11 (blockSize): 임계값을 계산할 주변 영역의 크기(11x11)입니다. 글자의 획 굵기보다 충분히 커야 글자와 배경을 구분 가능
    #     - 1 (C): 계산된 평균값에서 뺄 상수입니다. 노이즈를 미세하게 조절하여 배경을 더 깨끗하게 날리는 역할
    #     """
    #     binary = cv2.adaptiveThreshold(
    #         gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 15, -2
    #     )
    #
    #     # 이미지의 가로, 세로 길이 파악 (선 추출 커널의 기준 길이가 됨)
    #     height, width = binary.shape
    #
    #     # TODO: 형태학적 연산(Morphology)을 사용하여 가로선과 세로선을 추출 (cv2.getStructuringElement 활용)
    #     # 3. 모폴로지: 아주 길쭉한 커널을 사용하여 글자는 다 지우고 '긴 가로선'과 '긴 세로선'만 남김
    #     # 3-1. 가로선 추출 (Horizontal Line Detection)
    #     # 너비의 1/40 정도 길이를 가진 가로 커널 생성 (이 값은 문서 내 표의 크기에 따라 튜닝 필요)
    #     horizontal_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (50, 1))
    #     # 열림(Open) 연산: 커널 크기보다 작은 노이즈(일반 텍스트)는 지우고, 긴 가로선만 남김
    #     detect_horizontal = cv2.morphologyEx(binary, cv2.MORPH_OPEN, horizontal_kernel, iterations=2)
    #
    #     # 3-2. 세로선 추출 (Vertical Line Detection)
    #     # 높이의 1/40 정도 길이를 가진 세로 커널 생성
    #     vertical_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, height // 40))
    #     detect_vertical = cv2.morphologyEx(binary, cv2.MORPH_OPEN, vertical_kernel, iterations=2)
    #
    #     # 4. 표 교차점(Joint) 및 뼈대 마스크 생성
    #     # bitwise_and는 가로선과 세로선이 만나는 지점(T자, 十자)만 남깁니다. 텍스트는 이 지점이 거의 발생하지 않습니다.
    #     joints = cv2.bitwise_and(detect_horizontal, detect_vertical)
    #     table_mask = cv2.bitwise_or(detect_horizontal, detect_vertical)
    #
    #     # 5. 모든 윤곽선 탐지 및 1차 필터링
    #     contours, _ = cv2.findContours(table_mask, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
    #
    #     temp_boxes = []
    #     for contour in contours:
    #         x, y, w, h = cv2.boundingRect(contour)
    #         if w > width * 0.95 or h > height * 0.95:
    #             continue
    #         # 텍스트 오인식을 줄이기 위해 최소 길이를 상향 조정 (40 -> width // 20)
    #         if w > width // 20 or h > height // 20:
    #             temp_boxes.append([x, y, w, h])
    #
    #     # 6. 박스 병합 (Dynamic Padding 적용)
    #     dynamic_x_pad = width // 15
    #     dynamic_y_pad = height // 100
    #     merged_boxes = ImagePreprocessor._merge_boxes(temp_boxes, x_pad=dynamic_x_pad, y_pad=dynamic_y_pad)
    #
    #     # 7. 구조 분석 기반 최종 필터링 및 중복 제거
    #     bounding_boxes = []
    #     for x, y, w, h in merged_boxes:
    #         # 1. 작성요령 배제 (텍스트 밀도 체크)
    #         roi_binary = binary[y:y + h, x:x + w]
    #         black_pixels = cv2.countNonZero(roi_binary)
    #         density = black_pixels / float(w * h)
    #
    #         # 작성요령은 밀도가 매우 높습니다 (0.3 이상). 메인 표는 여백이 많아 0.1~0.2 수준입니다.
    #         if density > 0.35:
    #             continue
    #
    #         # 2. 세로 구조 분석 (가로선이 없어도 표임을 증명)
    #         # ROI 내에서 수직 투영(Vertical Projection)을 통해 열(Column) 개수 파악
    #         vertical_projection = np.sum(roi_binary, axis=0)
    #         # 픽셀 값이 있는 구간(글자)과 없는 구간(공백)의 변화 횟수 측정
    #         columns = 0
    #         in_column = False
    #         for val in vertical_projection:
    #             if val > 0 and not in_column:
    #                 columns += 1
    #                 in_column = True
    #             elif val == 0 and in_column:
    #                 in_column = False
    #
    #         # 금융조회서 메인 표는 보통 5개 이상의 열(Column)을 가집니다.
    #         if columns < 4:
    #             continue
    #
    #         # 3. 면적 및 비율 최종 필터
    #         if w * h < (width * height * 0.05) or w < width * 0.5:
    #             continue
    #
    #         bounding_boxes.append((x, y, w, h))
    #
    #     # 8. Y좌표 기준 정렬 반환
    #     bounding_boxes.sort(key=lambda box: box[1])
    #     return bounding_boxes

    @staticmethod
    def _merge_boxes(boxes: list[list[int]], x_pad: int, y_pad: int) -> list[tuple[int, int, int, int]]:
        if not boxes:
            return []

        # 초기 사각형 리스트 변환 [x1, y1, x2, y2]
        rects = [[b[0], b[1], b[0] + b[2], b[1] + b[3]] for b in boxes]

        merged = True
        while merged:
            merged = False
            new_rects = []
            while rects:
                r1 = rects.pop(0)
                matched = False
                for i, r2 in enumerate(new_rects):
                    # 인접 박스 판단 로직
                    if (r1[0] <= r2[2] + x_pad and r1[2] >= r2[0] - x_pad and
                        r1[1] <= r2[3] + y_pad and r1[3] >= r2[1] - y_pad):
                        new_rects[i] = [
                            min(r1[0], r2[0]),
                            min(r1[1], r2[1]),
                            max(r1[2], r2[2]),
                            max(r1[3], r2[3])
                        ]
                        matched = True
                        merged = True
                        break

                if not matched:
                    new_rects.append(r1)
            rects = new_rects

        # 결과 반환 시 중복 좌표를 한 번 더 걸러줌
        unique_results = sorted(list(set(tuple(r) for r in rects)))
        return [(r[0], r[1], r[2] - r[0], r[3] - r[1]) for r in unique_results]

    @staticmethod
    def enhance_image(cropped_image: np.ndarray) -> ndarray:
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
        가우시안 블러: 각 픽셀을 주변 픽셀의 가중 평균값으로 교체하여 이미지를 부드럽게 만드는 깁법
        이미지 스캔 시 발생하는 미세한 노이즈 제거
        ksize는 필터의 중심 픽셀을 기준으로 주변을 계산해야 하므로 홀수여야 함
        kernel size가 커지면 연산량이 증가하고, 이미지가 너무 흐릿해져 글자를 인식하는 데 어려움 발생 가능
        -> ksize는 (3, 3) 또는 (5, 5)가 일반적
        """
        processed_image = cv2.GaussianBlur(processed, (5, 5), 0)

        # 3. 이진화 (여기서는 INV를 쓰지 않음. 일반 문서처럼 배경은 하얗게, 글자는 까맣게)
        processed = cv2.adaptiveThreshold(
            processed_image, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 21, 10
        )

        # 4. 모폴로지 팽창/침식 연산을 통해 끊어진 표의 선을 보정
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

    @staticmethod
    def _get_skew_angle(binary_image: numpy.ndarray) -> float:
        """
        이미지 내 텍스트 픽셀의 분포를 분석하여 기울어진 각도를 계산합니다.

        Args:
            binary_image: 이진화된 이미지 (배경: 255, 글자: 0)
        Returns:
            보정해야 할 각도 (float)
        """
        # 1. Otsu의 이진화로 조명/그림자에 강건하게 배경과 텍스트 분리
        # 반전(INV)를 주어 글자를 255(흰색)으로 만듭니다.
        _, thresh = cv2.threshold(binary_image, 0, 255, cv2.THRESH_BINARY_INV | cv2.THRESH_OTSU)

        # 2. 이미지 내의 텍스트 픽셀 좌표를 추출하여 회전 각도 산출
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
        y_coords, x_coords = np.where(thresh > 0)   # 흰색 픽셀을 탐색

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
        주어진 각도만큼 아핀 변환(Affine Transformation)을 통해 이미지를 회전시킵니다.
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
