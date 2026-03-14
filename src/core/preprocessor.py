# src/core/preprocessor.py
import cv2
import numpy as np


class ImagePreprocessor:
    """
    금융 조회서 본문 페이지에서 표 영역을 탐지하여 크롭하고,
    OCR 인식률을 극대화하기 위한 전처리를 수행하는 전처리기입니다.

    이 클래스는 다음과 같이 동작합니다:
    1. 그레이스케일 변환 및 업스케일링 (해상도 확보)
    2. 적응형 이진화 및 팽창 연산 (끊어진 표 테두리 연결)
    3. 외곽선 탐지를 통한 표 영역 크롭 및 노이즈 필터링
    4. 세로선 제거 (OCR 엔진의 'I', '|' 오인식 방지) 및 3채널(BGR) 통일
    5. 문서 읽기 순서(위->아래, 좌->우)에 따른 결과 정렬

    ====================================================================
    [주요 OpenCV 함수 및 파라미터 상세 설명]

    1. 배열 및 해상도 처리
       - numpy.ndarray.shape: 이미지 배열의 차원을 나타냅니다.
         (컬러 이미지는 (세로, 가로, 3)의 3차원, 흑백은 (세로, 가로)의 2차원)
       - cv2.INTER_CUBIC (보간법): 이미지 확대 시 픽셀 사이의 값을 계산하는 방식입니다.
         다른 방식보다 가장 부드러운 결과를 제공하여 픽셀 깨짐을 막고 OCR 인식률을 높입니다.

    2. 적응형 이진화
       전체 이미지의 평균 밝기가 아닌, 이미지를 작은 구역(Block)으로 나누어
       각 구역의 조명 상태나 명암에 맞춰 배경은 하얗게(255), 글자/선은 까맣게(0) 처리합니다.
       스캔본의 불균일한 음영에서도 글자와 표의 실선을 명확히 분리해냅니다.
       - cv2.adaptiveThreshold(src, 255, ADAPTIVE_THRESH_GAUSSIAN_C, THRESH_BINARY_INV, blockSize, C)
       - 255: 조건을 만족했을 때 칠할 최대 색상값 (완전한 흰색).
       - cv2.ADAPTIVE_THRESH_GAUSSIAN_C: 주변 영역 평균을 구할 때 중앙부 픽셀에 가중치를 두어 조명 변화에 유연하게 대응합니다.
       - cv2.THRESH_BINARY_INV: 글자/선(어두운 부분)을 흰색(255)으로, 배경을 검은색(0)으로 반전시켜 추출합니다.
       - blockSize (예: 21): 임계값을 계산할 주변 영역의 픽셀 크기. 홀수여야 하며, 글자 획이나 선 굵기보다 커야 잘 구분됩니다.
       - C (상수, 예: 5 또는 10): 계산된 평균값에서 뺄 상수. 이 값이 클수록 노이즈가 줄고 글자 인식이 더 엄격해집니다.

    3. 모폴로지 연산 (팽창 및 침식)
       스캔본 특성상 희미하거나 끊어진 표의 실선들을 하나로 잇거나, 불필요한 노이즈를 지우는 붓 역할을 합니다.
       - cv2.getStructuringElement: 특정 모양(예: cv2.MORPH_RECT, 직사각형)의 커널(붓)을 생성합니다.
         (np.ones((5, 5), np.uint8) 처럼 직접 5x5 정방형 커널을 만들 수도 있습니다.)
       - cv2.dilate (팽창): 생성한 커널(붓)을 이용해 흰색 영역을 바깥으로 칠해나갑니다. 반복 횟수가
         많을수록 흰색 영역이 두꺼워져 끊어진 테두리들이 하나로 연결됩니다.
       - cv2.erode (침식): 커널보다 작은 흰색 영역은 깎아서 지우고 큰 덩어리만 남기는 연산입니다.

    4. 외곽선 탐지 (Contour Detection)
       팽창 연산으로 이어진 흰색 덩어리(표 테두리)들의 경계선을 찾습니다.
       - cv2.findContours(src, mode, method): 계층 데이터를 반환하지만 메모리 절약을 위해 언더바(_)로 무시합니다.
       - cv2.RETR_EXTERNAL: 이미지 내의 수많은 외곽선 중 가장 바깥쪽의 테두리(표 전체 윤곽)만 찾습니다.
       - cv2.CHAIN_APPROX_SIMPLE: 외곽선의 모든 픽셀을 저장하지 않고 꼭짓점(예: 직사각형은 4개)만 저장하여 메모리를 절약합니다.
       - cv2.boundingRect: 탐지된 외곽선을 감싸는 반듯한 최소 크기의 직사각형 좌표(x, y, w, h)를 구합니다.
    ====================================================================
    """


    def process_pages(self, page_images: list[np.ndarray]) -> list[np.ndarray]:
        """
        여러 장의 페이지 이미지를 입력받아 표를 추출하고 하나의 리스트로 통합합니다.

        Args:
            page_images (list[np.ndarray]): 원본 페이지 이미지 리스트
        Returns:
            list[np.ndarray]: 전처리가 완료된 표 이미지(3채널 BGR)의 1차원 리스트
        """
        all_table_images = []

        # 각 페이지별 표 추출 및 전처리 수행
        for page_img in page_images:
            tables = self._process_page(page_img)
            all_table_images.extend(tables)

        return all_table_images

    def _process_page(self, page_image: np.ndarray) -> list[np.ndarray]:
        """
        단일 페이지에서 표 영역을 크롭하고 전처리하여 문서 순서대로 정렬해 반환합니다.

        Args:
            page_image (np.ndarray): 단일 페이지 원본 이미지
        Returns:
            list[np.ndarray]: 크롭 및 전처리가 완료된 표 이미지 리스트
        """
        # 그레이스케일 및 2배 업스케일링
        if len(page_image.shape) == 3:
            gray = cv2.cvtColor(page_image, cv2.COLOR_BGR2GRAY)
        else:
            gray = page_image.copy()
        upscaled = cv2.resize(gray, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)

        # 이진화 및 영역 팽창 (표 테두리 연결)
        binary = cv2.adaptiveThreshold(
            upscaled, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY_INV, 21, 5
        )
        kernel = np.ones((5, 5), np.uint8)
        dilate = cv2.dilate(binary, kernel, iterations=3)

        # 가장 바깥쪽 테두리 탐지
        contours, _ = cv2.findContours(dilate, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        table_images = []

        # 페이지 면적의 1% 이상의 외곽선만 표로 간주 (미세 노이즈 배제)
        min_table_area = (upscaled.shape[0] * upscaled.shape[1]) * 0.01

        for cnt in contours:
            if cv2.contourArea(cnt) > min_table_area:
                # 외곽선을 감싸는 직사각형 영역 크롭
                x, y, w, h = cv2.boundingRect(cnt)
                table_crop = upscaled[y:y + h, x:x + w]

                # 크롭한 표 영역의 세로선 제거 및 3채널 변환 수행
                final_table = self._remove_vertical_lines(table_crop)
                table_images.append({'img': final_table, 'y': y, 'x': x})

        if not table_images:
            return []

        # 문서 순서(위->아래, 왼쪽->오른쪽)에 따른 정렬
        sorted_tables = self._sort_tables_by_coordinates(table_images)

        return [image['img'] for image in sorted_tables]

        return [image['img'] for image in table_images]

    @staticmethod
    def _remove_vertical_lines(image: np.ndarray) -> np.ndarray:
        """
        표 내부의 긴 세로선을 제거하고 OCR 호환을 위해 3채널(BGR)로 변환합니다.

        Args:
            image (np.ndarray): 크롭된 1채널 흑백 표 이미지
        Returns:
            np.ndarray: 세로선이 흰색으로 덮어씌워진 3채널(BGR) 표 이미지
        """
        # 이미지 이진화(글자/선 강조)
        binary = cv2.adaptiveThreshold(
            image, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 21, 10
        )

        # 세로선 탐지용 수직 커널 생성 (높이의 1/20 크기)
        rows = binary.shape[0]
        vertical_size = max(1, rows // 20)
        vertical_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, vertical_size))

        # 모폴로지 연산(침식 후 팽창)을 통해 낱개 글자는 지우고 긴 세로선만 남기기
        vertical_lines = cv2.erode(binary, vertical_kernel, iterations=1)
        vertical_lines = cv2.dilate(vertical_lines, vertical_kernel, iterations=1)

        # 원본 그레이스케일 이미지에서 탐지한 세로선 영역을 흰색(255)으로 덮어쓰기
        result_gray = image.copy()
        result_gray[vertical_lines > 0] = 255

        # 3채널(BGR)로 변환하여 반환
        result_bgr = cv2.cvtColor(result_gray, cv2.COLOR_GRAY2BGR)
        return result_bgr

    @staticmethod
    def _sort_tables_by_coordinates(table_metadata: list[dict]) -> list[dict]:
        """
        추출한 표의 메타데이터를 문서 순서(Y축 하행, X축 우행)로 정렬합니다.

        Args:
            table_metadata (list[dict]): 추출된 표 이미지 객체와 좌상단 좌표 정보를 담은 딕셔너리의 리스트
                                         (예: [{'img': np.ndarray, 'y': int, 'x': int}, ...])

        Returns:
            list[dict]: 위에서 아래로(Y축 오름차순), 같은 높이일 경우 왼쪽에서 오른쪽으로(X축 오름차순) 정렬이 완료된 딕셔너리 리스트
        """
        return sorted(table_metadata, key=lambda s: (s['y'], s['x']))
